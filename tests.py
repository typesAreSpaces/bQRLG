from qiskit import QuantumCircuit as QC
from qiskit import ClassicalRegister as CR
from qiskit import QuantumRegister as QR

from dd.autoref import BDD
from dd.autoref import Function as Node

from itertools import product

from utilities import get_info
from utilities import traverse
from utilities import input_circuit

from bdd_to_qc import bdd_to_qc
from bdd_to_qc import step

from encoding import NFA, DFA, EFAQ

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
    get_info(qc, True, False, False, False)

    return

def bdd_formula() -> tuple[BDD, Node]:
    bdd = BDD()
    bdd.declare('x', 'y', 'z')

    x = bdd.var('x')
    y = bdd.var('y')
    z = bdd.var('z')

    f = (~x & y & z) | x
    # f = (~x & y & z) | (x & ((~y & z) | y))
    # f = (~x & ~y & z) | (~x & y & ~z) | (x & ~y & ~z) | (x & y)
    # traverse(bdd, f, False)
    return (bdd, f)

def bdd_2_qc_example1() -> None:
    bdd, f = bdd_formula()

    for x in product([0, 1], repeat=3):
        print(f">> Input {x}")
        input = input_circuit(x)
        input.barrier()
        qc = bdd_to_qc(bdd, f, True)
        qc.add_register(CR(1))
        qc.measure(qc.num_qubits - 1, 0)
        qc.compose(input, front=True, qubits=range(3), inplace=True)
        get_info(qc, True, True, False, False)

    return

def step_example1() -> None:
    bdd, f = bdd_formula()

    for x in product([0, 1], repeat=3):
        print(f">> Input {x}")
        input = input_circuit(x)
        input.barrier()
        qc = step(bdd, f, True)
        qc.add_register(CR(1))
        qc.measure(0, 0)
        qc.compose(input, front=True, qubits=range(3), inplace=True)
        get_info(qc, True, True, False, False)

    return

def testing_automata():
    delta = dict()
    delta[('x', 'p')] = {'x'}
    delta[('x', 'q')] = {'x', 'y'}
    delta[('y', 'p')] = {'y'}
    delta[('y', 'q')] = {'y'}
    nfa1 = NFA({'p', 'q'}, {'x', 'y'}, delta, 'x', {'y'})
    nfa1._print()
    dfa1 = DFA(nfa1)
    dfa1._print()
    # efaq1 = EFAQ(dfa1)
