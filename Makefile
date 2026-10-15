.PHONY: run sync lint

run:
	uv run bqrlg

sync:
	uv sync

lint:
	uv run ruff check . --fix
	uv run ruff format .
