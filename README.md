# Kazakh dictionary for Hunspell

A spellchecker has two jobs and they pull against each other: catch mistakes,
and stay quiet about correct text. The only Kazakh dictionary distributions
ship — `kk_KZ` version **2009.09.01** — does the first by failing the second,
rejecting two words in three, so nobody could leave it on.

| | catches misspellings | keeps quiet on correct text |
|---|---|---|
| 2009 release | **99.0%** | 82.1% |
| this dictionary | 95.4% | **97.9%** |

Coverage and catching are the same knob — a looser dictionary catches fewer
mistakes — so this is a choice of where to sit, not a defect. It sits where a
Kazakh writer can leave it switched on.

On a million words of real news prose ([KazNERD](https://github.com/IS2AI/KazNERD),
weighted by how often each word occurs), it accepts **97.9%** against the 2009
release's 82.1%; counting each distinct word once, **95.0%** against 58.2%. On
the text of the Kazakh Constitution, **99.7%** of genuine words.

| | entries | recall on modern Kazakh | false accepts |
|---|---|---|---|
| 2009 release | 54,063 | 30.1% | 1.8% |
| this dictionary | 131,289 | **77.0%** | 2.4% |

Recall is measured on ~484k word forms from the sozdikqor corpus; false accepts
on 50,000 constructed non-words. The false-accept column is the price of
reaching three times as many real forms, and the check that a coverage gain is
real rather than gamed — a dictionary that accepts everything scores 100% on
recall. `make running`, `make typos` and `make scoped` reproduce the numbers.

## How it works

The 2009 affix file declares every suffix group `N`, so a word takes exactly
one suffix — but Kazakh stacks four (`мектеп-тер-іміз-де`). It worked around
this by pre-combining suffixes into 2,644 rules and entering inflected forms as
their own headwords, and it still rejected most of the language.

This dictionary generates the affix file instead. Suffix strings are mined from
a corpus, recorded against the *class* of stem they attach to (harmony, final
segment, part of speech — what decides a suffix's shape). Each is cut after its
first morpheme: that morpheme, the only one the stem governs, goes in level one
keyed on the class; the rest of the chain becomes one atomic string in level
two. So Hunspell's two affix levels reach chains of any depth, and competing
allomorphs (`-дан`/`-ден`/`-тан`/`-тен`/…) are folded to one key with the
losers dropped.

Vocabulary comes from [apertium-kaz](https://github.com/apertium/apertium-kaz)
(with parts of speech), the sozdikqor corpus, and the 2009 wordlist;
`data/lexicon.tsv` records the source of every entry. The suffix inventory and
chain adjacency draw on [KazNLP](https://github.com/nlacslab/kaznlp) and
[kazsearch-py](https://github.com/iDynbek/kazsearch-py). Irregular forms Hunspell
rules can't express — cluster-loanword epenthesis (`акт`→`актіге`), vowel
elision (`орын`→`орны`), voicing (`кітап`→`кітабы`) — are validated against
apertium-kaz and listed outright. `NOTES.md` has the detail.

## Installing

`make dist` builds `dist/kk_KZ.oxt`. Install it through **Tools → Extension
Manager → Add** — do not double-click the file, which crashes some LibreOffice
builds. For plain Hunspell, use the `dict/kk_KZ.aff` and `dict/kk_KZ.dic` pair.

First release, not yet used in anger. Compounds and the Latin alphabet are not
handled.

## Layout

| | |
|---|---|
| `baseline/` | the 2009 release, byte for byte, for comparison |
| `dict/` | generated `kk_KZ.aff` and `kk_KZ.dic` |
| `data/` | lexicon, mined residues, chains, and the hand-listed irregulars |
| `tools/` | the generator and its measurement scripts |
| `package/` | LibreOffice extension metadata |
| `NOTES.md` | how it works in full, and what could be measured |

Building `dict/` needs only this repository. Rebuilding `data/` needs the corpus
and wordlist sources; `make data` runs the stages in dependency order.

## Licence

**GPL-3.0-or-later**, because apertium-kaz is; see `COPYING`. `baseline/` is
redistributed under its own terms (GPL 2.0+ / LGPL 2.1+ / MPL 1.1). The
generator derives from kazsearch-py (LGPL-3.0-or-later).

Made by an individual volunteer with no organisational ties, so that Kazakh can
be written on the internet with the support other languages take for granted.
`data/lexicon.tsv` records the source of every entry, so any contributor's
material can be identified and withdrawn on request.
