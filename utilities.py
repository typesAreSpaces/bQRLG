from qiskit_aer import AerSimulator
from qiskit import transpile

from qiskit.visualization import plot_histogram
import matplotlib.pyplot as plt

from qiskit.qasm2 import dumps

def simulate(qc, show):
    simulator = AerSimulator()
    compiled = transpile(qc, simulator)
    result = simulator.run(compiled, shots=1024).result()

    counts = result.get_counts()
    print(counts)
    if show:
        plot_histogram(counts)
        plt.show()

def run(qc, showPlot, showQASM):
    print(qc)
    simulate(qc, showPlot)
    if showQASM:
        print(dumps(qc))
