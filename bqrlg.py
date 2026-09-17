from math import log2
from math import ceil

from dd.autoref import BDD
from dd.autoref import Function as Node

from qiskit import QuantumCircuit as QC
from qiskit import QuantumRegister as QR

from bdd_to_qc import bdd_to_qc

from encoding_automata import EFAQ

from utilities import DBG

# The input qubits are the first |u.support| qubits
# the rest are ancilla bits
def step(bdd : BDD, u : Node, use_blocks_q : bool) -> QC:
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

# TODO Extract n Boolean function from efag.transition
# Remember that n := \log_2(|K|), when we just care about
# simulating the transition of each output bit of \delta
# related to a value concerning the state (next state actually)
# In Example 3, the author extract a single Boolean function
# as only one bit was enough to keep track of the states
# during the simulation of the EFAQ
# Observations:
# - Suppose we obtain n BDDs, i.e., BDD_1, \cdots, BDD_n, 
# then we should take the 
# m := max(ancilla_bits(BDD_1), \dots, ancilla_bits(BDD_n))
# to allocate the m qubits for this

def delta_to_bdds(efaq : EFAQ) -> tuple[BDD, list[Node]]:
    n = efaq.num_bits_states
    num_vars = efaq.num_bits_states\
            + efaq.num_bits_symbols\
            + efaq.num_bits_ndcs

    bdd = BDD()
    variables = [f'x{i}' for i in range(num_vars)]
    bdd.declare(*variables)

    bdds = [bdd.false for _ in range(n)]

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

            bdds[i] |= cube

    return (bdd, bdds)

# TODO Keep working here
def bqrlg(efag : EFAQ, bound : int) -> QC:
    k0 = efag.initial_state
    return QC(1)
