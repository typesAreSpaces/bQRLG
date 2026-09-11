from dd.autoref import BDD
from dd.autoref import Function
from qiskit import QuantumCircuit

from utilities import DBG

# TODO: Use inplace-traversal instead of recursive
def bdd_to_qc(bdd : BDD, u : Function) -> QuantumCircuit:

    # First pass to get number of internal nodes

    num_nodes = 0
    todo = []
    visited = set()
    todo.append(u)

    while todo:
        u = todo.pop()

        if u == bdd.true or u == bdd.false:
            continue

        if u in visited:
            continue
        visited.add(u)
        num_nodes += 1

        var, low, high = bdd.succ(u)

        todo.append(low)
        todo.append(high)

    DBG(">> number of internal nodes", num_nodes)
    # Second pass to construct quantum circuit

    qc = QuantumCircuit(num_nodes)
    return qc
