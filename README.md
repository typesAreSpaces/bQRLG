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

## Amplification schedules

`bqrlg_parallel` uses one schedule entry per automaton step: `"none"`,
`"grover"`, or `"fnr"`. Omitting the schedule disables amplification.
Amplification settings are keyword-only.

```python
qc = bqrlg_parallel(efaq, bound=2)  # No amplification
qc = bqrlg_parallel(efaq, bound=2, amplification_schedule=["grover"] * 2)
qc = bqrlg_parallel(efaq, bound=2, amplification_schedule=["fnr"] * 2)
qc = bqrlg_parallel(
    efaq, bound=2,
    amplification_schedule=["fnr", "grover"],
    fnr_iterations=2,
    reject_state="00",  # Must match your automaton's reject encoding
)
```

`grover_iterations` and `fnr_iterations` control the repetitions in stages
that select their respective operation. The previous boolean amplification
flags have been removed; callers must use a schedule instead.
