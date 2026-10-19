from itertools import product
from pathlib import Path

import matplotlib.pyplot as plt
from dd.autoref import BDD
from dd.autoref import Function as Node
from qiskit import QuantumCircuit as QC
from qiskit import transpile
from qiskit.qasm2 import dumps
from qiskit.visualization import plot_histogram
from qiskit_aer import AerSimulator

DEBUG = False


def DBG(*args):
    if DEBUG:
        print(*args)


def run(qc: QC, show_plot: bool) -> None:
    simulator = AerSimulator()
    compiled = transpile(qc, simulator)
    result = simulator.run(compiled, shots=1024).result()

    counts = result.get_counts()
    print(counts)
    if show_plot:
        plot_histogram(counts)
        plt.show()


def get_info(
    qc: QC, run_q: bool, show_circuit: bool, show_plot: bool, show_qasm: bool
) -> None:
    if show_circuit:
        figures_dir = Path(__file__).resolve().parents[2] / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)
        image_path = figures_dir / "circuit.png"
        figure = qc.draw(output="mpl", fold=35)
        try:
            figure.savefig(image_path, dpi=200, bbox_inches="tight")
        finally:
            plt.close(figure)
        print(f"Circuit saved to {image_path}")
    if run_q:
        run(qc, show_plot)
    if show_qasm:
        print(dumps(qc))


def input_circuit(bits: tuple) -> QC:
    qc = QC(len(bits))

    for i, bit in enumerate(bits):
        if bit == 1:
            qc.x(i)

    return qc


def traverse(bdd: BDD, u: Node, once_q: bool, visited=None, depth=0) -> None:
    if once_q:
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
    traverse(bdd, low, once_q, visited, depth + 2)
    print(indent + "  high:")
    traverse(bdd, high, once_q, visited, depth + 2)


def bdd_evaluate_all(bdd: BDD, node: Node) -> None:
    variables = list(bdd.vars)

    for values in product([False, True], repeat=len(variables)):
        assignment = dict(zip(variables, values))
        result = bdd.let(assignment, node)

        value = result == bdd.true

        print(f"{assignment} -> {value}")
