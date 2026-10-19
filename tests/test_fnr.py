import itertools
import unittest
from collections import Counter

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from test_grover import automaton, paper_example, probabilities

from bqrlg.bdd_to_qc import bdd_to_qc
from bqrlg.bqrlg import _flip_and_rotate, bqrlg_parallel, delta_to_bdds


def classical_fnr(e, bound, iterations, reject):
    width = e.num_bits_symbols + e.num_bits_ndcs
    inputs = ["".join(bits) for bits in itertools.product("01", repeat=width)]
    counts = Counter()
    for word in itertools.product(inputs, repeat=bound):
        state = e.initial_state
        for symbol in word:
            for _ in range(iterations):
                if e.delta[state + symbol][: e.num_bits_states] == reject:
                    symbol = symbol[1:] + str(1 - int(symbol[0]))
            state = e.delta[state + symbol][: e.num_bits_states]
        counts[state] += 1 / len(inputs) ** bound
    return counts


class FnRTests(unittest.TestCase):
    def test_controlled_flip_rotate_truth_table(self):
        for width in (1, 2, 3):
            for flag in (0, 1):
                for bits in itertools.product((0, 1), repeat=width):
                    qc = QuantumCircuit(width + 1)
                    for q, bit in enumerate((*bits, flag)):
                        if bit:
                            qc.x(q)
                    _flip_and_rotate(qc, width, list(range(width)))
                    expected = list(bits[1:]) + [1 - bits[0]] if flag else list(bits)
                    index = sum(bit << q for (q, bit) in enumerate((*expected, flag)))
                    self.assertAlmostEqual(
                        Statevector.from_instruction(qc).probabilities()[index], 1
                    )

    def test_single_reject_bit_and_flag_is_retained(self):
        e = automaton(1, 1, 1, lambda k, s, c: s, {"1"})
        self.assertAlmostEqual(
            probabilities(e, 1, amplification_schedule=["fnr"] * 1)["1"], 3 / 4
        )
        self.assertAlmostEqual(
            probabilities(e, 1, fnr_iterations=2, amplification_schedule=["fnr"] * 1)[
                "1"
            ],
            1,
        )
        qc = bqrlg_parallel(e, 2, fnr_iterations=3, amplification_schedule=["fnr"] * 2)
        flags = [r for r in qc.qregs if r.name.startswith("fnr_flag_")]
        self.assertEqual(len(flags), 6)

    def test_multibit_rejection_and_classical_reference(self):
        for reject in ("00", "10"):
            e = automaton(2, 1, 1, lambda k, s, c: s + c, {"11"}, initial="01")
            for iterations in (0, 1, 2, 3):
                actual = probabilities(
                    e,
                    2,
                    fnr_iterations=iterations,
                    reject_state=reject,
                    amplification_schedule=["fnr"] * 2,
                )
                expected = classical_fnr(e, 2, iterations, reject)
                for k in set(actual) | set(expected):
                    self.assertAlmostEqual(actual.get(k, 0), expected.get(k, 0))

    def test_nonaccepting_intermediate_states_are_not_rejected(self):
        e = automaton(2, 1, 1, lambda k, s, c: "01", {"11"}, initial="10")
        qc = bqrlg_parallel(
            e, 1, amplification_schedule=["fnr"] * 1
        ).remove_final_measurements(inplace=False)
        state = Statevector.from_instruction(qc)
        flag = next(q for r in qc.qregs if r.name.startswith("fnr_flag_") for q in r)
        self.assertAlmostEqual(
            state.probabilities(qargs=[qc.find_bit(flag).index])[0], 1
        )

    def test_scratch_is_clean_and_barriers_preserve_distribution(self):
        e = paper_example()
        (bdd, formulas) = delta_to_bdds(e)
        width = sum(bdd_to_qc(bdd, f, False).num_qubits - 3 for f in formulas)
        qc = bqrlg_parallel(
            e,
            2,
            fnr_iterations=2,
            add_barrier_q=True,
            amplification_schedule=["fnr"] * 2,
        ).remove_final_measurements(inplace=False)
        state = Statevector.from_instruction(qc)
        self.assertAlmostEqual(
            state.probabilities(qargs=list(range(1, 1 + width)))[0], 1
        )
        expected = classical_fnr(e, 2, 2, "0")
        actual = probabilities(
            e,
            2,
            fnr_iterations=2,
            add_barrier_q=True,
            amplification_schedule=["fnr"] * 2,
        )
        for k in set(expected) | set(actual):
            self.assertAlmostEqual(actual.get(k, 0), expected.get(k, 0))

    def test_zero_bound_and_invalid_parameters(self):
        e = paper_example()
        self.assertAlmostEqual(
            probabilities(e, 0, amplification_schedule=["fnr"] * 0)["0"], 1
        )
        for options in (
            {"fnr_iterations": -1},
            {"amplification_schedule": ["fnr"], "reject_state": "10"},
            {"amplification_schedule": ["fnr"], "reject_state": "x"},
        ):
            with self.assertRaises(ValueError):
                bqrlg_parallel(e, 1, **options)


if __name__ == "__main__":
    unittest.main()
