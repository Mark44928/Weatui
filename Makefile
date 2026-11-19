.PHONY: check test

check:
	ruff check .
	python3 -m pytest -q
	python3 -m weatui --version
	python3 -m weatui --list-cities

test: check
