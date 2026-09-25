# bQRLG

Python tools for representing automata with binary decision diagrams and building related Qiskit circuits.

## Requirements

- Python 3.10 or newer
- [uv](https://docs.astral.sh/uv/)

## Install and run

From the repository root, sync the project environment and dependencies:

```sh
uv sync
```

Run the example configured in `src/bqrlg/__main__.py` with either command:

```sh
uv run bqrlg
uv run python -m bqrlg
```

The project can also be imported as a package. For example:

```python
from bqrlg import EFAQ, bqrlg_parallel
```

The implementation lives under `src/bqrlg/`. Example circuits and demonstrations are in `src/bqrlg/examples.py`; `tests/` is reserved for automated tests.
