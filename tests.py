from qiskit import QuantumCircuit
from utilities import get_info

from dd.autoref import BDD
from bdd_to_qc import bdd_to_qc

def simple_qc() -> None:
    # QuantumCircuit(num_qubits, num_classical_bits)
    # 2 qubits
    # 2 classical bits to store measurements
    qc = QuantumCircuit(2, 2)
    qc.measure(range(2), range(2))
    get_info(qc, False, False, False)

def bdd_2_qc_example1():

    bdd = BDD()
    bdd.declare('x', 'y', 'z')

    x = bdd.var('x')
    y = bdd.var('y')
    z = bdd.var('z')

    f = ((~ x) & y & z) | (x & (((~ y) & z) | y))
    qc = bdd_to_qc(bdd, f)
    get_info(qc, False, False, False)
