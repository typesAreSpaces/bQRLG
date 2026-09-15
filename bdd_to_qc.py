from dd.autoref import BDD
from dd.autoref import Function as Node

from qiskit import QuantumCircuit as QC
from qiskit import QuantumRegister as QR

from collections import deque

from utilities import DBG

def case_low_1_high_0(is_node_complemented : bool) -> QC:
    qc = QC(2)
    # qc.x(0)
    qc.cx(1, 0)
    if not(is_node_complemented):
        qc.x(0)
    return qc

def case_low_1_high_x(is_node_complemented : bool) -> QC:
    qc = QC(3)
    # qc.x(0)
    qc.cx(1, 0)
    qc.ccx(2, 1, 0)
    if not(is_node_complemented):
        qc.x(0)
    return qc

def case_low_0_high_1(is_node_complemented : bool) -> QC:
    qc = QC(2)
    qc.cx(1, 0)
    if is_node_complemented:
        qc.x(0)
    return qc

def case_low_0_high_x(is_node_complemented : bool) -> QC:
    qc = QC(3)
    qc.ccx(2, 1, 0)
    if is_node_complemented:
        qc.x(0)
    return qc

def case_low_x_high_1(is_node_complemented : bool) -> QC:
    qc = QC(3)
    qc.ccx(2, 1, 0)
    qc.cx(2, 0)
    qc.cx(1, 0)
    if is_node_complemented:
        qc.x(0)
    return qc

def case_low_x_high_0(is_node_complemented : bool) -> QC:
    qc = QC(3)
    qc.ccx(2, 1, 0)
    qc.cx(2, 0)
    if is_node_complemented:
        qc.x(0)
    return qc

def case_low_x_high_x(is_node_complemented : bool) -> QC:
    qc = QC(4)
    qc.ccx(2, 1, 0)
    qc.cx(2, 0)
    qc.ccx(3, 1, 0)
    if is_node_complemented:
        qc.x(0)
    return qc

# The input qubits are the first |u.support| qubits
# the rest are ancilla bits
def bdd_to_qc(bdd : BDD, u : Node, addBarrierQ : bool) -> QC:
    T = bdd.true
    F = bdd.false

    num_variables = len(u.support)
    DBG(">> num_variables", num_variables)
    qc = QC(num_variables)
    c_output = dict()
    fresh_var = num_variables

    queue = deque()
    todo = []
    visited = set()

    queue.append(u)
    while queue:
        u = queue.popleft()

        if u in visited \
                or u == T \
                or u == F:
            continue

        todo.append(u)
        visited.add(u)
        # var is an integer/level index
        var, low, high = bdd.succ(u)
        queue.append(low)
        queue.append(high)

    while todo:
        u = todo.pop()
        if u == T or u == F:
            continue

        var, low, high = bdd.succ(u)
        c_output[u] = fresh_var
        qc.add_register(QR(1))
        fresh_var += 1
        is_node_complemented = u.node < 0

        if low == T:
            if high == T:
                DBG("Not possible low-1, high-1")
            elif high == F:
                DBG("Case low-1, high-0")
                qc.compose(case_low_1_high_0(is_node_complemented),
                           [c_output[u], var],
                           inplace=True)
            else:
                DBG("Case low-1, high-?")
                qc.compose(case_low_1_high_x(is_node_complemented),
                           [c_output[u], var, c_output[high]],
                           inplace=True)
        elif low == F:
            if high == T:
                DBG("Case low-0, high-1")
                qc.compose(case_low_0_high_1(is_node_complemented),
                           [c_output[u], var],
                           inplace=True)
            elif high == F:
                DBG("Not possible low-0, high-0")
            else:
                DBG("Case low-0, high-?")
                qc.compose(case_low_0_high_x(is_node_complemented),
                           [c_output[u], var, c_output[high]],
                           inplace=True)
        else:
            if high == T:
                DBG("Case low-?, high-1")
                qc.compose(case_low_x_high_1(is_node_complemented),
                           [c_output[u], var, c_output[low]],
                           inplace=True)
            elif high == F:
                DBG("Case low-?, high-0")
                qc.compose(case_low_x_high_0(is_node_complemented),
                           [c_output[u], var, c_output[low]],
                           inplace=True)
            else:
                DBG("Case low-?, high-?")
                qc.compose(case_low_x_high_x(is_node_complemented),
                           [c_output[u], var, c_output[low], c_output[high]],
                           inplace=True)

        if addBarrierQ:
            qc.barrier()

    return qc
