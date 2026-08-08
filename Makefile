PY ?= python3
KAZSEARCH ?= ../kazsearch-py

.PHONY: help aff check baseline measure negatives clean

help:
	@echo "make aff       generate dict/kk_KZ.aff from the kazsearch layer model"
	@echo "make check     fail if dict/kk_KZ.aff is stale"
	@echo "make baseline  measure the 2009 release"
	@echo "make measure   measure dict/ against the 2009 release"

tests/corpus_cyr.txt:
	$(PY) tools/measure.py baseline/kk_KZ --kazsearch $(KAZSEARCH) >/dev/null

negatives tests/negatives.txt: tests/corpus_cyr.txt
	$(PY) tools/negatives.py tests/corpus_cyr.txt -o tests/negatives.txt

aff:
	$(PY) tools/gen_aff.py --kazsearch $(KAZSEARCH) -o dict/kk_KZ.aff

check:
	$(PY) tools/gen_aff.py --kazsearch $(KAZSEARCH) --check dict/kk_KZ.aff

baseline: tests/negatives.txt
	$(PY) tools/measure.py baseline/kk_KZ --kazsearch $(KAZSEARCH)

measure: tests/negatives.txt
	$(PY) tools/measure.py dict/kk_KZ --against baseline/kk_KZ --kazsearch $(KAZSEARCH)

clean:
	rm -rf tests/corpus_cyr.txt tests/negatives.txt __pycache__ tools/__pycache__
