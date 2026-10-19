.PHONY: run sync lint test test-encoding test-bdd test-grover test-fnr test-figure14

TEST_ARGS ?=
TEST_RUNNER = uv run python -m unittest discover -s tests -v

run:
	uv run bqrlg

sync:
	uv sync

lint:
	uv run ruff check . --fix
	uv run ruff format .

test:
	$(TEST_RUNNER) $(TEST_ARGS)

test-encoding:
	$(TEST_RUNNER) -p "test_encoding.py" $(TEST_ARGS)

test-bdd:
	$(TEST_RUNNER) -p "test_bdd_synthesis.py" $(TEST_ARGS)

test-grover:
	$(TEST_RUNNER) -p "test_grover.py" $(TEST_ARGS)

test-fnr:
	$(TEST_RUNNER) -p "test_fnr.py" $(TEST_ARGS)

test-figure14:
	$(TEST_RUNNER) -p "test_figure14.py" $(TEST_ARGS)
