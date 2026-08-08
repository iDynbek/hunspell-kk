PY ?= python3
KAZSEARCH ?= ../kazsearch-py
APERTIUM  ?= ../apertium-kaz/apertium-kaz.kaz.lexc
KAZDICT   ?= ../kazdict/data/build/kazdict.db
KAZNLP    ?= ../kaznlp/kaznlp/morphology/mdl/sfx
KAZNERD   ?= ../KazNERD/KazNERD

.PHONY: help dict aff dic check data lexicon names names-wp paradigm typos chains harmony corpus residues prune negatives baseline measure scoped running dist clean

help:
	@echo "make dict      generate dict/kk_KZ.aff and dict/kk_KZ.dic"
	@echo "make check     fail if dict/kk_KZ.aff is stale"
	@echo "make measure   measure dict/ against the 2009 release"
	@echo "make baseline  measure the 2009 release on its own"
	@echo "make typos     the metric that matters: does it CATCH misspellings"
	@echo "make running   measure on real running text, weighted by word frequency"
	@echo "make paradigm  check the full nominal grid of one stem per class"
	@echo "make scoped    measure per source scope: modern, glossing, historical"
	@echo "make data      rebuild everything under data/ (needs the sources)"
	@echo "make dist      package dist/kk_KZ.oxt for LibreOffice"

# Building the dictionary needs only this repository: everything corpus-derived
# is committed under data/.
dict: aff dic

aff:
	$(PY) tools/gen_aff.py --kazsearch $(KAZSEARCH) -o dict/kk_KZ.aff

dic:
	$(PY) tools/gen_dic.py -o dict/kk_KZ.dic

check:
	$(PY) tools/gen_aff.py --kazsearch $(KAZSEARCH) --check dict/kk_KZ.aff

# Rebuilding data/ needs the corpus and the wordlist sources. The order is not
# arbitrary: residues are mined against the lexicon, and what is safe to prune
# depends on what the affix file built from those residues can regenerate.
data:
	$(MAKE) names
	$(MAKE) names-wp
	$(MAKE) lexicon
	$(MAKE) chains
	$(MAKE) residues
	$(MAKE) paradigm
	$(MAKE) aff
	$(MAKE) harmony
	$(MAKE) prune
	$(MAKE) dic

lexicon:
	$(PY) tools/build_lexicon.py --apertium $(APERTIUM) --kazdict $(KAZDICT) \
		-o data/lexicon.tsv

chains:
	$(PY) tools/import_chains.py --sfx $(KAZNLP) -o data/chains.tsv

tests/corpus_cyr.txt:
	$(PY) tools/measure.py baseline/kk_KZ --kazsearch $(KAZSEARCH) >/dev/null

# Tokens with the scope of the edition they came from, so a headline number can
# mean "modern Kazakh" rather than an average over Chagatai poetry.
corpus tests/corpus.tsv:
	$(PY) tools/build_corpus.py --kazdict $(KAZDICT) -o tests/corpus.tsv

residues: tests/corpus_cyr.txt
	$(PY) tools/mine_residues.py --kazsearch $(KAZSEARCH) -o data/residues.tsv

# Loanword harmony, which no rule over the letters recovers: банк takes
# банктен, конференция takes конференцияда.
# Corpus recall cannot tell "the language does not do this" from "the corpus
# did not happen to". The nominal grid is closed, so it can.
paradigm:
	$(PY) tools/paradigm.py --write tests/paradigms.tsv \
		--residues data/paradigm.tsv dict/kk_KZ
	$(PY) tools/verb_paradigm.py --write tests/verb_paradigms.tsv \
		--residues data/verb_paradigm.tsv dict/kk_KZ

harmony: tests/corpus_cyr.txt
	$(PY) tools/mine_harmony.py --kazsearch $(KAZSEARCH) --kaznerd $(KAZNERD) \
		-o data/harmony.tsv

prune: tests/corpus_cyr.txt
	$(PY) tools/prune.py --kazsearch $(KAZSEARCH) -o data/prune.txt

negatives tests/negatives.txt: tests/corpus_cyr.txt
	$(PY) tools/negatives.py tests/corpus_cyr.txt -o tests/negatives.txt

baseline: tests/negatives.txt
	$(PY) tools/measure.py baseline/kk_KZ --kazsearch $(KAZSEARCH)

# What a reader would actually see: real prose, each word weighted by how
# often it occurs, rather than a dictionary's word types counted once each.
# The test split only: names are mined from KazNERD's training split, so
# scoring on the whole corpus would be scoring on what was memorised.
# A spellchecker exists to catch mistakes. Recall says how rarely it underlines
# correct text; this says how often it does its job. The 2009 release catches
# 99.0%, and it is shown alongside because being below it is the thing to know.
typos: tests/corpus_cyr.txt
	$(PY) tools/typos.py --write tests/typos.txt dict/kk_KZ baseline/kk_KZ

running:
	$(PY) tools/measure_running.py dict/kk_KZ baseline/kk_KZ \
		--kaznerd $(KAZNERD) --split test --show-misses 10

names:
	$(PY) tools/mine_names.py --kaznerd $(KAZNERD) --kazsearch $(KAZSEARCH) \
		-o data/names.txt

# Given names and surnames from Kazakh Wikipedia, after the Statistics
# Bureau's figures. Needs network; the result is committed.
names-wp:
	$(PY) tools/fetch_names_wikipedia.py -o data/names_wp.txt

scoped: tests/corpus.tsv tests/negatives.txt
	$(PY) tools/measure.py dict/kk_KZ --against baseline/kk_KZ \
		--corpus tests/corpus.tsv --scoped

measure: tests/negatives.txt
	$(PY) tools/measure.py dict/kk_KZ --against baseline/kk_KZ --kazsearch $(KAZSEARCH)

# A LibreOffice extension is a zip with the dictionary, a registration file
# telling it which locales the pair serves, and a manifest naming that file.
dist: dict
	@rm -rf dist && mkdir -p dist/build/META-INF
	cp dict/kk_KZ.aff dict/kk_KZ.dic dist/build/
	cp package/description.xml package/dictionaries.xcu \
		package/README_kk_KZ.txt COPYING dist/build/
	cp package/META-INF/manifest.xml dist/build/META-INF/
	cd dist/build && zip -q -r ../kk_KZ.oxt . && cd ../..
	@rm -rf dist/build
	@ls -l dist/kk_KZ.oxt

clean:
	rm -rf dist tests/corpus_cyr.txt tests/corpus.tsv tests/negatives.txt __pycache__ tools/__pycache__
