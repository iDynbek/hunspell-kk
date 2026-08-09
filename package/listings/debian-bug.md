# Debian BTS — email to submit@bugs.debian.org

Subject: hunspell-kk: new upstream replaces the 2009 dictionary (35.8% -> 98.1%)

Package: hunspell-kk
Severity: wishlist

The packaged kk_KZ dictionary is the 2009 OpenOffice release, whose affix
file allows one suffix per word; on a million words of real Kazakh news
prose it accepts 82.1% of tokens (58.2% of distinct words), so in practice
it underlines most correct Kazakh and users disable it.

An actively maintained replacement exists, GPL-3.0-or-later:
  https://github.com/iDynbek/hunspell-kk
  https://github.com/iDynbek/hunspell-kk/releases/tag/v0.2.8

It accepts 98.1% of the same text, covers the full nominal and verbal
inflection grids, and ships a reproducible measurement harness. The README
states the trade-off plainly: 95.3% of realistic misspellings caught against
the 2009 file's 99.0%, the latter being a side effect of rejecting most
correct words.

Please consider switching the source to the new upstream.
