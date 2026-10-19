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
    efaq,
    bound=2,
    amplification_schedule=["fnr", "grover"],
    fnr_iterations=2,
    reject_state="00",  # Must match your automaton's reject encoding
)
```

`grover_iterations` and `fnr_iterations` control the repetitions in stages
that select their respective operation. The previous boolean amplification
flags have been removed; callers must use a schedule instead.

## Automaton encoding and validation

NFAs must have nonempty state and symbol sets and valid transition endpoints.
Missing transitions go to an absorbing rejecting sink (reusing one when
available). Spare nondeterministic choice codes repeat valid successors
cyclically, so they cannot introduce new accepted words. This policy preserves
the language but need not sample successors uniformly.

State, symbol, and choice assignments are sorted for reproducibility. Explicit
binary encodings must be unique, have the declared width, and cover all DFA
states, including any generated rejecting sink. Unused binary state/symbol
codes transition to that sink. Singleton alphabets and deterministic choices
use empty bit strings; state registers retain at least one qubit. The encoded
reject state is exposed as `efaq.reject_state` and used by default for FnR when
available. Construction does not mutate supplied encodings or DFA transitions.

`bqrlg_series` is not implemented and raises `NotImplementedError` rather than
returning an empty circuit. Serial scratch reuse and synthesis shared across
multiple output bits remain future optimizations.

Python 3.10 is supported; the dependency resolver selects a compatible `dd`
release (the regression suite is checked with `dd` 0.5.7 on Python 3.10).
