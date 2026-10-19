from collections.abc import Sequence
from itertools import pairwise

from dd.autoref import BDD
from dd.autoref import Function as Node
from qiskit import ClassicalRegister as CR
from qiskit import QuantumCircuit as QC
from qiskit import QuantumRegister as QR

from .bdd_to_qc import bdd_to_qc
from .encoding_automata import EFAQ


# The input qubits are the first |u.support| qubits
# the rest are ancilla bits
# except the last one which holds the next_state, then
# swaps it with the first one to hold the previous_state
def step_forward_backward(bdd: BDD, u: Node, use_blocks_q: bool) -> QC:
    step_forward = bdd_to_qc(bdd, u, False)
    # BDD synthesis uses self-inverse X, CX, and CCX gates.
    step_backward = step_forward.reverse_ops()
    num_qubits = step_forward.num_qubits
    qc = QC(num_qubits)

    if use_blocks_q:
        step_forward = step_forward.to_gate()
        step_backward = step_backward.to_gate()
        step_forward.name = "Step forward"
        step_backward.name = "Step backward"

    qc.add_register(QR(1))
    qc.compose(step_forward, range(num_qubits), inplace=True)
    qc.cx(num_qubits - 1, num_qubits)
    qc.compose(step_backward, range(num_qubits), inplace=True)
    qc.swap(0, num_qubits)

    return qc


def delta_to_bdds(efaq: EFAQ) -> tuple[BDD, list[Node]]:
    n = efaq.num_bits_states
    num_vars = efaq.num_bits_states + efaq.num_bits_symbols + efaq.num_bits_ndcs

    bdd = BDD()
    variables = [f"x{i}" for i in range(num_vars)]
    bdd.declare(*variables)

    formulas = [bdd.false for _ in range(n)]

    # Build each input cube once, sharing it across all output formulas.
    for _input, _output in efaq.delta.items():
        if (
            len(_input) != num_vars
            or len(_output) != num_vars
            or any(bit not in "01" for bit in _input + _output)
            or _output[n:] != _input[n:]
        ):
            raise ValueError(
                "EFAQ transitions must preserve inputs and match the declared bit widths"
            )
        cube = bdd.true
        for var, bit in zip(variables, _input):
            cube &= bdd.var(var) if bit == "1" else ~bdd.var(var)
        for i, bit in enumerate(_output[:n]):
            if bit == "1":
                formulas[i] |= cube

    return (bdd, formulas)


def _phase_flip_all_ones(qc: QC, positions: list[int]) -> None:
    """Apply a phase of -1 exactly when all listed qubits are one."""
    if len(positions) == 1:
        qc.z(positions[0])
    else:
        target = positions[-1]
        qc.h(target)
        qc.mcx(positions[:-1], target)
        qc.h(target)


def _flip_and_rotate(qc: QC, flag: int, positions: list[int]) -> None:
    """Conditionally flip the first input bit, then rotate its value to the end.

    On two input bits this is exactly Figure 12: CX followed by CSWAP.
    The ordered input register contains the symbol bits followed by NDC bits.
    """
    qc.cx(flag, positions[0])
    for left, right in pairwise(positions):
        qc.cswap(flag, left, right)


# Observations:
# - Fig. 11 from the original paper suggest the working bits
# for each BDD are placed in parallel
def bqrlg_parallel(
    efaq: EFAQ,
    bound: int,
    add_barrier_q: bool = False,
    *,
    amplification_schedule: Sequence[str] | None = None,
    grover_iterations: int = 1,
    fnr_iterations: int = 1,
    reject_state: str | None = None,
) -> QC:
    """Generate exactly ``bound`` symbols, optionally amplifying before each update.

    Grover marks prospective accepting states, uncomputes the BDD workspace,
    then diffuses only the current symbol/NDC register. A separate computation
    advances the state afterward. One iteration reproduces the paper's example;
    more iterations can overshoot and do not guarantee better acceptance.

    FnR computes the prospective state, records a match to ``reject_state``
    (all zeros by default), uncomputes, then conditionally flips and rotates the
    symbol/NDC register. Every iteration retains a fresh rejection flag. The
    caller must choose the designated reject state; it is not inferred from the
    accepting states. FnR does not guarantee an accepting outcome.

    ``amplification_schedule`` optionally chooses "none", "grover", or "fnr"
    for each stage, e.g. ("fnr", "grover") for Figure 14. Omitting the schedule
    applies no amplification. A supplied schedule must contain ``bound`` entries.
    """
    if bound < 0:
        raise ValueError("bound must be nonnegative")
    if grover_iterations < 0:
        raise ValueError("grover_iterations must be nonnegative")
    if fnr_iterations < 0:
        raise ValueError("fnr_iterations must be nonnegative")
    if amplification_schedule is not None:
        if len(amplification_schedule) != bound or any(
            mode not in {"none", "grover", "fnr"} for mode in amplification_schedule
        ):
            raise ValueError(
                "amplification_schedule needs one none/grover/fnr entry per stage"
            )
        schedule = tuple(amplification_schedule)
    else:
        schedule = ("none",) * bound
    if reject_state is None:
        reject_state = getattr(efaq, "reject_state", None) or "0" * efaq.num_bits_states
    if "fnr" in schedule and (
        len(reject_state) != efaq.num_bits_states
        or any(bit not in "01" for bit in reject_state)
    ):
        raise ValueError("reject_state must be a binary encoding of the state width")

    (bdd, formulas) = delta_to_bdds(efaq)

    forward_qcs = [bdd_to_qc(bdd, formula, False) for formula in formulas]
    # Reversing gate order undoes these self-inverse BDD gates.
    backward_qcs = [qc.reverse_ops() for qc in forward_qcs]

    num_bits_states = efaq.num_bits_states
    # assert num_bits_states == len(forward_qcs)
    num_bits_input = num_bits_states + efaq.num_bits_symbols + efaq.num_bits_ndcs
    curr_total = num_bits_states
    position_working_bits = []
    for qc in forward_qcs:
        working_bits = qc.num_qubits - num_bits_input
        position_working_bits.append(range(curr_total, curr_total + working_bits))
        curr_total += working_bits

    # The first efaq.num_bits_states are for encoding the state
    # The rest are working bits for each forward_qcs
    qc = QC(curr_total)
    # Prepare input for k0
    k0 = efaq.initial_state
    for i, initial_bit in enumerate(k0):
        if initial_bit == "1":
            qc.x(i)

    # Simulate \delta over
    # a string of size `bound'
    new_symbol_todo_bits = efaq.num_bits_symbols + efaq.num_bits_ndcs
    position_raw_symbols_bits = []
    position_symbols_bits = []

    for stage in range(bound):
        position_state_output_bits = []
        curr_qc_size = qc.num_qubits
        qc.add_register(QR(new_symbol_todo_bits))

        # --------------------------------------------------------------------
        # Process each state output bit

        position_raw_symbols_bits.append(
            range(curr_qc_size, curr_qc_size + efaq.num_bits_symbols)
        )
        position_symbols_bits.append(
            range(curr_qc_size, curr_qc_size + new_symbol_todo_bits)
        )

        stage_mode = schedule[stage]
        if stage_mode != "none" and new_symbol_todo_bits:
            input_positions = list(
                range(curr_qc_size, curr_qc_size + new_symbol_todo_bits)
            )
            output_positions = [positions[-1] for positions in position_working_bits]

            def apply_compute(
                input_positions: list[int], backward: bool = False
            ) -> None:
                indices = (
                    reversed(range(num_bits_states))
                    if backward
                    else range(num_bits_states)
                )
                for index in indices:
                    circuit = backward_qcs[index] if backward else forward_qcs[index]
                    qc.compose(
                        circuit,
                        [
                            *range(num_bits_states),
                            *input_positions,
                            *position_working_bits[index],
                        ],
                        inplace=True,
                    )
                if add_barrier_q:
                    qc.barrier()

            for _ in range(grover_iterations if stage_mode == "grover" else 0):
                apply_compute(input_positions)
                # Match the whole next-state encoding, including zero bits.
                # Distinct accepting encodings define disjoint marked subspaces.
                for accepting in sorted(efaq.final_states):
                    zero_positions = [
                        q for q, bit in zip(output_positions, accepting) if bit == "0"
                    ]
                    for position in zero_positions:
                        qc.x(position)
                    _phase_flip_all_ones(qc, output_positions)
                    for position in zero_positions:
                        qc.x(position)
                if add_barrier_q:
                    qc.barrier()
                apply_compute(input_positions, backward=True)
                # H X (multi-controlled Z) X H; global sign is immaterial.
                qc.h(input_positions)
                qc.x(input_positions)
                _phase_flip_all_ones(qc, input_positions)
                qc.x(input_positions)
                qc.h(input_positions)
                if add_barrier_q:
                    qc.barrier()

            for iteration in range(fnr_iterations if stage_mode == "fnr" else 0):
                flag = qc.num_qubits
                qc.add_register(QR(1, f"fnr_flag_{stage}_{iteration}"))
                apply_compute(input_positions)
                # Mark exactly the designated reject encoding, not every
                # nonaccepting state: intermediate states must remain usable.
                zero_positions = [
                    q for q, bit in zip(output_positions, reject_state) if bit == "0"
                ]
                for position in zero_positions:
                    qc.x(position)
                if len(output_positions) == 1:
                    qc.cx(output_positions[0], flag)
                else:
                    qc.mcx(output_positions, flag)
                for position in zero_positions:
                    qc.x(position)
                if add_barrier_q:
                    qc.barrier()
                apply_compute(input_positions, backward=True)
                # The flag must remain: changing its input prevents safe
                # uncomputation of the predicate that originally set it.
                _flip_and_rotate(qc, flag, input_positions)
                if add_barrier_q:
                    qc.barrier()

        # Copy only AFTER amplification, so no history bit blocks interference.
        # Apply forward circuits
        for i in range(num_bits_states):
            qc.compose(
                forward_qcs[i],
                [
                    *range(num_bits_states),
                    *range(curr_qc_size, curr_qc_size + new_symbol_todo_bits),
                    *position_working_bits[i],
                ],
                inplace=True,
            )
            if add_barrier_q:
                qc.barrier()

        # Add new output bit
        curr_num_bits = qc.num_qubits
        for i in range(num_bits_states):
            qc.add_register(QR(1))
            qc.cx(position_working_bits[i][-1], curr_num_bits + i)
            position_state_output_bits.append(curr_num_bits + i)
            if add_barrier_q:
                qc.barrier()

        # Apply backward circuits
        for i in range(num_bits_states):
            qc.compose(
                backward_qcs[num_bits_states - 1 - i],
                [
                    *range(num_bits_states),
                    *range(curr_qc_size, curr_qc_size + new_symbol_todo_bits),
                    *position_working_bits[num_bits_states - 1 - i],
                ],
                inplace=True,
            )
            if add_barrier_q:
                qc.barrier()

        # Apply swap gates
        for i in range(num_bits_states):
            qc.swap(position_state_output_bits[i], i)
            if add_barrier_q:
                qc.barrier()
        # --------------------------------------------------------------------

    # Measure state bits and symbol bits
    qc.add_register(CR(num_bits_states + bound * efaq.num_bits_symbols))
    for i in range(num_bits_states):
        qc.measure(i, i)
    i = num_bits_states
    for position_raw_symbols_bit in position_raw_symbols_bits:
        for position in position_raw_symbols_bit:
            qc.measure(position, i)
            i += 1

    # Apply Hadamard gates at the beginning
    hadamard = QC(new_symbol_todo_bits)
    for i in range(new_symbol_todo_bits):
        hadamard.h(i)
    for symbol_with_ndc in position_symbols_bits:
        qc.compose(hadamard, front=True, qubits=symbol_with_ndc, inplace=True)

    return qc


# TODO
# Observations:
# - Suppose we obtain n BDDs, i.e., BDD_1, \dots, BDD_n,
# then we should take the
# m := max(ancilla_bits(BDD_1), \dots, ancilla_bits(BDD_n))
# to allocate the m qubits for this
def bqrlg_series(efaq: EFAQ, bound: int) -> QC:
    raise NotImplementedError("Serial BDD workspace reuse is not implemented")
