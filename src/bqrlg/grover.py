from qiskit import QuantumCircuit as QC

from math import sqrt
from math import floor
from math import pi

# ------------------
# Diffusion Operator
# ------------------
# This implements I - 2 |0><0|
# which has the same physical effect
# as the operator 2 |0><0| - I
# since the difference is a global phase
def Diffuser(n : int) -> QC:
    qc = QC(n)

    qc.h(range(n))
    qc.barrier() 
    
    qc.x(range(n))
    qc.barrier() 

    ## Multi controlled-Z
    qc.h(n-1)
    qc.mcx(list(range(n-1)), n-1)
    qc.h(n-1)
    qc.barrier() 

    qc.x(range(n))
    qc.barrier()

    qc.h(range(n))
    qc.barrier()

    return qc

# --------------
# Grover Circuit
# --------------
def Grover(oracle : QC) -> QC:
    n = oracle.num_qubits - 1
    qc = QC(n+1, n)
    num_iter = floor(pi*sqrt((2**n))/4)

    # Step 1: Uniform superposition
    qc.h(range(n))

    qc.x(n)
    qc.h(n)
    
    i = 0
    while i < num_iter:
        # Step 2: Oracle
        qc.compose(oracle, inplace=True)
        # Step 3: Diffuser
        qc.compose(Diffuser(n), qubits=range(n), inplace=True)
        i = i + 1

    # Step 4: Measure
    # qc.measure(range(n), range(n))

    return qc
