# A battle-tested Hebrew tokenizer for dirty texts (bible, twitter, opensubs, oscar, cc100, mc4) focused on multi-word expression extraction.

from functools import partialmethod
import re

from unidecode import unidecode_expect_nonascii


def cc(s):
    return '[' + s + ']'


def ncc(s):
    return cc('^' + s)


def ncg(s):
    return '(?:' + s + ')'


def nla(s):
    return '(?!' + s + ')'


final_chars = 'ךםןףץ'
nonfinal_chars = 'כמנפצ'
to_nonfinal_table = str.maketrans(final_chars, nonfinal_chars)
to_final_table = str.maketrans(nonfinal_chars, final_chars)


class HebTokenizer:
    """
    Nikud and Teamim are ignored.
    Punctuation is normalized to ASCII (using unidecode).
    Correct usage of final letters (ךםןףץ) is enforced. Final פ and 'צ (with geresh) are allowed.
    Minimal word length is 2 proper letters.
    Same character repetition (שולטתתתת), which is a common form of slang writing, is limited to a maximum of max_char_repetition (default=2),
        and for the end of words or complete words, a same or more restrictive, maximum max_end_of_word_char_repetition (default=2). Use 0 or None for no limit.
        Note that these will throw away a small number of words with legitimate repetitions, most notably 'מממ' as in 'מממשלת' ,'מממש' ,'מממן'.
        allow_mmm (default=True) will specifically allow 'מממ' for the case max_char_repetition==2.
        Other less common legitimate repetitions include: 'תתת' ,'ששש' ,'נננ' ,'ממממ' ,'כככ' ,'ייי' ,'וווו' ,'ווו' ,'ההה' ,'בבב'.
    Words having only one or two distinct characters (חיחיחיחיחי), also a common form of slang writing, are limited to lengths up to max_one_two_char_word_len (default=7).
    Acronyms (צה"ל) and abbreviations ('וכו) are excluded, as well as numerals (42). (TBD)
    MWE refers to multi-word expression *candidates*, which are tokenized based on hyphen/makaf or surrounding punctuation.
    Hyphen-based MWE's are discarded if they contain more than max_mwe_hyphens (default=1). Use 0 not allowing hyphens or None for unlimited hyphens.
    Line opening hyphens as used in conversation and enumeration, can be ignored by allow_line_opening_hyphens (default=True)
    Strict mode can enforce the absence of extraneous hebrew letters in the same "clause" (strict=HebTokenizer.CLAUSE),
        sentence (strict=HebTokenizer.SENTENCE) or line (strict=HebTokenizer.LINE) of the MWE. Use 0 or None to not be strict (default=None).
    """

    @staticmethod
    def to_nonfinal(text):
        return text.translate(to_nonfinal_table)

    @staticmethod
    def to_final(text):
        return text.translate(to_final_table)

    hebrew_diacritics = '\u0591-\u05bd\u05bf-\u05c2\u05c4\u05c5\u05c7'  # all nikud and teamim except makaf, sof-pasuk, nun-hafukha
    hebrew_diacritics_regex = re.compile(cc(hebrew_diacritics))

    hebrew_letters = 'א-ת'
    nonfinal_letters = 'אבגדהוזחטיכלמנסעפצקרשת'
    final_letters = to_final.__func__(nonfinal_letters) + 'פ'
    nonfinal_letters_allowing_geresh = 'גזצ'
    final_letters_allowing_geresh = to_final.__func__(nonfinal_letters_allowing_geresh) + 'צ'
    geresh = '\''
    nonfinal_letter_geresh_pattern = ncg(cc(nonfinal_letters_allowing_geresh) + geresh + '|' + cc(nonfinal_letters))
    final_letter_geresh_pattern = ncg(cc(final_letters_allowing_geresh) + geresh + '|' + cc(final_letters))
    non_hebrew_letters_regex = re.compile(ncc(hebrew_letters) + '+')
    bad_final_regex = re.compile(cc(final_chars) + cc(nonfinal_letters))

    sentence_sep = '.?!'
    clause_sep_before_space = sentence_sep + ':;,)"'
    clause_sep_after_space = '("'
    clause_sep_between_spaces = '-'
    clause_sep_pattern = '\t|' + cc(clause_sep_before_space) + '\\s|\\s' + cc(clause_sep_after_space) + '|\\s' + cc(clause_sep_between_spaces) + '\\s'
    clause_sep_regex = re.compile(clause_sep_pattern)
    sentence_sep_regex = re.compile(cc(sentence_sep))

    mwe_words_sep = ' -'
    mwe_words_sep_regex = re.compile(cc(mwe_words_sep))

    mmm_pattern = '(?<!(?<!m)mmm)'.replace('m', 'מ')
    line_opening_hyphen_pattern = '((?:^|\n|\r)\\s*-{1,2})(?=\\w)'
    line_opening_hyphen_regex = re.compile(line_opening_hyphen_pattern, flags=re.MULTILINE)

    CLAUSE = 1
    SENTENCE = 2
    LINE = 3

    default_max_char_repetition = 2
    default_max_end_of_word_char_repetition = 2
    default_allow_mmm = True
    default_max_one_two_char_word_len = 7  # based on Hspell. e.g. שישישיי
    default_max_mwe_hyphens = 1
    default_allow_line_opening_hyphens = True
    default_strict = None
    default_bad_final_exceptions = ('לםרבה', 'יוםיום', 'סוףסוף')  # note: these exceptions are only for finding bad finals. the tokenizer will still ignore them

    def __init__(self, max_char_repetition=default_max_char_repetition, max_end_of_word_char_repetition=default_max_end_of_word_char_repetition, allow_mmm=default_allow_mmm, max_one_two_char_word_len=default_max_one_two_char_word_len, max_mwe_hyphens=default_max_mwe_hyphens, allow_line_opening_hyphens=default_allow_line_opening_hyphens):
        self.max_char_repetition = max_char_repetition
        self.max_end_of_word_char_repetition = max_end_of_word_char_repetition
        self.allow_mmm = allow_mmm
        self.max_one_two_char_word_len = max_one_two_char_word_len
        self.max_mwe_hyphens = max_mwe_hyphens
        self.allow_line_opening_hyphens = allow_line_opening_hyphens

        mmm = ''
        neg_rep = ''
        neg_end_rep = ''
        short_or_diverse = ''
        cch = cc(self.hebrew_letters)
        ncch = ncc(self.hebrew_letters)
        if max_char_repetition == 2 and allow_mmm:
            mmm = self.mmm_pattern
        if max_char_repetition:
            neg_rep = nla('(?P=ref_char0){' + str(max_char_repetition) + '}' + mmm)
        if max_end_of_word_char_repetition:
            if max_char_repetition:
                assert max_end_of_word_char_repetition <= max_char_repetition, f'max_end_of_word_char_repetition={max_end_of_word_char_repetition} cannot be greater than max_char_repetition={max_char_repetition}'
            neg_end_rep = nla('(?P=ref_char0){' + str(max_end_of_word_char_repetition) + '}' + ncg('$|' + ncch))
        if max_one_two_char_word_len:
            short_or_diverse = '(?=' + cch + '{1,' + str(max_one_two_char_word_len) + '}\\b|' + cch + '*(?P<ref_char1>' + cch + ')(?!(?P=ref_char1))(?P<ref_char>' + cch + ')' + cch + '*(?!(?P=ref_char1))(?!(?P=ref_char))' + cch + '+)'
        self.word_pattern = '(?<!' + cch + '[^\\s-])\\b' + short_or_diverse + ncg('(?P<ref_char0>' + self.nonfinal_letter_geresh_pattern + ')' + neg_rep + neg_end_rep) + '+' + self.final_letter_geresh_pattern + '(?!\\w)' + nla('[^\\s-]' + cch) + nla('-' + ncg('$|' + ncch))

        reuse_cnt = {}

        def reuse_regex_pattern(pattern):
            if pattern not in reuse_cnt:
                reuse_cnt[pattern] = 0
            else:
                reuse_cnt[pattern] += 1
            return re.sub('(\\(?P[<=])', '\\1' + '_' * reuse_cnt[pattern], pattern)

        max_mwe_hyphens_pattern = ''
        if max_mwe_hyphens != 0:
            max_mwe_hyphens_str = ''
            if max_mwe_hyphens is not None:
                max_mwe_hyphens_str = str(max_mwe_hyphens)
            max_mwe_hyphens_pattern = '|' + ncg('-' + reuse_regex_pattern(self.word_pattern)) + '{1,' + max_mwe_hyphens_str + '}'
        self.mwe_pattern = '(?<!-)' + reuse_regex_pattern(self.word_pattern) + ncg(ncg(' ' + reuse_regex_pattern(self.word_pattern)) + '+' + max_mwe_hyphens_pattern) + '(?!-)'
        self.line_with_strict_mwe_pattern = '^' + ncch + '*' + self.mwe_pattern + ncch + '*$'

        self.word_regex = re.compile(self.word_pattern)
        self.mwe_regex = re.compile(self.mwe_pattern)
        self.line_with_strict_mwe_regex = re.compile(self.line_with_strict_mwe_pattern, flags=re.MULTILINE)

    @classmethod
    def remove_diacritics(cls, text):
        return cls.hebrew_diacritics_regex.sub('', text)

    @classmethod
    def sanitize(cls, text, remove_diacritics=True):
        if remove_diacritics:
            text = cls.remove_diacritics(text)
        text = text.replace('\u05C3', '. ')  # deal with sof-pasuk for biblical texts
        return cls.non_hebrew_letters_regex.sub(lambda x: unidecode_expect_nonascii(x.group(), errors='preserve'), text)

    @classmethod
    def find_bad_final(cls, text, remove_diacritics=True, bad_final_exceptions=default_bad_final_exceptions, ret_all=False):  # this could help detect text containing badly fused words or lines
        if remove_diacritics:
            text = cls.remove_diacritics(text)
        for x in bad_final_exceptions or []:
            text = text.replace(x, '')
        if ret_all:
            return cls.bad_final_regex.findall(text)
        return cls.bad_final_regex.search(text)

    def is_word(self, text, sanitize=True):
        if sanitize:
            text = self.sanitize(text)
        return bool(self.word_regex.fullmatch(text))

    def get_words(self, text, sanitize=True, iterator=False):
        if sanitize:
            text = self.sanitize(text)
        result = (match.group() for match in self.word_regex.finditer(text))
        if not iterator:
            result = list(result)
        return result

    def has_word(self, text, sanitize=True):
        for _ in self.get_words(text, sanitize=sanitize, iterator=True):
            return True
        return False

    def is_mwe(self, text, sanitize=True):
        if sanitize:
            text = self.sanitize(text)
        return bool(self.mwe_regex.fullmatch(text))

    def is_word_or_mwe(self, text, sanitize=True):
        if sanitize:
            text = self.sanitize(text)
        return self.is_word(text, sanitize=False) or self.is_mwe(text, sanitize=False)

    def get_mwe(self, text, sanitize=True, strict=default_strict, iterator=False):
        if sanitize:
            text = self.sanitize(text)
        if self.allow_line_opening_hyphens:
            text = self.line_opening_hyphen_regex.sub('\\1 ', text)
        if strict:
            if strict == self.CLAUSE:
                text = '\n'.join(self.clause_sep_regex.split(text))
            elif strict == self.SENTENCE:
                text = '\n'.join(self.sentence_sep_regex.split(text))
            else:
                assert strict == self.LINE, f'Unknown strict mode: {strict}'
            result = (self.mwe_regex.search(match.group()).group() for match in
                      self.line_with_strict_mwe_regex.finditer(text))
        else:
            result = (match.group() for match in self.mwe_regex.finditer(text))
        if not iterator:
            result = list(result)
        return result

    def get_mwe_words(self, text, sanitize=True, strict=default_strict, flat=False, iterator=False):
        result = (self.mwe_words_sep_regex.split(mwe) for mwe in self.get_mwe(text, sanitize=sanitize, strict=strict))
        if flat:
            result = (word for word_list in result for word in word_list)
        if not iterator:
            result = list(result)
        return result

    def get_mwe_ngrams(self, text, n, sanitize=True, strict=default_strict, as_strings=False, flat=False, iterator=False):
        words = self.get_mwe_words(text, sanitize=sanitize, strict=strict, flat=False, iterator=iterator)
        result = ([' '.join(word_list[i:i+n]) if as_strings else tuple(word_list[i:i+n]) for i in range(len(word_list)-n+1)] for word_list in words if len(word_list) >= n)
        if flat:
            result = (ngram for ngram_list in result for ngram in ngram_list)
        if not iterator:
            result = list(result)
        return result

    get_mwe_bigrams = partialmethod(get_mwe_ngrams, n=2)


to_nonfinal = HebTokenizer.to_nonfinal
to_final = HebTokenizer.to_final
remove_diacritics = HebTokenizer.remove_diacritics
sanitize = HebTokenizer.sanitize
find_bad_final = HebTokenizer.find_bad_final


if __name__ == '__main__':

    text = 'א בְּרֵאשִׁ֖ית בָּרָ֣א אֱלֹהִ֑ים אֵ֥ת הַשָּׁמַ֖יִם וְאֵ֥ת הָאָֽרֶץ. ב וְהָאָ֗רֶץ הָיְתָ֥ה תֹ֙הוּ֙ וָבֹ֔הוּ וְחֹ֖שֶׁךְ עַל־פְּנֵ֣י תְה֑וֹם, וְר֣וּחַ אֱלֹהִ֔ים מְרַחֶ֖פֶת עַל־פְּנֵ֥י הַמָּֽיִם. ג וַיֹּ֥אמֶר אֱלֹהִ֖ים: "יְהִ֣י א֑וֹר", וַֽיְהִי־אֽוֹר. ד וַיַּ֧רְא אֱלֹהִ֛ים אֶת־הָא֖וֹר כִּי־ט֑וֹב, וַיַּבְדֵּ֣ל אֱלֹהִ֔ים בֵּ֥ין הָא֖וֹר וּבֵ֥ין הַחֹֽשֶׁךְ. ה וַיִּקְרָ֨א אֱלֹהִ֤ים לָאוֹר֙ "י֔וֹם" וְלַחֹ֖שֶׁךְ קָ֣רָא "לָ֑יְלָה", וַֽיְהִי־עֶ֥רֶב וַֽיְהִי־בֹ֖קֶר י֥וֹם אֶחָֽד.'

    def print_with_len(lst):
        print(lst, len(lst))

    print_with_len(text)
    print_with_len(to_final(text))
    print_with_len(to_nonfinal(text))
    print_with_len(remove_diacritics(text))
    print(f'bad_final={find_bad_final(text)}')
    print_with_len(sanitize(text))
    print_with_len(HebTokenizer.sanitize(text))

    heb_tokenizer = HebTokenizer()
    print_with_len(heb_tokenizer.sanitize(text))
    print_with_len(heb_tokenizer.get_words(text))
    print(f'has_word={heb_tokenizer.has_word(text)}')
    print_with_len(heb_tokenizer.get_mwe(text))
    print_with_len(heb_tokenizer.get_mwe_words(text))
    print_with_len(heb_tokenizer.get_mwe_words(text, flat=True))
    print_with_len(heb_tokenizer.get_mwe_bigrams(text))
    print_with_len(heb_tokenizer.get_mwe_bigrams(text, as_strings=True))
    print_with_len(heb_tokenizer.get_mwe_bigrams(text, flat=True))
    print_with_len(heb_tokenizer.get_mwe_bigrams(text, as_strings=True, flat=True))
    print_with_len(heb_tokenizer.get_mwe_ngrams(text, n=3))
    print_with_len(heb_tokenizer.get_mwe_ngrams(text, n=3, as_strings=True))
    print_with_len(heb_tokenizer.get_mwe_ngrams(text, n=3, flat=True))
    print_with_len(heb_tokenizer.get_mwe_ngrams(text, n=3, as_strings=True, flat=True))
