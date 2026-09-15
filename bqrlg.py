from math import log2
from math import ceil

from dd.autoref import BDD
from dd.autoref import Function as Node

from qiskit import QuantumCircuit as QC
from qiskit import QuantumRegister as QR

from bdd_to_qc import bdd_to_qc

from encoding_automata import EFAQ

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
# m := max(ancilla_bits(BDD_1), \cdots, ancilla_bits(BDD_n))
# to allocate the m qubits for this

# TODO Modify this function 
# to handle the image of \Delta
def truth_table_to_bdd(values: list[bool]):
    n = ceil(log2(len(values))) 

    bdd = BDD()
    variables = [f'x{i}' for i in range(n)]
    bdd.declare(*variables)

    u = bdd.false

    for i, value in enumerate(values):
        if not value:
            continue

        bits = format(i, f'0{n}b')

        cube = bdd.true

        for var, bit in zip(variables, bits):
            if bit == '1':
                cube &= bdd.var(var)
            else:
                cube &= ~bdd.var(var)

        u |= cube

    return bdd, u

# TODO Keep working here
def bqrlg(efag : EFAQ, bound : int) -> QC:
    k0 = efag.initial_state
    return QC(1)
