from utilities import simulate, run
from utilities import traverse, traverse2, print_bdd
from utilities import traverse3

from qiskit import QuantumCircuit
from dd.autoref import BDD

from encoding import NFA, DFA, EFAQ
from bdd_to_qc import bdd_to_qc


def TwoSimpleWires():
    # QuantumCircuit(num_qubits, num_classical_bits)
    # 2 qubits
    # 2 classical bits to store measurements
    qc = QuantumCircuit(2, 2)
    qc.measure(range(2), range(2))
    return qc

# Main

def main():
    qc = TwoSimpleWires()
    run(qc, False, False)
    a = EFAQ(DFA(NFA([0, 1], [0, 1], "todo", 0, [1])))
    return 0

# if __name__ == '__main__':
    # main()

# Test

bdd = BDD()
bdd.declare('x', 'y', 'z')

x = bdd.var('x')
y = bdd.var('y')
z = bdd.var('z')

f = ((~ x) & y & z) | (x & (((~ y) & z) | y))
u = bdd.add_expr('(x & y) | z')

# traverse(bdd, u)
traverse(bdd, f)
# traverse2(bdd, f)
# print_bdd(bdd, f)
# traverse3(bdd, f)
