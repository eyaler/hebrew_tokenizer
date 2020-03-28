import re
from unidecode import unidecode


class HebTokenizer:
    # Nikud and teamim are ignored
    # Correct usage of final letters (ךםןףץ) is enforced. Final פ is allowed.
    # Same letter repetition (שולטתתתת), which is a common form of slang writing, is limited to a maximum of max_letter_repetition (default=3),
    #   and at the end of words a maximum max_end_of_word_letter_repetition (default=2).
    # Acronyms (צה"ל) and abbrevations ('וכו) are excluded.
    # MWE refers to multi-word expression *candidates*, which are tokenized based on hyphen/makaf or surrounding punctuation.
    # Hyphen-based MWE's are discarded if the contain more than max_mwe_hyphens (default=1).
    # Strict mode enforces the absence of extraneous hebrew letters in the same "clause" (strict=CLAUSE), sentence (strict=SENTENCE) or line (strict=LINE) of the MWE.

    hebrew_diacritics = '\u0591-\u05bd\u05bf-\u05c2\u05c4\u05c5\u05c7' # all nikud and teamim except makaf, sof-pasuk, nun-hafukha
    hebrew_letters = 'א-ת'
    nonfinal_letters = 'אבגדהוזחטיכלמנסעפצקרשת'
    final_letters = 'אבגדהוזחטיךלםןסעפףץקרשת'
    nonfinal_letters_allowing_geresh = 'גזצ'
    final_letters_allowing_geresh = 'גזץ'
    nonfinal_letter_geresh_pattern = '(?:[' + nonfinal_letters_allowing_geresh + ']\'|[' + nonfinal_letters + '])'
    final_letter_geresh_pattern = '(?:[' + final_letters_allowing_geresh + ']\'|[' + final_letters + '])'
    sentence_sep = '.?!'
    clause_sep_before_space = sentence_sep + ':;,)"'
    clause_sep_after_space = '("'
    clause_sep_between_spaces = '-'
    clause_pattern = '[' + clause_sep_before_space + '] | [' + clause_sep_after_space + ']| [' + clause_sep_between_spaces + '] '
    clause_regex = re.compile(clause_pattern)
    sentence_pattern = '[' + sentence_sep + '] '
    sentence_pattern = re.compile(sentence_pattern)
    CLAUSE = 1
    SENTENCE = 2
    LINE = 3

    def __init__(self, max_letter_repetition=3, max_end_of_word_letter_repetition=2, max_mwe_hyphens=1):
        self.max_letter_repetition = max_letter_repetition
        self.max_end_of_word_letter_repetition = max_end_of_word_letter_repetition
        neg_rep = '' if not self.max_letter_repetition else '(?!\\1{' + str(self.max_letter_repetition) + '})'
        neg_end_rep = '' if not self.max_end_of_word_letter_repetition else '(?!\\1{' + str(self.max_end_of_word_letter_repetition) + ',}(?:$|[^'+self.hebrew_letters+']))'
        self.word_pattern = '(?<![' + self.hebrew_letters + '][^ -])\\b(?:(' + self.nonfinal_letter_geresh_pattern + ')'+ neg_rep + neg_end_rep +')+' + self.final_letter_geresh_pattern + '(?!\w)(?![^ -][' + self.hebrew_letters + '])(?!-(?:$|[^' + self.hebrew_letters + ']))'
        self.mwe_pattern = '(?<!-)' + self.word_pattern + '(?:(?: ' + self.word_pattern.replace('\\1','\\2') + ')+'
        if max_mwe_hyphens != 0:
            self.mwe_pattern += '|(?:-' + self.word_pattern.replace('\\1','\\3') + '){1,'+('' if max_mwe_hyphens is None else str(max_mwe_hyphens))+'}'
        self.mwe_pattern += ')(?!-)'
        self.line_with_strict_mwe_pattern = '^[^' + self.hebrew_letters + ']*' + self.mwe_pattern + '[^' + self.hebrew_letters + ']*$'

        self.word_regex = re.compile(self.word_pattern)
        self.mwe_regex = re.compile(self.mwe_pattern)
        self.line_with_strict_mwe_regex = re.compile(self.line_with_strict_mwe_pattern, flags=re.MULTILINE)

    def sanitize(self, text):
        text = re.sub('[' + self.hebrew_diacritics + ']', '', text)
        text = re.sub('[^' + self.hebrew_letters + ']+', lambda x: unidecode(x.group()), text)
        return text

    def is_word(self, text):
        text = self.sanitize(text)
        return self.word_regex.fullmatch(text) is not None

    def get_words(self, text):
        text = self.sanitize(text)
        return [match.group() for match in self.word_regex.finditer(text)]

    def is_mwe(self, text):
        text = self.sanitize(text)
        return self.mwe_regex.fullmatch(text) is not None

    def is_word_or_mwe(self, text):
        return self.is_word(text) or self.is_mwe(text)

    def break_clauses(self, text):
        return '\n'.join(self.clause_regex.split(text))

    def get_mwe(self, text, strict=None):
        text = self.sanitize(text)
        if strict:
            if strict == self.CLAUSE:
                text = '\n'.join(self.clause_regex.split(text))
            elif strict == self.SENTENCE:
                text = '\n'.join(self.sentence_regex.split(text))
            return [self.mwe_regex.search(match.group()).group() for match in self.line_with_strict_mwe_regex.finditer(text)]
        return [match.group() for match in self.mwe_regex.finditer(text)]

    def get_mwe_words(self, text, strict=None):
        return [re.split('[ -]', mwe) for mwe in self.get_mwe(text, strict=strict)]


if __name__ == '__main__':
    text = 'א בְּרֵאשִׁ֖ית בָּרָ֣א אֱלֹהִ֑ים אֵ֥ת הַשָּׁמַ֖יִם וְאֵ֥ת הָאָֽרֶץ. ב וְהָאָ֗רֶץ הָיְתָ֥ה תֹ֙הוּ֙ וָבֹ֔הוּ וְחֹ֖שֶׁךְ עַל־פְּנֵ֣י תְה֑וֹם, וְר֣וּחַ אֱלֹהִ֔ים מְרַחֶ֖פֶת עַל־פְּנֵ֥י הַמָּֽיִם. ג וַיֹּ֥אמֶר אֱלֹהִ֖ים: "יְהִ֣י א֑וֹר", וַֽיְהִי־אֽוֹר. ד וַיַּ֧רְא אֱלֹהִ֛ים אֶת־הָא֖וֹר כִּי־ט֑וֹב, וַיַּבְדֵּ֣ל אֱלֹהִ֔ים בֵּ֥ין הָא֖וֹר וּבֵ֥ין הַחֹֽשֶׁךְ. ה וַיִּקְרָ֨א אֱלֹהִ֤ים לָאוֹר֙ "י֔וֹם" וְלַחֹ֖שֶׁךְ קָ֣רָא "לָ֑יְלָה", וַֽיְהִי־עֶ֥רֶב וַֽיְהִי־בֹ֖קֶר י֥וֹם אֶחָֽד.'

    def print_with_len(lst):
        print(lst, len(lst))

    heb_tokenizer = HebTokenizer()
    print_with_len(text)
    print_with_len(heb_tokenizer.sanitize(text))
    print_with_len(heb_tokenizer.get_words(text))
    print_with_len(heb_tokenizer.get_mwe(text))
    print_with_len(heb_tokenizer.get_mwe_words(text))
