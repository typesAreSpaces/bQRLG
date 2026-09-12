from qiskit import QuantumCircuit as QC
from qiskit import ClassicalRegister as CR
from qiskit import QuantumRegister as QR

from dd.autoref import BDD

from itertools import product

from utilities import get_info
from utilities import traverse
from utilities import input_circuit

from bdd_to_qc import bdd_to_qc

def simple_qc() -> None:
    qc1 = QC(2)
    qc1.cx(0, 1)

    qc = QC()
    qc.add_register(QR(2))
    qc.compose(qc1, qubits=[0,1], inplace=True)
    qc.add_register(QR(1))
    qc.compose(qc1, qubits=[1,2], inplace=True)
    qc.add_register(QR(1))
    qc.add_register(QR(1))
    qc.compose(qc1, qubits=[0,3], inplace=True)
    get_info(qc, False, False, False)

    return

def bdd_2_qc_example1() -> None:
    bdd = BDD()
    bdd.declare('x', 'y', 'z')

    x = bdd.var('x')
    y = bdd.var('y')
    z = bdd.var('z')

    f = (~x & y & z) | (x & ((~y & z) | y))
    # f = (~x & ~y & z) | (~x & y & ~z) | (x & ~y & ~z) | (x & y)
    # traverse(bdd, f, False)

    for x in product([0, 1], repeat=3):
        print(f">> Input {x}")
        input = input_circuit(x)
        input.barrier()
        qc = bdd_to_qc(bdd, f)

        # This is going to be useful
        # for the backward step
        # qc1 = qc.reverse_ops()

        qc.add_register(CR(1))
        qc.measure(qc.num_qubits - 1, 0)
        qc.compose(input, front=True, qubits=range(3), inplace=True)
        get_info(qc, True, False, False)

        # qc1.add_register(CR(1))
        # qc1.measure(qc1.num_qubits - 1, 0)
        # qc1.compose(input, front=True, qubits=range(3), inplace=True)
        # get_info(qc1, True, False, False)

    return
