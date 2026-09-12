from qiskit import QuantumCircuit

from qiskit_aer import AerSimulator
from qiskit import transpile

from qiskit.visualization import plot_histogram
import matplotlib.pyplot as plt

from qiskit.qasm2 import dumps

from dd.autoref import BDD
from dd.autoref import Function as Node

DEBUG = False

def DBG(*args):
    if DEBUG:
        print(*args)

def run(qc : QuantumCircuit, showPlot : bool) -> None:
    simulator = AerSimulator()
    compiled = transpile(qc, simulator)
    result = simulator.run(compiled, shots=1024).result()

    counts = result.get_counts()
    print(counts)
    if showPlot:
        plot_histogram(counts)
        plt.show()
    return

def get_info(qc : QuantumCircuit, runQ : bool, 
        showPlot : bool, showQASM : bool) -> None:
    print(qc)
    if runQ:
        run(qc, showPlot)
    if showQASM:
        print(dumps(qc))
    return

def input_circuit(bits : list):
    qc = QuantumCircuit(len(bits))

    for i, bit in enumerate(bits):
        if bit == 1:
            qc.x(i)

    return qc

def traverse(bdd : BDD, u : Node, onceQ, visited=None, depth=0) -> None:
    if onceQ:
        if visited is None:
            visited = set()

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
    traverse(bdd, low, onceQ, visited, depth + 2)
    print(indent + "  high:")
    traverse(bdd, high, onceQ, visited, depth + 2)
