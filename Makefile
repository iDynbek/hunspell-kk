PY ?= python3
KAZSEARCH ?= ../kazsearch-py

.PHONY: help dict aff dic check residues negatives baseline measure clean

help:
	@echo "make dict      generate dict/kk_KZ.aff and dict/kk_KZ.dic"
	@echo "make check     fail if dict/kk_KZ.aff is stale"
	@echo "make residues  re-mine data/residues.tsv (needs a corpus)"
	@echo "make baseline  measure the 2009 release"
	@echo "make measure   measure dict/ against the 2009 release"

dict: aff dic

aff:
	$(PY) tools/gen_aff.py --kazsearch $(KAZSEARCH) -o dict/kk_KZ.aff

dic:
	$(PY) tools/gen_dic.py -o dict/kk_KZ.dic

check:
	$(PY) tools/gen_aff.py --kazsearch $(KAZSEARCH) --check dict/kk_KZ.aff

tests/corpus_cyr.txt:
	$(PY) tools/measure.py baseline/kk_KZ --kazsearch $(KAZSEARCH) >/dev/null

residues: tests/corpus_cyr.txt
	$(PY) tools/mine_residues.py --kazsearch $(KAZSEARCH) -o data/residues.tsv

negatives tests/negatives.txt: tests/corpus_cyr.txt
	$(PY) tools/negatives.py tests/corpus_cyr.txt -o tests/negatives.txt

baseline: tests/negatives.txt
	$(PY) tools/measure.py baseline/kk_KZ --kazsearch $(KAZSEARCH)

measure: tests/negatives.txt
	$(PY) tools/measure.py dict/kk_KZ --against baseline/kk_KZ --kazsearch $(KAZSEARCH)

clean:
	rm -rf tests/corpus_cyr.txt tests/negatives.txt __pycache__ tools/__pycache__
