PY := python3
export PYTHONPATH := src

.PHONY: help test audit contacts ga unsc ga-window unsc-window sql clean

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

ga-window: ## GA voting analysis restricted to 2021-2026
	$(PY) -m rcwatch ga --since 2021-01-01 | tee out/ga_rus_chn_2021_2026.json

unsc-window: ## Security Council analysis restricted to 2021-2026
	$(PY) -m rcwatch unsc --since 2021-01-01 | tee out/unsc_rus_chn_2021_2026.json

sql:       ## emit the GDELT BigQuery contact-series SQL
	$(PY) -m rcwatch gdelt-sql

clean:
	rm -rf out/cache __pycache__ .pytest_cache src/rcwatch/__pycache__ tests/__pycache__
