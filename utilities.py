from qiskit import QuantumCircuit

from qiskit_aer import AerSimulator
from qiskit import transpile

from qiskit.visualization import plot_histogram
import matplotlib.pyplot as plt

from qiskit.qasm2 import dumps

from dd.autoref import BDD
from dd.autoref import Function

DEBUG = True

def DBG(*args):
    if DEBUG:
        print(*args)

def simulate(qc : QuantumCircuit, show : bool) -> None:
    simulator = AerSimulator()
    compiled = transpile(qc, simulator)
    result = simulator.run(compiled, shots=1024).result()

    counts = result.get_counts()
    print(counts)
    if show:
        plot_histogram(counts)
        plt.show()
    return

def run(qc : QuantumCircuit, runQ : bool, 
        showPlot : bool, showQASM : bool) -> None:
    print(qc)
    if runQ:
        simulate(qc, showPlot)
    if showQASM:
        print(dumps(qc))
    return

def traverse(bdd : BDD, u : Function, visited=None, depth=0) -> None:
    if visited is None:
        visited = set()

    # Function objects are hashable
    if u in visited:
        return

    visited.add(u)

    indent = "  " * depth

    # Terminal nodes
    if u == bdd.false:
        print(indent + "FALSE")
        return

    if u == bdd.true:
        print(indent + "TRUE")
        return

    # Get variable and children
    var, low, high = bdd.succ(u)

    print(indent + f"Node: {u}, variable: {var}")
    print(indent + "  low:")
    traverse(bdd, low, visited, depth + 2)
    print(indent + "  high:")
    traverse(bdd, high, visited, depth + 2)
