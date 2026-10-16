.DEFAULT_GOAL := help
PYTHON ?= python3
.PHONY: help test check
help:
	@printf '%s\n' 'test: deterministic unit and integration tests' 'check: tests and Kit project validation'
test:
	$(PYTHON) -m unittest discover -s tests -v
check: test
	kit check --project
	kit check --all
