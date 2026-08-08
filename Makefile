PY ?= python3
KAZSEARCH ?= ../kazsearch-py
APERTIUM  ?= ../apertium-kaz/apertium-kaz.kaz.lexc
KAZDICT   ?= ../kazdict/data/build/kazdict.db

.PHONY: help dict aff dic check data lexicon residues prune negatives baseline measure clean

help:
	@echo "make dict      generate dict/kk_KZ.aff and dict/kk_KZ.dic"
	@echo "make check     fail if dict/kk_KZ.aff is stale"
	@echo "make measure   measure dict/ against the 2009 release"
	@echo "make baseline  measure the 2009 release on its own"
	@echo "make data      rebuild everything under data/ (needs a corpus and the sources)"

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
	$(MAKE) lexicon
	$(MAKE) residues
	$(MAKE) aff
	$(MAKE) prune
	$(MAKE) dic

lexicon:
	$(PY) tools/build_lexicon.py --apertium $(APERTIUM) --kazdict $(KAZDICT) \
		-o data/lexicon.tsv

tests/corpus_cyr.txt:
	$(PY) tools/measure.py baseline/kk_KZ --kazsearch $(KAZSEARCH) >/dev/null

residues: tests/corpus_cyr.txt
	$(PY) tools/mine_residues.py --kazsearch $(KAZSEARCH) -o data/residues.tsv

prune: tests/corpus_cyr.txt
	$(PY) tools/prune.py --kazsearch $(KAZSEARCH) -o data/prune.txt

negatives tests/negatives.txt: tests/corpus_cyr.txt
	$(PY) tools/negatives.py tests/corpus_cyr.txt -o tests/negatives.txt

baseline: tests/negatives.txt
	$(PY) tools/measure.py baseline/kk_KZ --kazsearch $(KAZSEARCH)

measure: tests/negatives.txt
	$(PY) tools/measure.py dict/kk_KZ --against baseline/kk_KZ --kazsearch $(KAZSEARCH)

clean:
	rm -rf tests/corpus_cyr.txt tests/negatives.txt __pycache__ tools/__pycache__
