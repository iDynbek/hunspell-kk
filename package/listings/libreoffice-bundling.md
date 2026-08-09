# LibreOffice bundled dictionaries — gerrit submission

Goal: ship kk_KZ inside every LibreOffice download. kk has never been bundled;
distros package the 2009 extension separately. Repo: `libreoffice/dictionaries`
(gerrit, GitHub is a read-only mirror; PRs are rejected there).

## One-time setup
1. Account at https://gerrit.libreoffice.org (can log in with GitHub).
2. `git clone https://gerrit.libreoffice.org/dictionaries && cd dictionaries`
3. Install the commit-msg hook: `scp -p -P 29418 <user>@gerrit.libreoffice.org:hooks/commit-msg .git/hooks/`
   (or copy it from the gerrit web UI's clone instructions).

## The change
Layout mirrors the other languages (see `bo/` for a minimal one):

```
kk_KZ/
  kk_KZ.aff            <- dict/kk_KZ.aff
  kk_KZ.dic            <- dict/kk_KZ.dic
  README.md            <- package/submissions/libreoffice/README.md
  description.xml      <- package/description.xml
  dictionaries.xcu     <- package/dictionaries.xcu
  META-INF/manifest.xml <- package/META-INF/manifest.xml
Dictionary_kk.mk       <- package/submissions/libreoffice/Dictionary_kk.mk
```

Also add `Dictionary_kk` to `Module_dictionaries.mk` (alphabetical). The
core-repo side (scp2/postprocess registration) is usually done by the reviewer
or as a follow-up — mention in the commit message that core changes are needed
and offer to do them. Recent template to crib from: any `Add ... dictionary`
commit in the repo's log.

## Commit message
```
Add Kazakh (kk_KZ) dictionary

Kazakh has never been bundled; the dictionary in circulation is a 2009
OpenOffice extension whose affix file allows one suffix per word, rejecting
most correct text of an agglutinative language (82.1% of running-text tokens
accepted, 58.2% of types). This dictionary generates the suffix chains the
language uses: 98.1% / 95.4% on a million words of held-out news prose, full
nominal and verbal inflection, suggestion tables for the Russian-for-Kazakh
and Latin-homoglyph confusions. GPL-3.0-or-later.

Upstream, with reproducible measurements: https://github.com/iDynbek/hunspell-kk
```

4. `git add -A && git commit` (hook adds Change-Id), then
   `git push origin HEAD:refs/for/master`.
5. Review happens on gerrit; expect a licensing question — answer: baseline
   carried forward under its GPL-2.0-or-later option, apertium-kaz GPL-3.0,
   whole GPL-3.0-or-later; hu_HU in the same repo is also GPL.
