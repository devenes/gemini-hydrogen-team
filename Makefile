.PHONY: install ui-build web adk-web doctor test test-live lint clean

PYTHON := .venv/bin/python
PYTEST := .venv/bin/pytest
RUFF := .venv/bin/ruff
CLI := .venv/bin/hydrogen-team

install:
	uv venv --python 3.13 .venv
	uv pip install --python $(PYTHON) -e ".[dev]"
	cd web && npm install

ui-build:
	cd web && npm run build

web:
	$(CLI) web

adk-web:
	$(CLI) adk-web

doctor:
	$(CLI) doctor

test:
	$(PYTEST) -m "not live"

test-live:
	$(PYTEST) -m live -s

lint:
	$(RUFF) check src tests

clean:
	rm -rf dist build .pytest_cache .ruff_cache src/hydrogen_team/static
