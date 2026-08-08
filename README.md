# Kazakh dictionary for Hunspell

|  | recall | affix gap | wordlist gap | false accepts |
|---|---|---|---|---|
| 2009 release | 35.8% | 66,073 | 80,092 | 2.1% |
| generated | **62.0%** | **5,585** | 80,941 | 5.7% |

Against 227,637 Kazakh word forms and 50,000 known non-words, hunspell 1.7.3.
`make measure` reproduces it.

The affix side is close to finished: what it can still not reach is 5,585 forms
against the baseline's 66,073. What is left is the wordlist, which has not been
touched — 80,941 rejected forms have no analysis that is a headword at all, and
that number is the same in both rows because it is the same 2009 wordlist.

The Kazakh dictionary every distribution ships is `kk_KZ` version
**2009.09.01**, an OpenOffice extension by Akmaral Mussayeva, László Németh and
Rail Aliev over Alexey Lipchansky's aspell wordlist. It is not in
`LibreOffice/dictionaries`; the distro packages (`myspell-kk`, `hunspell-kk`)
all repackage that one release.

The two rejection causes are counted apart because they want different work,
and the false-accept rate is there because recall on its own is trivially
gamed: a dictionary that accepts every string scores 100%. Loosening the affix
conditions trades one against the other, so a change is only an improvement if
it moves recall further than it moves that last column.

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

[kazsearch-py](https://github.com/iDynbek/kazsearch-py) carries a description of
that shape: nine suffix layers in their attachment order. But it drives a
*stemmer*, and stemming only has to strip what might be a suffix; it never has
to decide which shape a suffix takes. Generating does. The model knows `-лар`,
`-дар` and `-тар` are all plural, not that `мектеп` selects the third, so a
generator built on it alone would emit `*мектеплер`.

Enumerating its cross-product would not work either — the nominal chain alone is
45 × 6 × 24 × 40 × 16 combinations, almost none of which anyone has uttered. So
the suffix strings are mined from the corpus instead. `tools/mine_residues.py`
records each one against the *class* of stem it was seen on, which is what picks
the shape, and the layer model is used only to know where one morpheme ends.

`tools/gen_aff.py` then cuts each residue after its first morpheme. That
morpheme is the only one whose shape the stem decides, so it goes in level one
keyed on the class; the entire rest of the chain becomes one atomic string in
level two. Depth stops mattering — `ларындағылардың` is five morphemes and
still two levels.

Shapes then compete. For a given stem class one shape of a morpheme is correct
and its siblings are errors, so `-дан`, `-ден`, `-тан`, `-тен`, `-нан`, `-нен`
are folded to one key and the ones left far behind the winner are dropped —
which is what keeps three stray corpus tokens (`айтды`, `атға`, `ақды` are each
in it once) from licensing a wrong allomorph for every stem in a class.
`tools/negatives.py` is the check: it corrupts real forms along both axes to
build 50,000 strings the phonology forbids.

### The two bugs that decided the design

The 2009 conditions can only look at a fixed window of the stem, so
`[аоуұыэ]т` matches `ат` but not `спорт` — 6,521 forms lost to stems with a
consonant cluster at the end. And because the same consonant list has to be
retyped for every suffix in both harmonies, one of them was left short: the
back-harmony plural covers `бвгғдт` where the front covers
`бвгғдкқһпстфхцчшщ`, so `халықтар`, `кітаптар` and `достар` are all rejected —
26,803 forms, 40% of the entire affix gap.

Neither is fixable inside a condition. Both go away if the stem is classified
once, at its entry, and the rules are told the answer instead of guessing at
what they cannot see.

### What is left

`адамдың` is accepted and should not be; the genitive of `адам` is `адамның`.
`-дың` after an `n`-final stem is a real suffix — `қондың`, "you landed" — and
the 2009 wordlist records no part of speech, so nothing in it distinguishes
`адам` from `қон`. Most of the residual 5.7% is this, and it is wordlist work.

## Layout

| | |
|---|---|
| `baseline/` | the 2009 release, byte for byte, for comparison |
| `dict/` | generated `kk_KZ.aff` and `kk_KZ.dic` |
| `data/residues.tsv` | the suffix strings Kazakh text puts on a stem, by stem class |
| `tools/kkphon.py` | vowel harmony and final segment — what picks a suffix's shape |
| `tools/mine_residues.py` | corpus → `data/residues.tsv` |
| `tools/gen_aff.py` | `data/residues.tsv` → a two-level `.aff` |
| `tools/gen_dic.py` | the wordlist, with each entry's class on it |
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
