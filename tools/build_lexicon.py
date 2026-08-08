"""Assemble the wordlist, with a part of speech on every entry that has one.

The 2009 wordlist records no part of speech, and that is not a cosmetic gap.
`-дың` after an `n`-final stem is the genitive on a noun and the second-person
past on a verb — `адамның` but `қондың` — so with nothing to tell `адам` from
`қон` the affix file has to allow both, and `*адамдың` follows. Splitting the
suffix classes by part of speech is the fix, and it needs a source that carries
one.

Three go in, and each entry records which:

    apertium   apertium-kaz, GPL-3.0. 34,870 entries, part of speech from the
               continuation class — `бала:бала V-IV` is a verb, `балақ:балақ
               N1` a noun. The most reliable of the three.
    kazdict    the sozdikqor corpus, 86,569 single-word Cyrillic headwords with
               labels for 53,154. Much the largest, and the only one that
               reaches modern loanwords. Headwords are printed in capitals,
               which is typography rather than orthography, so they are folded.
    baseline   the 2009 wordlist, no part of speech at all.

    python tools/build_lexicon.py -o data/lexicon.tsv

The source column is kept so that provenance stays auditable per entry and a
source can be withdrawn without rebuilding the rest.
"""

from __future__ import annotations

import argparse
import collections
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

NOMINAL, VERBAL = "n", "v"

# `surface:lemma CONTINUATION ;` — the continuation class is the part of speech.
LEXC_ENTRY = re.compile(r"^\s*([^!:;\s][^:]*):([^\s;]+)\s+([A-Za-z0-9_-]+)\s*;")
CYRILLIC_WORD = re.compile(r"^[Ѐ-ӿ]+$")

# Only the verbs need singling out; everything that inflects like a noun —
# adjectives, adverbs, numerals, proper names — shares one track, because
# Kazakh gives them all the same case, plural and possessive endings.
KAZDICT_VERB = "ет"


def from_apertium(path: Path) -> dict[str, set[str]]:
    out = collections.defaultdict(set)
    for line in path.read_text(encoding="utf-8").splitlines():
        match = LEXC_ENTRY.match(line.split("!")[0])
        if not match:
            continue
        surface, continuation = match.group(1).strip(), match.group(3)
        surface = surface.replace("%", "")
        if CYRILLIC_WORD.match(surface):
            out[surface.lower()].add(VERBAL if continuation.startswith("V") else NOMINAL)
    return out


def from_kazdict(path: Path) -> dict[str, set[str]]:
    out = collections.defaultdict(set)
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    rows = con.execute("""
        SELECT h.form, (SELECT group_concat(DISTINCT l.code)
                          FROM entry e JOIN sense s ON s.entry_id = e.id
                          JOIN sense_label sl ON sl.sense_id = s.id
                          JOIN label l ON l.id = sl.label_id
                         WHERE e.headword_id = h.id AND l.kind = 'pos')
          FROM headword h
         WHERE h.n_words = 1 AND h.script = 'cyrillic'""")
    for form, codes in rows:
        form = form.strip().lower()
        if not CYRILLIC_WORD.match(form):
            continue
        if codes:
            tags = set(codes.split(","))
            out[form] |= {VERBAL} if KAZDICT_VERB in tags else set()
            out[form] |= {NOMINAL} if tags - {KAZDICT_VERB} else set()
        else:
            out[form] |= set()
    con.close()
    return out


def from_baseline(path: Path) -> dict[str, set[str]]:
    out = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines()[1:]:
        word = line.split("/")[0].split("\t")[0].strip()
        if word:
            out.setdefault(word.lower(), set())
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", type=Path, default=ROOT / "data/lexicon.tsv")
    ap.add_argument("--apertium", type=Path,
                    default=ROOT.parent / "apertium-kaz/apertium-kaz.kaz.lexc")
    ap.add_argument("--kazdict", type=Path,
                    default=ROOT.parent / "kazdict/data/build/kazdict.db")
    ap.add_argument("--baseline", type=Path, default=ROOT / "baseline/kk_KZ.dic")
    args = ap.parse_args()

    sources = [("apertium", args.apertium, from_apertium),
               ("kazdict", args.kazdict, from_kazdict),
               ("baseline", args.baseline, from_baseline)]

    tracks: dict[str, set[str]] = collections.defaultdict(set)
    origin: dict[str, set[str]] = collections.defaultdict(set)
    for name, path, load in sources:
        if not path.exists():
            print(f"skipping {name}: no {path}", file=sys.stderr)
            continue
        entries = load(path)
        for word, pos in entries.items():
            tracks[word] |= pos
            origin[word].add(name)
        print(f"{name:<9} {len(entries):>7,} entries, "
              f"{sum(1 for p in entries.values() if p):>7,} with a part of speech",
              file=sys.stderr)

    with args.output.open("w", encoding="utf-8") as fh:
        fh.write("# word\ttracks\tsources — generated by tools/build_lexicon.py\n")
        for word in sorted(tracks):
            fh.write(f"{word}\t{''.join(sorted(tracks[word])) or '-'}"
                     f"\t{','.join(sorted(origin[word]))}\n")

    tally = collections.Counter("".join(sorted(t)) or "-" for t in tracks.values())
    print(f"\n{len(tracks):,} words → {args.output}", file=sys.stderr)
    print("  " + "  ".join(f"{k}={v:,}" for k, v in sorted(tally.items())),
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
