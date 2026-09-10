from qiskit_aer import AerSimulator
from qiskit import transpile

from qiskit.visualization import plot_histogram
import matplotlib.pyplot as plt

from qiskit.qasm2 import dumps

from dd.autoref import BDD

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

def traverse(bdd, u):
    if u == bdd.false:
        print("FALSE")
        return

    if u == bdd.true:
        print("TRUE")
        return

    # print(f"Node: {u}, variable: {bdd.var(u)}")
    print(f"Node: {u}, variable: {u.var}")

    # traverse(bdd, bdd.low(u))
    # traverse(bdd, bdd.high(u))
    traverse(bdd, u.low)
    traverse(bdd, u.high)

def traverse2(bdd, u, visited=None):
    if visited is None:
        visited = set()

    if u in visited:
        return

    visited.add(u)

    if u == bdd.false:
        print("FALSE")
        return

    if u == bdd.true:
        print("TRUE")
        return

    # print(f"Node {u}: variable={bdd.var(u)}")
    print(f"Node {u}: variable={u.var}")

    # traverse2(bdd, bdd.low(u), visited)
    # traverse2(bdd, bdd.high(u), visited)
    traverse2(bdd, u.low, visited)
    traverse2(bdd, u.high, visited)

def print_bdd(bdd, u, visited=None):
    if visited is None:
        visited = set()

    if u in visited or u in (bdd.false, bdd.true):
        return

    visited.add(u)

    # print(f"{u} [{bdd.var(u)}]")
    print(f"{u} [{u.var}]")

    # print(f"  low  -> {bdd.low(u)}")
    # print(f"  high -> {bdd.high(u)}")
    print(f"  low  -> {u.low}")
    print(f"  high -> {u.high}")

    # print_bdd(bdd, bdd.low(u), visited)
    # print_bdd(bdd, bdd.high(u), visited)
    print_bdd(bdd, u.low, visited)
    print_bdd(bdd, u.high, visited)

def traverse3(bdd, u, visited=None, depth=0):
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

    print(indent + f"{var}")

    print(indent + "  low:")
    traverse3(bdd, low, visited, depth + 2)

    print(indent + "  high:")
    traverse3(bdd, high, visited, depth + 2)
