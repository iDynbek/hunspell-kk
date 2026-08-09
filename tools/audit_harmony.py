"""Override each stem's vowel harmony where apertium-kaz disagrees with kkphon.

`kkphon.harmony` reads the last committing vowel of the stem, which is right for
native words but wrong for many loanwords: `артиллерия` has an internal `е`, so
it is read front, yet it inflects back — `артиллериясы`, not `*артиллериясі`.
`мине_harmony.py` catches the ones the corpus attests; this catches the rest by
asking the analyzer directly.

For each stem a genitive is built in both harmonies with the same linking
consonant (`артиллерияның` vs `артиллериянің`), differing only in the vowel that
carries harmony. apertium-kaz gives one a clean analysis and the other an
`err_orth`; that settles the harmony. Stems it cannot analyse either way, or
analyses both, are left to kkphon.

    python tools/audit_harmony.py -o data/harmony.tsv

Needs the analyzer in the `apertium` distrobox (see tools/audit_apertium.py).
Merges into the existing data/harmony.tsv rather than replacing it, so the
corpus-mined overrides survive.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gen_dic import read_lexicon  # noqa: E402
from kkphon import (BACK_VOWELS, FINAL_N, FINAL_R, FINAL_V, FINAL_Z,  # noqa: E402
                    FRONT_VOWELS, final_class, harmony)

ROOT = Path(__file__).resolve().parent.parent
LOOKUP = "hfst-lookup -q /usr/share/apertium/apertium-kaz/kaz.automorf.hfst"

# Unambiguously harmony-committing inflectional endings, back and front. Checked
# as exact `stem + ending` forms rather than as a prefix, so `археология` is not
# mistaken for an inflection of `археолог`.
BACK_ENDINGS = ("тар", "дар", "лар", "ты", "ды", "ны", "ға", "қа", "да", "та",
                "нан", "дан", "тан", "ның", "дың", "тың", "мыз", "мын", "сың")
FRONT_ENDINGS = ("тер", "дер", "лер", "ті", "ді", "ні", "ге", "ке", "де", "те",
                 "нен", "ден", "тен", "нің", "дің", "тің", "міз", "мін", "сің")


def attested_harmonies(stem: str, corpus: set[str]) -> set[str]:
    """Every harmony the corpus is seen inflecting a stem in.

    apertium-kaz's lexicon and real usage disagree on some loanwords — it calls
    `археолог` front, the corpus writes `археологтар`. Some loanwords the corpus
    writes both ways (`педагогтар` and `педагогтер`). Either way an override away
    from a harmony the corpus actually uses would reject real text, so the rule
    is: never overrule the corpus, only fill in where it is silent. The ending
    has to open the suffix, so `археологтардың` counts for `археолог` but the
    separate word `археология` does not.
    """
    out: set[str] = set()
    for word in corpus:
        if not word.startswith(stem) or len(word) <= len(stem):
            continue
        suffix = word[len(stem):]
        if suffix.startswith(BACK_ENDINGS):
            out.add("b")
        elif suffix.startswith(FRONT_ENDINGS):
            out.add("f")
    return out


def probes(stem: str) -> tuple[str, str]:
    """The genitive in back and front harmony, same linking consonant."""
    fc = final_class(stem)
    c = "н" if fc in (FINAL_V, FINAL_N) else "д" if fc in (FINAL_R, FINAL_Z) else "т"
    return stem + c + "ың", stem + c + "ің"


def clean(analyses: list[str]) -> bool:
    return any(not a.endswith("+?") and "err" not in a for a in analyses)


def analyze(words: list[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for i in range(0, len(words), 40000):
        chunk = words[i:i + 40000]
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt",
                                         dir=Path.home(), delete=False) as fh:
            fh.write("\n".join(chunk))
            path = fh.name
        try:
            proc = subprocess.run(
                ["distrobox", "enter", "apertium", "--", "bash", "-c",
                 f"{LOOKUP} < {path}"],
                capture_output=True, text=True, timeout=590)
        finally:
            Path(path).unlink(missing_ok=True)
        for line in proc.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                out.setdefault(parts[0], []).append(parts[1])
    return out


def read_existing(path: Path) -> tuple[list[str], dict[str, str]]:
    if not path.exists():
        return ["# stem\tharmony"], {}
    header, data = [], {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            header.append(line)
        elif line:
            stem, value = line.split("\t")
            data[stem] = value
    return header, data


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", type=Path, default=ROOT / "data/harmony.tsv")
    ap.add_argument("--lexicon", type=Path, default=ROOT / "data/lexicon.tsv")
    ap.add_argument("--kaznerd", type=Path, default=ROOT.parent / "KazNERD/KazNERD",
                    help="corpus that overrules apertium where the two disagree")
    ap.add_argument("--dry-run", action="store_true",
                    help="report the disagreements without writing")
    args = ap.parse_args()

    header, existing = read_existing(args.output)
    lexicon = sorted(w for w in read_lexicon(args.lexicon) if len(w) >= 3)

    corpus: set[str] = set()
    if args.kaznerd.exists():
        from measure_running import tokens
        corpus = {w.lower() for w in tokens(args.kaznerd, "*")}
        print(f"{len(corpus):,} corpus tokens to overrule apertium", file=sys.stderr)

    forms: list[str] = []
    for w in lexicon:
        forms.extend(probes(w))
    print(f"{len(lexicon):,} stems, {len(forms):,} probes", file=sys.stderr)
    ana = analyze(forms)

    found: dict[str, str] = {}
    for w in lexicon:
        back, front = probes(w)
        b, f = clean(ana.get(back, [])), clean(ana.get(front, []))
        if b == f:                      # both or neither — apertium is no help
            continue
        verdict = "b" if b else "f"
        if verdict == harmony(w):       # apertium agrees with kkphon, nothing to do
            continue
        if harmony(w) in attested_harmonies(w, corpus):
            continue                     # the corpus uses kkphon's harmony; leave it
        found[w] = verdict

    new = {w: v for w, v in found.items() if existing.get(w) != v}
    print(f"{len(found):,} stems apertium re-harmonises, {len(new):,} new/changed",
          file=sys.stderr)
    for w in list(new)[:25]:
        print(f"  {w}: {harmony(w)} -> {new[w]}", file=sys.stderr)

    if args.dry_run:
        return 0

    existing.update(found)
    body = "\n".join(f"{k}\t{v}" for k, v in sorted(existing.items()))
    args.output.write_text("\n".join(header) + "\n" + body + "\n", encoding="utf-8")
    print(f"{len(existing):,} overrides -> {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
