from qiskit import QuantumCircuit
from utilities import simulate, run

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
    run(qc, True, True)
    return 0

if __name__ == '__main__':
    main()
