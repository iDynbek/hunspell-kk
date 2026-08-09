# Chromium spellcheck — add kk (two gerrit CLs)

Chromium has no Kazakh dictionary (`chromium/deps/hunspell_dictionaries` has no
kk-*). Two changes are needed; heavier than the other channels because it
requires a Chromium checkout and the Google CLA.

## CL 1 — the dictionary repo
Repo: https://chromium.googlesource.com/chromium/deps/hunspell_dictionaries

1. Chromium stores both the source pair and a compiled `.bdic`. Build the
   converter from a Chromium checkout (`convert_dict` target), then:
   `convert_dict kk-KZ` with `kk_KZ.aff`/`kk_KZ.dic` renamed to `kk-KZ.aff`/`kk-KZ.dic`
   → produces `kk-KZ-1-0.bdic`.
2. CL adds: `kk_KZ.aff`, `kk_KZ.dic`, `kk-KZ-1-0.bdic`, plus a `README_kk_KZ.txt`
   with licence and upstream URL (mirror an existing language's README).
3. Push via `git cl upload` against that repo.

## CL 2 — chrome, register the language
In `chromium/src`: add `kk` to the spellcheck language list in
`components/spellcheck/common/spellcheck_common.cc` (kSupportedSpellCheckerLanguages),
referencing the bdic version added in CL 1. `git cl upload`, mention CL 1 as a
dependency.

## Commit message (both CLs)
```
Add Kazakh (kk) spellcheck dictionary

Kazakh had no dictionary. Source: https://github.com/iDynbek/hunspell-kk
(v0.2.8, GPL-3.0-or-later) — generated two-level affix rules covering full
nominal and verbal inflection; accepts 98.1% of tokens on a million words of
held-out news prose; reproducible measurement harness in the repo.
```

Note: `convert_dict` historically chokes on some UTF-8 affix constructs — test
the produced .bdic in a local Chrome build (spellcheck a Kazakh paragraph)
before uploading. If it fails, file the converter issue first; do not ship an
untested bdic.
