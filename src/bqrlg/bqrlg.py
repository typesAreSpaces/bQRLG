from math import log2
from math import ceil

from dd.autoref import BDD
from dd.autoref import Function as Node

from qiskit import QuantumCircuit as QC
from qiskit import QuantumRegister as QR
from qiskit import ClassicalRegister as CR

from .bdd_to_qc import bdd_to_qc

from .encoding_automata import EFAQ

from .utilities import DBG

# The input qubits are the first |u.support| qubits
# the rest are ancilla bits
# except the last one which holds the next_state, then
# swaps it with the first one to hold the previous_state
def step_forward_backward(bdd : BDD, u : Node, use_blocks_q : bool) -> QC:
    step_forward =  bdd_to_qc(bdd, u, False)
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

def delta_to_bdds(efaq : EFAQ) -> tuple[BDD, list[Node]]:
    n = efaq.num_bits_states
    num_vars = efaq.num_bits_states\
            + efaq.num_bits_symbols\
            + efaq.num_bits_ndcs

    bdd = BDD()
    variables = [f'x{i}' for i in range(num_vars)]
    bdd.declare(*variables)

    formulas = [bdd.false for _ in range(n)]

    # Iterate over each row of efaq.delta
    # i.e., efaq.delta(_input) = _output
    for _input, _output in efaq.delta.items():
        _output = _output[:n]

        # Update the i^{th} bdd
        for i, bit_k in enumerate(_output):
            if bit_k == '0':
                continue

            cube = bdd.true

            for var, bit in zip(variables, _input):
                if bit == '1':
                    cube &= bdd.var(var)
                else:
                    cube &= ~bdd.var(var)

            formulas[i] |= cube

    return (bdd, formulas)

# Observations:
# - Fig. 11 from the original paper suggest the working bits
# for each BDD are placed in parallel
def bqrlg_parallel(efaq : EFAQ, bound : int,
                   add_barrier_q : bool = False,
                   enable_grover : bool = False) -> QC:
    (bdd, formulas) = delta_to_bdds(efaq)

    forward_qcs = [bdd_to_qc(bdd, formula, False) for formula in formulas]
    backward_qcs = [qc.reverse_ops() for qc in forward_qcs]

    num_bits_states = efaq.num_bits_states
    # assert num_bits_states == len(forward_qcs)
    num_bits_input = efaq.num_bits_states \
            + efaq.num_bits_symbols \
            + efaq.num_bits_ndcs
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
        if initial_bit == '1':
            qc.x(i)

    # Simulate \delta over
    # a string of size `bound'
    new_symbol_todo_bits = efaq.num_bits_symbols + efaq.num_bits_ndcs
    position_raw_symbols_bits = []
    position_symbols_bits = []
    for stage in range(bound):
        curr_qc_size = qc.num_qubits
        qc.add_register(QR(new_symbol_todo_bits))

        # --------------------------------------------------------------------
        # Process each state output bit

        position_raw_symbols_bits.append(
                range(curr_qc_size, curr_qc_size + efaq.num_bits_symbols))
        position_symbols_bits.append(
                range(curr_qc_size, curr_qc_size + new_symbol_todo_bits))

        # Apply forward circuits
        for i in range(num_bits_states):
            qc.compose(forward_qcs[i],
                   [*range(num_bits_states),
                    *range(curr_qc_size, curr_qc_size + new_symbol_todo_bits),
                    *position_working_bits[i]],
                   inplace=True)
            if add_barrier_q:
                qc.barrier()

        # Add new output bit
        for i in range(num_bits_states):
            qc.add_register(QR(1))
            qc.cx(position_working_bits[i][-1], qc.num_qubits - 1)
            if add_barrier_q:
                qc.barrier()

        # Apply backward circuits
        for i in range(num_bits_states):
            qc.compose(backward_qcs[num_bits_states - 1 - i],
                   [*range(num_bits_states),
                    *range(curr_qc_size, curr_qc_size + new_symbol_todo_bits),
                    *position_working_bits[num_bits_states - 1 - i]],
                   inplace=True)
            if add_barrier_q:
                qc.barrier()

        # Apply swap gates
        for i in range(num_bits_states):
            qc.swap(qc.num_qubits - 1, i)
            if add_barrier_q:
                qc.barrier()
        # --------------------------------------------------------------------

    # Measure state bits and symbol bits
    qc.add_register(CR(num_bits_states + bound*efaq.num_bits_symbols))
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
def bqrlg_series(efaq : EFAQ, bound : int) -> QC:
    # TODO
    (bdd, formulas) = delta_to_bdds(efaq)

    forward_qcs = [bdd_to_qc(bdd, formula, True) for formula in formulas]
    backward_qcs = [qc.reverse_ops() for qc in forward_qcs]

    num_qubits = max([qc.num_qubits for qc in forward_qcs])

    qc = QC(num_qubits)

    # Prepare input for k0
    k0 = efaq.initial_state
    for i, initial_bit in enumerate(k0):
        print(">> initial_bits", initial_bit)
        if initial_bit == '1':
            qc.x(i)

    # Simulate \delta over
    # a string of size `bound'
    for stage in range(bound):
        print(">> stage", stage)

    # Measure state bits and symbol bits
    qc.add_register(CR(efaq.num_bits_states + bound*efaq.num_bits_symbols))

    return qc
