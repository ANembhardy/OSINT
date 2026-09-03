PY := python3
export PYTHONPATH := src

.PHONY: help test audit contacts ga unsc sql clean

help:
	@grep -E '^[a-z-]+:.*?##' $(MAKEFILE_LIST) | sed 's/:.*##/\t/'

test:      ## run the offline test suite
	pytest tests -q

audit:     ## provenance audit of the seed data
	$(PY) -m rcwatch audit

contacts:  ## leader-level contact indicators (measure M5)
	$(PY) -m rcwatch contacts --level leader

ga:        ## Russia-China General Assembly voting analysis (M1-M3)
	$(PY) -m rcwatch ga | tee out/ga_rus_chn.json

unsc:      ## Russia-China Security Council voting analysis (M4)
	$(PY) -m rcwatch unsc | tee out/unsc_rus_chn.json

sql:       ## emit the GDELT BigQuery contact-series SQL
	$(PY) -m rcwatch gdelt-sql

clean:
	rm -rf out/cache __pycache__ .pytest_cache src/rcwatch/__pycache__ tests/__pycache__
