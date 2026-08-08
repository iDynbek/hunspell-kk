# Kazakh dictionary for Hunspell

|  | entries | recall | affix gap | wordlist gap | false accepts |
|---|---|---|---|---|---|
| 2009 release | 54,063 | 35.8% | 66,073 | 80,092 | 2.1% |
| generated | 91,336 | **76.2%** | **5,472** | **48,810** | 5.7% |

Against 227,637 Kazakh word forms and 50,000 known non-words, hunspell 1.7.3.
`make measure` reproduces it.

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

## The wordlist

The 2009 wordlist enters inflected forms as headwords in their own right —
`абай`, `абайдан` and `абайдың` are three of its 54,063 entries — because that
was how a one-suffix affix file coped. It costs precision now: an inflected form
entered as a stem gets a class flag of its own, so suffixes stack on top of an
already-inflected word.

`tools/prune.py` decides what to drop by asking Hunspell, twice. Build the
dictionary without every candidate at once and keep back whatever it rejects:
removing them together is the conservative direction, and it keeps derivations
like `абайсыздық` that the ladder cannot tell from an inflection. Then check
what that costs — a regenerable headword can still be the stem of something
longer — and put back the 7,405 entries that turn out to be load-bearing.

New vocabulary comes from two sources, and `data/lexicon.tsv` records which for
every entry, so provenance stays auditable and a source can be withdrawn without
rebuilding the rest.

| | | |
|---|---|---|
| apertium | [apertium-kaz](https://github.com/apertium/apertium-kaz), GPL-3.0 | 30,531 entries, all with a part of speech |
| kazdict | the sozdikqor corpus | 86,853 single-word Cyrillic headwords, 48,776 with a part of speech |
| baseline | the 2009 wordlist | 53,971 entries, no part of speech at all |

### Part of speech

`-дың` is the genitive on a noun and the second-person past on a verb —
`адамның` but `қондың` — so with nothing to tell `адам` from `қон` the affix
file has to allow both and `*адамдың` follows. The suffix classes are therefore
split into a nominal and a verbal track, twenty in place of ten, and residues
are mined per track.

Only stems with exactly one part of speech vote on what a track contains. A
word that is both, like `бала`, cannot say which track a suffix belongs to, and
counting it for both would put every verbal ending back on the nominal side.
Such words still inflect both ways; they just do not get a vote.

### What is left

The affix file only knows the suffix chains the corpus attested, so a legal but
unseen one is rejected: `мектептерімізде` appears nowhere in 227,637 forms and
is not accepted, even though every one of its four suffixes is. Composing tails
from attested morpheme pairs rather than whole attested strings would reach
them.

`адамдың` is still accepted, now for a different reason: `адамды` survives in
the wordlist as a 2009 padded form, because dropping it would cost `адамдық`
and its inflections, which are not headwords in their own right. Entering the
derivations properly is what removes it.

## Layout

| | |
|---|---|
| `baseline/` | the 2009 release, byte for byte, for comparison |
| `dict/` | generated `kk_KZ.aff` and `kk_KZ.dic` |
| `data/lexicon.tsv` | every headword, its track, and which source it came from |
| `data/residues.tsv` | the suffix strings Kazakh text puts on a stem, by stem class |
| `data/prune.txt` | headwords the affix file makes unnecessary |
| `tools/kkphon.py` | harmony, final segment and track — what picks a suffix's shape |
| `tools/build_lexicon.py` | the three sources → `data/lexicon.tsv` |
| `tools/mine_residues.py` | corpus → `data/residues.tsv` |
| `tools/gen_aff.py` | `data/residues.tsv` → a two-level `.aff` |
| `tools/prune.py` | → `data/prune.txt`, by asking Hunspell what it can regenerate |
| `tools/gen_dic.py` | the wordlist, with each entry's class on it |
| `tools/measure.py` | recall, split into affix gap and wordlist gap, plus false accepts |
| `tools/negatives.py` | non-words built by corrupting real forms |

Building `dict/` needs only this repository. Rebuilding `data/` needs a corpus
and the three wordlist sources; `make data` runs the stages in the order they
depend on each other. `tests/corpus_cyr.txt` and `tests/negatives.txt` are
generated and not committed — the corpus is third-party text, and vendoring it
would attach its provenance to the dictionary's.

## Licence

`baseline/` is redistributed under its own terms — GNU GPL 2.0 or later, GNU
LGPL 2.1 or later, or Mozilla MPL 1.1 or later, at your option — with
`baseline/README_kk_KZ.txt` as published.

The generator is derived from kazsearch-py, LGPL-3.0-or-later, itself a port of
the Rust core of [pg-kazsearch](https://github.com/darkhanakh/pg-kazsearch).

The wordlist takes entries from apertium-kaz, which is **GPL-3.0**, so the
generated dictionary is GPL-3.0 as a whole. The baseline's GPL-2.0-or-later
option permits that for the material carried forward from it.

The kazdict entries are headwords drawn from the sozdikqor corpus, which
aggregates 60 published dictionaries. A bare list of a language's words is not
obviously anyone's to license, but the selection may attract database rights in
some jurisdictions, and this has not been cleared. `data/lexicon.tsv` names the
source of every entry so that the kazdict-only ones can be dropped without
rebuilding anything else.
