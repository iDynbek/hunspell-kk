# Kazakh dictionary for Hunspell

The Kazakh dictionary every distribution ships is `kk_KZ` version
**2009.09.01**, an OpenOffice extension by Akmaral Mussayeva, László Németh and
Rail Aliev over Alexey Lipchansky's aspell wordlist. It is not in
`LibreOffice/dictionaries`; the distro packages (`myspell-kk`, `hunspell-kk`)
all repackage that one release.

Measured against 227,637 Kazakh word forms with hunspell 1.7.3:

```
recall            35.8%
rejected        146,165
  affix gap      66,073   45.2%   stem is a headword, the rules cannot reach the form
  wordlist gap   80,092   54.8%   no analysis of the form is a headword
false accepts      1,027    2.1%   of 50,000 known non-words
```

Reproduce it with `make baseline`. The two rejection causes want different
work, which is why they are counted apart, and the false-accept rate is there
because recall on its own is trivially gamed: a dictionary that accepts every
string scores 100%. Loosening the affix conditions trades one against the
other, so a change is only an improvement if it moves recall without moving
that last line.

## Why it rejects two forms in three

`baseline/kk_KZ.aff` is 51 suffix groups and 2,644 rules, and its entire
preamble is `SET UTF-8` and `TRY`. No prefixes, no continuation flags, every
group declared `N`:

```
SFX A N 45
SFX A 0 дар [аоуұыэ]ж
SFX A 0 лар [аоуұыэ]
```

Nothing carries a flag onto what it appends, so a word takes **exactly one
suffix, ever**. Kazakh routinely stacks four — `мектеп-тер-іміз-де` is stem,
plural, possessive, locative — and that word is rejected.

Two workarounds paper over it, and both are visible in the data. Suffixes are
pre-combined into single rules, which is why 51 groups need 2,644 rules. And
inflected forms are entered as headwords in their own right: `абай`, `абайдан`
and `абайдың` are three separate entries of 54,063.

There is also no room to grow. Without a `FLAG` directive the flags are single
ASCII characters, about 64 usable, and 51 are taken.

Nothing in the preamble helps suggestions either — no `REP`, `MAP`, `KEY`,
`WORDCHARS`, `ICONV`, `BREAK` or `COMPOUND*`. `MAP` in particular is what
teaches a spellchecker that а/ә, о/ө, ұ/ү, қ/к, ғ/г, ң/н and и/і are the pairs
a Kazakh typist actually confuses.

## Approach

Hunspell strips at most two affix levels, and that is deliberate: Németh closed
[#90](https://github.com/hunspell/hunspell/issues/90) in 2008 saying an
"affix" is meant to be an affix *combination*, and that Hungarian generates its
combinations with nested m4 macros. The gap he named in the same comment is the
one this fills — *"there is no standard tool yet to generate these combinations
from simple n-fold descriptions."*

[kazsearch-py](https://github.com/iDynbek/kazsearch-py) already carries the
n-fold description: nine suffix layers in their attachment order, each suffix
tagged with the vowel harmony it demands. `tools/gen_aff.py` folds those layers
down to the two levels hunspell strips, so the source of truth stays the
layered model and the `.aff` is generated from it — the same arrangement as
`rules.lua` in the KOReader plugin.

```
nominal   level 1 = DERIV × PLUR × POSS     level 2 = CASE × PRED
verbal    level 1 = VVOICE × VNEG           level 2 = VTENSE × VPERSON
```

That model is not sufficient on its own. It drives a *stemmer*, and stemming
only has to strip what might be a suffix; it never has to decide which shape a
suffix takes. Generating does. The model knows `-лар` and `-дар` and `-тар` are
all plural, not that `мектеп` selects the third — so a generator built from it
alone would emit `*мектеплер`.

The 2009 affix file is exactly the missing half, and gets it right:

```
SFX A 0 дар [жзлмнң]…    SFX A 0 лар [аоуұыэйру]…    SFX A 0 тар [бвгғдкқпстфхһцчшщ]…
```

So the generator takes the layer ordering from the model and the allomorph
conditions from the baseline, and `tools/negatives.py` is what keeps the second
half honest: it corrupts real forms along both axes — harmony, `-лар` → `-лер`,
and voicing, `-тар` → `-лар` — to build strings the phonology forbids.

## Layout

| | |
|---|---|
| `baseline/` | the 2009 release, byte for byte, for comparison |
| `dict/` | generated `kk_KZ.aff` and `kk_KZ.dic` |
| `tools/gen_aff.py` | the layered model → a two-level `.aff` |
| `tools/measure.py` | recall, split into affix gap and wordlist gap, plus false accepts |
| `tools/negatives.py` | non-words built by corrupting real forms |

`tests/corpus_cyr.txt` and `tests/negatives.txt` are generated from kazsearch-py
and not committed: the corpus is third-party text of uncertain provenance, and
vendoring it would attach that question to the dictionary's licence.

## Licence

`baseline/` is redistributed under its own terms — GNU GPL 2.0 or later, GNU
LGPL 2.1 or later, or Mozilla MPL 1.1 or later, at your option — with
`baseline/README_kk_KZ.txt` as published.

The generator is derived from kazsearch-py, LGPL-3.0-or-later, itself a port of
the Rust core of [pg-kazsearch](https://github.com/darkhanakh/pg-kazsearch).
Generated output is distributed under **LGPL-3.0-or-later**, which the
baseline's LGPL-2.1-or-later option permits for any wordlist material carried
forward.
