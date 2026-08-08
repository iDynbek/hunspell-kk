"""Ask apertium-kaz's grammar about every chain this affix file licenses.

Apertium's analyzer catches 98.7% of realistic misspellings against this
dictionary's 94.0%, and the difference is morphotactics: their transitions are
hand-encoded by linguists, ours are mined, and mining invents. This audit
prices the difference chain by chain — half of the 18,886 licensed chains
turned out to be refusable on every stem tried.

For each (class, chain) the affix file licenses, the chain is synthesized onto
five stems of that class that Apertium recognises as lemmas of the right part
of speech. A chain rejected on *every* stem is presumed invented, and vetoed —
unless the corpus attests it with real weight, or a paradigm grid pins it:
Apertium's own lexicon has gaps (95.5% token coverage), so where we hold
direct evidence, our evidence wins.

    python tools/audit_apertium.py --threshold 25 -o data/apertium_veto.tsv

Run it against an affix file built WITHOUT a veto — move data/apertium_veto.tsv
aside and `make aff` first — or the audit judges only what its own last run
left alive.

Needs the analyzer, by default in the `apertium` distrobox:

    distrobox create --name apertium --image docker.io/library/debian:bookworm
    # inside: add https://apertium.projectjj.com/apt/install-nightly.sh,
    # then apt install apertium-kaz hfst
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gen_aff import CLASS_FLAG  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FLAG2CLS = {str(v): k for k, v in CLASS_FLAG.items()}

LOOKUP = ("distrobox", "enter", "apertium", "--",
          "hfst-lookup", "-q", "/usr/share/apertium/apertium-kaz/kaz.automorf.hfst")

NOMINAL_TAGS = {"n", "adj", "np", "num", "prn", "adv"}
VERBAL_TAGS = {"v", "vaux"}
VOICELESS = set("кқп")
VOWELS = set("аәеоөұүыіи")
REPS_PER_CLASS = 5


def lookup(words: list[str]) -> dict[str, list[str]]:
    """word → its analyses, unknowns filtered out."""
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt",
                                     dir=Path.home(), delete=False) as fh:
        fh.write("\n".join(words))
        path = fh.name
    try:
        proc = subprocess.run([*LOOKUP[:4], "bash", "-c",
                               f"{' '.join(LOOKUP[4:])} < {path}"],
                              capture_output=True, text=True, timeout=560)
    finally:
        Path(path).unlink(missing_ok=True)
    out: dict[str, list[str]] = collections.defaultdict(list)
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and not parts[1].endswith("+?"):
            out[parts[0]].append(parts[1])
    return out


def licensed_chains(aff: Path):
    """Every (class flag, chain) the affix file can produce, strips excluded."""
    groups = collections.defaultdict(list)
    for line in aff.read_text(encoding="utf-8").splitlines():
        m = re.match(r"SFX (\d+) (\S+) (\S+) \S+$", line)
        if not m:
            continue
        flag, strip, append = m.groups()
        cont = None
        if "/" in append:
            append, cont = append.split("/")
        groups[flag].append(("" if strip == "0" else strip, append, cont))
    for flag in sorted(set(groups) & set(FLAG2CLS)):
        for strip, s1, cont in groups[flag]:
            if strip:
                continue                     # voicing/elision: paradigm-guarded
            yield flag, s1
            if cont:
                for _s, tail, _c in groups.get(cont, []):
                    yield flag, s1 + tail


def representatives(lexicon: Path, kaznerd: Path) -> dict[str, list[str]]:
    """Per class, frequent bare stems Apertium knows as lemmas of that track."""
    from gen_dic import read_lexicon
    from kkphon import stem_class
    from measure_running import tokens
    lex = read_lexicon(lexicon)
    freq = tokens(kaznerd, "train")
    candidates = collections.defaultdict(list)
    for word, _n in sorted(freq.items(), key=lambda kv: -kv[1]):
        low = word.lower()
        if low in lex and 3 <= len(low) <= 9:
            for track in lex[low]:
                flag = str(CLASS_FLAG[track + stem_class(low)])
                if len(candidates[flag]) < 12 and low not in candidates[flag]:
                    candidates[flag].append(low)

    analyses = lookup(sorted({w for v in candidates.values() for w in v}))
    reps = {}
    for flag, words in candidates.items():
        wanted = VERBAL_TAGS if int(flag) >= 10 + len(FLAG2CLS) // 2 else NOMINAL_TAGS
        good = []
        for w in words:
            for a in analyses.get(w, []):
                lemma, _, rest = a.partition("<")
                if lemma == w and rest.split(">", 1)[0] in wanted:
                    good.append(w)
                    break
        reps[flag] = good[:REPS_PER_CLASS]
    return reps


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", type=Path, default=ROOT / "data/apertium_veto.tsv")
    ap.add_argument("--aff", type=Path, default=ROOT / "dict/kk_KZ.aff")
    ap.add_argument("--threshold", type=int, default=25,
                    help="corpus tokens that outrank Apertium's refusal; its "
                         "lexicon has gaps, and direct evidence wins over them")
    ap.add_argument("--kaznerd", type=Path, default=ROOT.parent / "KazNERD/KazNERD")
    args = ap.parse_args()

    reps = representatives(ROOT / "data/lexicon.tsv", args.kaznerd)
    pairs = []
    for flag, chain in licensed_chains(args.aff):
        for rep in reps.get(flag, []):
            if chain[:1] in VOWELS and rep[-1] in VOICELESS:
                continue
            pairs.append((flag, chain, rep))
    forms = sorted({rep + chain for _f, chain, rep in pairs})
    print(f"{len(forms):,} forms to judge", file=sys.stderr)

    accepted = set()
    for i in range(0, len(forms), 60000):
        accepted |= set(lookup(forms[i:i + 60000]))

    votes = collections.defaultdict(lambda: [0, 0])
    for flag, chain, rep in pairs:
        vote = votes[flag, chain]
        vote[1] += 1
        if rep + chain in accepted:
            vote[0] += 1

    mined = collections.Counter()
    for line in (ROOT / "data/residues.tsv").read_text(encoding="utf-8").splitlines():
        if not line.startswith("#") and line:
            cls, strip, res, n = line.split("\t")
            if strip == "0":
                mined[cls, res] += int(n)
    pinned = set()
    for name in ("paradigm.tsv", "verb_paradigm.tsv"):
        for line in (ROOT / "data" / name).read_text(encoding="utf-8").splitlines():
            if not line.startswith("#") and line:
                cls, strip, res, _n = line.split("\t")
                if strip == "0":
                    pinned.add((cls, res))

    vetoed = sorted((FLAG2CLS[f], chain) for (f, chain), (acc, _t) in votes.items()
                    if acc == 0 and (FLAG2CLS[f], chain) not in pinned
                    and mined.get((FLAG2CLS[f], chain), 0) < args.threshold)
    args.output.write_text(
        "# class\tchain — refused by apertium-kaz on every representative stem,\n"
        f"# unpinned and attested below {args.threshold} tokens; "
        "tools/audit_apertium.py\n"
        + "\n".join(f"{c}\t{ch}" for c, ch in vetoed) + "\n", encoding="utf-8")
    print(f"{len(votes):,} chains audited, {len(vetoed):,} vetoed → {args.output}",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
