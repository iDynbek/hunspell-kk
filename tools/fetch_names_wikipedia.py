"""Fetch Kazakh given names and surnames from Kazakh Wikipedia.

KazNERD supplies the names that appear in news text, which is a biased sample:
it is heavy on politicians and place names and thin on ordinary given names.
Kazakh Wikipedia carries the other kind — lists of the most common personal
names and surnames in Kazakhstan, each with the number of people who bear it,
compiled from the National Statistics Bureau's own release.

Fifteen thousand male names, fifteen thousand female, and ten thousand
surnames, in the spelling official documents use. That spelling matters: the
lists have `Серик` and `Нурлан` beside `Серік` and `Нұрлан`, and the Russified
forms are what people actually type.

Bearer counts are kept so the tail can be cut. A name held by three people in
the country is not one a spellchecker should silently accept, and the long tail
of these lists is mostly transliteration variants of the head.

    python tools/fetch_names_wikipedia.py -o data/names_wp.txt

Kazakh Wikipedia is CC-BY-SA-4.0; the underlying figures are from the
Statistics Bureau of the Republic of Kazakhstan.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://kk.wikipedia.org/w/api.php"

PAGES = [
    "Қазақстан қазақтарының ер есімдерінің тізімі",
    "Қазақстан қазақтарының ер есімдерінің тізімі (5001-10000)",
    "Қазақстан қазақтарының ер есімдерінің тізімі (10001-15000)",
    "Қазақстан қазақтарының әйел есімдерінің тізімі",
    "Қазақстан қазақтарының әйел есімдерінің тізімі (5001-10000)",
    "Қазақстан қазақтарының әйел есімдерінің тізімі (10001-15000)",
    "Қазақстан қазақтарының унисекс есімдері тізімі",
    "Қазақстан қазақтарының фамилиялары тізімі",
    "Қазақстан қазақтарының фамилиялары тізімі (5001-10000)",
]

# `| [[Азамат]] || 63 818` — the name is a wikilink, the count may be spaced.
ROW = re.compile(r"\|\s*\[\[([^\]|]+?)(?:\|[^\]]*)?\]\]\s*\|\|\s*([\d\s ]+)")
CYRILLIC_WORD = re.compile(r"^[Ѐ-ӿ]+$")


def wikitext(page: str) -> str:
    url = f"{API}?" + urllib.parse.urlencode(
        {"action": "parse", "page": page, "prop": "wikitext", "format": "json"})
    request = urllib.request.Request(
        url, headers={"User-Agent": "hunspell-kk/0.1 (dictionary build)"})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    if "error" in payload:
        raise LookupError(f"{page}: {payload['error'].get('info')}")
    return payload["parse"]["wikitext"]["*"]


def names(text: str) -> dict[str, int]:
    out = {}
    for name, count in ROW.findall(text):
        name = name.strip()
        if CYRILLIC_WORD.match(name) and len(name) > 2:
            bearers = int(re.sub(r"[^\d]", "", count) or 0)
            out[name] = max(out.get(name, 0), bearers)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--output", type=Path, default=ROOT / "data/names_wp.txt")
    ap.add_argument("--min-bearers", type=int, default=50,
                    help="drop names fewer people than this are called")
    args = ap.parse_args()

    everyone: dict[str, int] = {}
    for page in PAGES:
        try:
            found = names(wikitext(page))
        except Exception as exc:                              # network, rename
            print(f"  skipped {page}: {exc}", file=sys.stderr)
            continue
        print(f"  {len(found):>6,}  {page}", file=sys.stderr)
        for name, bearers in found.items():
            everyone[name] = max(everyone.get(name, 0), bearers)

    if not everyone:
        sys.exit("nothing fetched")

    kept = sorted(n.lower() for n, b in everyone.items() if b >= args.min_bearers)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "# Kazakh given names and surnames from kk.wikipedia.org (CC-BY-SA-4.0),\n"
        "# after the Statistics Bureau of the Republic of Kazakhstan.\n"
        f"# via tools/fetch_names_wikipedia.py --min-bearers {args.min_bearers}\n"
        + "\n".join(kept) + "\n", encoding="utf-8")
    print(f"\n{len(everyone):,} names, {len(kept):,} borne by {args.min_bearers}+ "
          f"people → {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
