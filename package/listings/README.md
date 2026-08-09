# Distribution submissions — status and order

Every draft in this directory is ready to file as-is. Numbers are current for
v0.2.8; if a newer release is out, re-check `98.1% / 95.4%`, `2.3%`, `131,289`.

| # | channel | draft | needs | status |
|---|---------|-------|-------|--------|
| 1 | addons.mozilla.org (Firefox/Thunderbird) | `mozilla-amo.md` | Mozilla account | ready — upload `dist/kk_KZ.xpi` (manifest fixed for the 45-char name limit) |
| 2 | extensions.libreoffice.org | `libreoffice-extensions.md` | LibreOffice account | ready — upload `dist/kk_KZ.oxt` |
| 3 | wooorm/dictionaries (npm) | — | — | **filed**: [#97](https://github.com/wooorm/dictionaries/issues/97) + engine issue [nspell#54](https://github.com/wooorm/nspell/issues/54); awaiting maintainer |
| 4 | Debian (`hunspell-kk`) | `debian-bug.md` | email to submit@bugs.debian.org | ready |
| 5 | Fedora (`hunspell-kk`) | `fedora-bug.md` | bugzilla.redhat.com account | ready |
| 6 | LibreOffice bundled (every download, all OSes) | `libreoffice-bundling.md` | gerrit account | ready — files in `../submissions/libreoffice/` |
| 7 | ONLYOFFICE (ships the 2009 dict today) | `onlyoffice.md` | GitHub fork + PR | ready |
| 8 | Chromium spellcheck | `chromium.md` | Chromium checkout + CLA | ready, heaviest — test the .bdic locally first |

Suggested order: 1 and 2 (15 min each, instant reach) → 4 and 5 (a distro
switch also strengthens the case for 6) → 7 (trivial PR, direct replacement)
→ 6 (highest ceiling) → 8 (when you have a Chromium dev setup or a
collaborator who does).
