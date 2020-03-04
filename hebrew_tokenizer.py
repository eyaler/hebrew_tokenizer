import re
from unidecode import unidecode


class HebTokenizer:

    # Correct usage of final letters (ךםןףץ) is enforced. Final פ is allowed.
    # Same letter repitition (שולטתתתת), which is a common form of slang writing, is limited to a maximum of max_letter_repetition (default=3).
    # Acronyms (צה"ל) and abbrevations ('וכו) are excluded.
    # MWE refers to multi-word expression *candidates*, which are tokenized based on hyphen/makaf or surrounding punctuation.

    hebrew_diacritics = '\u0591-\u05bd\u05bf-\u05c2\u05c4\u05c5\u05c7' # all nikud and teamim except makaf, sof-pasuk, nun-hafukha
    hebrew_letters = 'א-ת'
    nonfinal_letters = 'אבגדהוזחטיכלמנסעפצקרשת'
    final_letters = 'אבגדהוזחטיךלםןסעפףץקרשת'
    nonfinal_letters_allowing_geresh = 'גזצ'
    final_letters_allowing_geresh = 'גזץ'
    nonfinal_letter_geresh_pattern = '(?:[' + nonfinal_letters_allowing_geresh + ']\'|[' + nonfinal_letters + '])'
    final_letter_geresh_pattern = '(?:[' + final_letters_allowing_geresh + ']\'|[' + final_letters + '])'

    def __init__(self, max_letter_repetition=3):
        self.max_letter_repetition = max_letter_repetition
        self.word_pattern = '(?<![' + self.hebrew_letters + '][^\s-])\\b(?:(' + self.nonfinal_letter_geresh_pattern + ')(?!\\1{' + str(
            self.max_letter_repetition) + '}))+' + self.final_letter_geresh_pattern + '(?!\w)(?![^\s-][' + self.hebrew_letters + '])'
        self.mwe_pattern = '(?<!-)' + self.word_pattern + '(?:-' + self.word_pattern.replace('\\1','\\2') + '|' + '(?: ' + self.word_pattern.replace('\\1','\\3') + ')+)(?!-)'
        self.word_regex = re.compile(self.word_pattern)
        self.mwe_regex = re.compile(self.mwe_pattern)

    def sanitize(self, text):
        text = re.sub('[' + self.hebrew_diacritics + ']', '', text)
        text = re.sub('[^' + self.hebrew_letters + ']+', lambda x: unidecode(x.group()), text)
        return text

    def is_word(self, text):
        text = self.sanitize(text)
        return self.word_regex.fullmatch(text) is not None

    def get_words(self, text):
        text = self.sanitize(text)
        return [match.group(0) for match in self.word_regex.finditer(text)]

    def is_mwe(self, text):
        text = self.sanitize(text)
        return self.mwe_regex.fullmatch(text) is not None

    def is_word_or_mwe(self, text):
        return self.is_word(text) or self.is_mwe(text)

    def get_mwe(self, text):
        text = self.sanitize(text)
        return [match.group(0) for match in self.mwe_regex.finditer(text)]

    def get_mwe_words(self, text):
        return [re.split('[ -]', mwe) for mwe in self.get_mwe(text)]


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
