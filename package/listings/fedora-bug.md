# bugzilla.redhat.com — component: hunspell-kk

**Summary:** hunspell-kk: replace the 2009 dictionary with the actively
maintained one (35.8% -> 97.7% acceptance of real Kazakh)

**Description:**
The kk_KZ dictionary that hunspell-kk packages is the 2009 OpenOffice release.
Its affix file allows exactly one suffix per word, which for an agglutinative
language means it rejects most correct text: measured on a million words of
Kazakh news prose it accepts 82.1% of tokens and only 58.2% of distinct words,
and against a 227k-form wordlist its recall is 35.8%.

An actively maintained replacement exists, GPL-3.0-or-later:
  https://github.com/iDynbek/hunspell-kk
  release: https://github.com/iDynbek/hunspell-kk/releases/tag/v0.1.0

It accepts 97.7% of the same news text (flagging one word in 44 instead of
one in 5.5), covers the complete nominal and verbal inflection grids, and the
repository carries the measurement harness so the numbers are reproducible
(`make running`, `make typos`). Trade-off, stated in its README: it catches
94.0% of realistic misspellings where the 2009 file catches 99.0% — the 2009
figure being a side effect of rejecting most correct words.

Please consider updating the package source to the new upstream.
