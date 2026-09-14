from dd.autoref import BDD
from dd.autoref import Function as Node

from qiskit import QuantumCircuit as QC
from qiskit import QuantumRegister as QR

from collections import deque

from utilities import DBG

# The input qubits are the first |u.support| qubits
# the rest are ancilla bits
def bdd_to_qc(bdd : BDD, u : Node, addBarrierQ : bool) -> QC:
    T = bdd.true
    F = bdd.false

    num_variables = len(u.support)
    DBG(">> num_variables", num_variables)

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

    qc = QC(num_variables)
    c_output = dict()
    fresh_var = num_variables

    while todo:
        u = todo.pop()
        if u == T or u == F:
            continue

        var, low, high = bdd.succ(u)
        c_output[u] = fresh_var
        qc.add_register(QR(1))
        fresh_var += 1

        if low == T:
            if high == T:
                DBG("Not possible low-1, high-1")
            elif high == F:
                DBG("Case low-1, high-0")
                _qc = QC(2)
                # _qc.x(0)
                _qc.cx(1, 0)
                if u.node > 0:
                    _qc.x(0)
                qc.compose(_qc, [c_output[u], var], inplace=True)
            else:
                DBG("Case low-1, high-?")
                _qc = QC(3)
                # _qc.x(0)
                _qc.cx(1, 0)
                _qc.ccx(2, 1, 0)
                if u.node > 0:
                    _qc.x(0)
                qc.compose(_qc, [c_output[u], var, c_output[high]], inplace=True)
        elif low == F:
            if high == T:
                DBG("Case low-0, high-1")
                _qc = QC(2)
                _qc.cx(1, 0)
                if u.node < 0:
                    _qc.x(0)
                qc.compose(_qc, [c_output[u], var], inplace=True)
            elif high == F:
                DBG("Not possible low-0, high-0")
            else:
                DBG("Case low-0, high-?")
                _qc = QC(3)
                _qc.ccx(2, 1, 0)
                if u.node < 0:
                    _qc.x(0)
                qc.compose(_qc, [c_output[u], var, c_output[high]], inplace=True)
        else:
            if high == T:
                DBG("Case low-?, high-1")
                _qc = QC(3)
                _qc.ccx(2, 1, 0)
                _qc.cx(2, 0)
                _qc.cx(1, 0)
                if u.node < 0:
                    _qc.x(0)
                qc.compose(_qc, [c_output[u], var, c_output[low]], inplace=True)
            elif high == F:
                DBG("Case low-?, high-0")
                _qc = QC(3)
                _qc.ccx(2, 1, 0)
                _qc.cx(2, 0)
                if u.node < 0:
                    _qc.x(0)
                qc.compose(_qc, [c_output[u], var, c_output[low]], inplace=True)
            else:
                DBG("Case low-?, high-?")
                _qc = QC(4)
                _qc.ccx(2, 1, 0)
                _qc.cx(2, 0)
                _qc.ccx(3, 1, 0)
                if u.node < 0:
                    _qc.x(0)
                qc.compose(_qc, [c_output[u], var, c_output[low], c_output[high]], inplace=True)

        if addBarrierQ:
            qc.barrier()

    return qc

# The input qubits are the first |u.support| qubits
# the rest are ancilla bits
def step(bdd : BDD, u : Node, useBlocks : bool) -> QC:
    step_forward =  bdd_to_qc(bdd, u, False)
    step_backward = step_forward.reverse_ops()
    num_qubits = step_forward.num_qubits
    qc = QC(num_qubits)

    if useBlocks:
        step_forward = step_forward.to_gate()
        step_backward = step_backward.to_gate()
        step_forward.name = "Step forward"
        step_backward.name = "Step backward"

    qc.add_register(QR(1))
    qc.compose(step_forward, range(num_qubits), inplace=True)
    qc.cx(num_qubits - 1, num_qubits)
    qc.compose(step_backward, range(num_qubits), inplace=True)
    qc.swap(0, num_qubits)

    return qc
