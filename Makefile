PY ?= python3
KAZSEARCH ?= ../kazsearch-py

.PHONY: help aff check baseline measure clean

help:
	@echo "make aff       generate dict/kk_KZ.aff from the kazsearch layer model"
	@echo "make check     fail if dict/kk_KZ.aff is stale"
	@echo "make baseline  measure the 2009 release"
	@echo "make measure   measure dict/ against the 2009 release"

aff:
	$(PY) tools/gen_aff.py --kazsearch $(KAZSEARCH) -o dict/kk_KZ.aff

check:
	$(PY) tools/gen_aff.py --kazsearch $(KAZSEARCH) --check dict/kk_KZ.aff

baseline:
	$(PY) tools/measure.py baseline/kk_KZ --kazsearch $(KAZSEARCH)

measure:
	$(PY) tools/measure.py dict/kk_KZ --against baseline/kk_KZ --kazsearch $(KAZSEARCH)

clean:
	rm -rf tests/corpus_cyr.txt __pycache__ tools/__pycache__
