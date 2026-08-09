# ONLYOFFICE — replace the 2009 kk_KZ (GitHub PR)

ONLYOFFICE ships the 2009 dictionary verbatim (`ONLYOFFICE/dictionaries`,
`kk_KZ/` — its .aff starts with the 2009 `SFX A N 45`). Straight replacement PR.

## Steps
1. Fork https://github.com/ONLYOFFICE/dictionaries, branch off `master`.
2. In `kk_KZ/`, replace:
   - `kk_KZ.aff` ← `dict/kk_KZ.aff`
   - `kk_KZ.dic` ← `dict/kk_KZ.dic`
   - `README_kk_KZ.txt` ← `package/README_kk_KZ.txt`
   - keep `kk_KZ.json` as is (`{"codes": [1087]}` — the Kazakh Windows LCID).
3. PR title: `Update Kazakh (kk_KZ) to the actively maintained dictionary`

## PR body
```
The bundled kk_KZ is the 2009 OpenOffice dictionary, whose affix file allows
one suffix per word; on an agglutinative language it rejects most correct text
(82.1% of running-text tokens accepted, 58.2% of distinct words).

This replaces it with https://github.com/iDynbek/hunspell-kk (v0.2.8,
GPL-3.0-or-later): 98.1% / 95.4% on the same held-out news corpus, full
nominal and verbal inflection, and suggestion tables that correct the
Russian-for-Kazakh letter confusions (о/ө, н/ң) and Latin homoglyphs
(үшiн → үшін). Measurements are reproducible from the repo (`make running`,
`make typos`).

kk_KZ.json (LCID 1087) is unchanged.
```
