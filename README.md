# hebrew_tokenizer
A battle-tested Hebrew tokenizer for dirty texts (bible, twitter, opensubs) focused on multi-word expression extraction.

* Nikud and Teamim are ignored.
* Punctuation is normalized to ASCII (using unidecode).
* Correct usage of final letters (ךםןףץ) is enforced. Final פ and 'צ (with geresh) are allowed.
* Same letter repetition (שולטתתתת), which is a common form of slang writing, is limited to a maximum of max_letter_repetition (default=2),
    and at the end of words a maximum max_end_of_word_letter_repetition (default=2). Use 0 or None for no limit.
    * Note that these will throw away a very small number of legitimate repetitions, most notably 'מממ' as in 'מממן', 'מממשלת'.
    * allow_mmm (default=True) will specifically allow 'מממ' for the case max_letter_repetition==2.
* Acronyms (צה"ל) and abbreviations ('וכו) are excluded, as well as numerals (42). (TBD)
* MWE refers to multi-word expression *candidates*, which are tokenized based on hyphen/makaf or surrounding punctuation.
* Hyphen-based MWE's are discarded if they contain more than max_mwe_hyphens (default=1). Use 0 not allowing hyphens or None for unlimited hyphens.
* Line opening hyphens as used in conversation and enumeration, can be ignored by allow_line_opening_hyphens (default=True)
* Strict mode can enforce the absence of extraneous hebrew letters in the same "clause" (strict=HebTokenizer.CLAUSE),
    sentence (strict=HebTokenizer.SENTENCE) or line (strict=HebTokenizer.LINE) of the MWE. Use 0 or None to not be strict (default=None).
