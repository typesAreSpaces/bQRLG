from qiskit import QuantumCircuit as QC
from qiskit import QuantumRegister as QR
from qiskit import ClassicalRegister as CR

from dd.autoref import BDD
from dd.autoref import Function as Node

from itertools import product

from utilities import get_info
from utilities import traverse
from utilities import input_circuit
from utilities import bdd_evaluate_all

from bdd_to_qc import bdd_to_qc

from bqrlg import step_forward_backward
from bqrlg import delta_to_bdds
from bqrlg import bqrlg_parallel

from encoding_automata import NFA, DFA, EFAQ

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

    # f = (~x & y & z) | x
    # f = (~x & y & z) | (x & ((~y & z) | y))
    f = (~x & ~y & z) | (~x & y & ~z) | (x & ~y & ~z) | (x & y)
    # traverse(bdd, f, False)
    return (bdd, f)

def bdd_to_qc_example1() -> None:
    bdd, f = bdd_formula()

    for x in product([0, 1], repeat=3):
        print(f">> Input {x}")
        _input = input_circuit(x)
        _input.barrier()
        qc = bdd_to_qc(bdd, f, True)
        qc.add_register(CR(1))
        qc.measure(qc.num_qubits - 1, 0)
        qc.compose(_input, front=True, qubits=range(3), inplace=True)
        get_info(qc, True, True, False, False)

    return

def step_example1() -> None:
    bdd, f = bdd_formula()

    for x in product([0, 1], repeat=3):
        print(f">> Input {x}")
        _input = input_circuit(x)
        _input.barrier()
        qc = step_forward_backward(bdd, f, True)
        qc.add_register(CR(1))
        qc.measure(0, 0)
        qc.compose(_input, front=True, qubits=range(3), inplace=True)
        get_info(qc, True, False, False, False)

    return

def efaq1() -> EFAQ:
    symbols = {'p', 'q'}
    states = {'x', 'y'}
    delta = dict()
    delta[('x', 'p')] = {'x'}
    delta[('x', 'q')] = {'x', 'y'}
    delta[('y', 'p')] = {'y'}
    delta[('y', 'q')] = {'y'}
    initial_state = 'x'
    final_states = {'y'}

    nfa = NFA(symbols, states, delta, initial_state, final_states)
    dfa = DFA(nfa)
    efaq = EFAQ(dfa, 
                {'p': '0', 'q': '1'}, 
                {'x': '0', 'y': '1'},
                {('x', 'p0'): 'x', ('x', 'q0'): 'x', ('x', 'q1'): 'y',
                 ('y', 'p0'): 'y', ('y', 'q0'): 'y', ('x', 'p1'): 'x', 
                 ('y', 'p1'): 'y', ('y', 'q1'): 'y'})
    return efaq

def efaq2() -> EFAQ:
    symbols = {'p', 'q'}
    states = {'x', 'y'}
    delta = dict()
    delta[('x', 'p')] = {'x'}
    delta[('x', 'q')] = {'x', 'y'}
    delta[('y', 'p')] = {'y'}
    delta[('y', 'q')] = {'y'}
    initial_state = 'x'
    final_states = {'x'}

    nfa = NFA(symbols, states, delta, initial_state, final_states)
    dfa = DFA(nfa)
    efaq = EFAQ(dfa)

    return efaq

def testing_automata1() -> None:
    efaq1()._print()

    return

def testing_automata2() -> None:
    efaq2()._print()

    return

def testing_delta_to_bdds() -> None:
    efaq = efaq1()
    (a, b) = delta_to_bdds(efaq)
    # traverse(a, b[-1], True)
    bdd_evaluate_all(a, b[0])

    return

def testing_bqrlg_parrallel() -> None:
    efaq = efaq1()
    qc = bqrlg_parallel(efaq, 2, True)
    get_info(qc, True, True, True, False)

    return

def boolean_formula1(x : bool, y : bool, z : bool) -> bool:
    return x or ((not x) and y and z)

def experiment_homomophism() -> None:
    for x in [False, True]:
        for y in [False, True]:
            for z in [False, True]:
                f = boolean_formula1(x, y, z)
                print(f">> {x},{y},{z} | {f}")
    print("")
    for x in [False, True]:
        for y in [False, True]:
            for z in [False, True]:
                f = not(boolean_formula1(not(x), not(y), not(z)))
                print(f">> {x},{y},{z} | {f}")
    print("")
    for x in [False, True]:
        for y in [False, True]:
            for z in [False, True]:
                f = not(boolean_formula1(not(x), y, not(z)))
                print(f">> {x},{y},{z} | {f}")
