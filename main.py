from qiskit import QuantumCircuit
from utilities import simulate, run

from encoding import NFA, DFA, EFAQ

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

if __name__ == '__main__':
    main()
