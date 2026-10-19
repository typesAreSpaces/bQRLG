import itertools
import random
import unittest

from dd.autoref import BDD
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from bqrlg.bdd_to_qc import bdd_to_qc


class BDDSynthesisTests(unittest.TestCase):
    def assert_truth_table(self, bdd, root, names):
        compiled = bdd_to_qc(bdd, root, False)
        for values in itertools.product((False, True), repeat=len(names)):
            qc = QuantumCircuit(compiled.num_qubits)
            for index, value in enumerate(values):
                if value:
                    qc.x(index)
            qc.compose(compiled, inplace=True)
            expected = int(bdd.let(dict(zip(names, values)), root) == bdd.true)
            state = Statevector.from_instruction(qc)
            self.assertAlmostEqual(
                state.probabilities(qargs=[compiled.num_qubits - 1])[expected], 1
            )
            qc.compose(compiled.inverse(), inplace=True)
            uncomputed = Statevector.from_instruction(qc)
            original = sum(int(value) << index for index, value in enumerate(values))
            self.assertAlmostEqual(uncomputed.probabilities()[original], 1)

    def test_shared_nodes_at_different_depths(self):
        bdd = BDD()
        names = ["x0", "x1", "x2", "x3"]
        bdd.declare(*names)
        root = bdd.ite(
            bdd.var("x0"),
            bdd.ite(bdd.var("x1"), bdd.var("x2"), bdd.var("x3")),
            bdd.var("x2"),
        )
        self.assert_truth_table(bdd, root, names)
        self.assert_truth_table(bdd, ~root, names)

    def test_every_three_variable_boolean_function(self):
        bdd = BDD()
        names = ["x0", "x1", "x2"]
        bdd.declare(*names)
        for mask in range(256):
            root = bdd.false
            for index, values in enumerate(itertools.product((False, True), repeat=3)):
                if mask & (1 << index):
                    root |= bdd.cube(dict(zip(names, values)))
            self.assert_truth_table(bdd, root, names)

    def test_variable_reordering_preserves_input_identity(self):
        bdd = BDD()
        names = ["x0", "x1", "x2"]
        bdd.declare(*names)
        root = bdd.add_expr("x0 & ~x2")
        bdd.reorder({"x2": 0, "x1": 1, "x0": 2})
        self.assert_truth_table(bdd, root, names)

    def test_random_four_variable_functions(self):
        rng = random.Random(2023)
        bdd = BDD()
        names = ["x0", "x1", "x2", "x3"]
        bdd.declare(*names)
        for _ in range(16):
            root = bdd.false
            for values in itertools.product((False, True), repeat=4):
                if rng.getrandbits(1):
                    root |= bdd.cube(dict(zip(names, values)))
            self.assert_truth_table(bdd, root, names)


if __name__ == "__main__":
    unittest.main()
