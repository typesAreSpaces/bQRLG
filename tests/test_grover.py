import itertools
import unittest
from types import SimpleNamespace

from qiskit.quantum_info import Statevector

from bqrlg.bdd_to_qc import bdd_to_qc
from bqrlg.bqrlg import bqrlg_parallel, delta_to_bdds


def automaton(n, s, c, transition, accepting, initial=None):
    delta = {}
    for bits in itertools.product("01", repeat=n + s + c):
        x = "".join(bits)
        delta[x] = transition(x[:n], x[n : n + s], x[n + s :]) + x[n:]
    return SimpleNamespace(
        num_bits_states=n,
        num_bits_symbols=s,
        num_bits_ndcs=c,
        initial_state=initial or "0" * n,
        final_states=set(accepting),
        delta=delta,
    )


def paper_example():
    return automaton(
        1, 1, 1, lambda k, s, c: str(int(k == "1" or s + c == "11")), {"1"}
    )


def probabilities(e, bound, **options):
    qc = bqrlg_parallel(e, bound, **options).remove_final_measurements(inplace=False)
    state = Statevector.from_instruction(qc)
    return state.probabilities_dict(qargs=list(reversed(range(e.num_bits_states))))


class GroverTests(unittest.TestCase):
    def test_figure10_and_baseline(self):
        e = paper_example()
        self.assertAlmostEqual(probabilities(e, 2)["1"], 7 / 16)
        self.assertAlmostEqual(
            probabilities(e, 2, amplification_schedule=["grover"] * 2)["1"], 1
        )

    def test_multibit_zero_acceptance_and_unused_inputs(self):
        e = automaton(2, 1, 1, lambda k, s, c: s + c, {"00"}, initial="11")
        self.assertAlmostEqual(probabilities(e, 1)["00"], 1 / 4)
        self.assertAlmostEqual(
            probabilities(e, 1, amplification_schedule=["grover"] * 1)["00"], 1
        )

    def test_constant_output(self):
        e = automaton(2, 1, 1, lambda k, s, c: "01", {"01"})
        self.assertAlmostEqual(
            probabilities(e, 2, amplification_schedule=["grover"] * 2)["01"], 1
        )

    def test_multiple_accepting_states(self):
        e = automaton(2, 1, 1, lambda k, s, c: s + c, {"00", "11"})
        p = probabilities(e, 1, amplification_schedule=["grover"] * 1)
        self.assertAlmostEqual(p.get("00", 0) + p.get("11", 0), 1 / 2)

    def test_no_accepting_states_and_zero_iterations(self):
        e = paper_example()
        baseline = probabilities(e, 2)
        p = probabilities(
            e, 2, grover_iterations=0, amplification_schedule=["grover"] * 2
        )
        for k in baseline:
            self.assertAlmostEqual(p[k], baseline[k])
        e.final_states = set()
        p = probabilities(e, 2, amplification_schedule=["grover"] * 2)
        for k in baseline:
            self.assertAlmostEqual(p[k], baseline[k])

    def test_iteration_count_and_one_input_diffusion(self):
        e = paper_example()
        self.assertAlmostEqual(
            probabilities(
                e, 1, grover_iterations=2, amplification_schedule=["grover"] * 1
            )["1"],
            1 / 4,
        )
        e = automaton(1, 1, 0, lambda k, s, c: s, {"0"})
        self.assertAlmostEqual(
            probabilities(e, 1, amplification_schedule=["grover"] * 1)["0"], 1 / 2
        )

    def test_barriers_and_zero_bound(self):
        e = paper_example()
        self.assertAlmostEqual(
            probabilities(
                e, 2, add_barrier_q=True, amplification_schedule=["grover"] * 2
            )["1"],
            1,
        )
        self.assertAlmostEqual(
            probabilities(e, 0, amplification_schedule=["grover"] * 0)["0"], 1
        )

    def test_scratch_is_uncomputed(self):
        e = paper_example()
        (bdd, formulas) = delta_to_bdds(e)
        width = sum(bdd_to_qc(bdd, f, False).num_qubits - 3 for f in formulas)
        qc = bqrlg_parallel(
            e, 2, amplification_schedule=["grover"] * 2
        ).remove_final_measurements(inplace=False)
        state = Statevector.from_instruction(qc)
        self.assertAlmostEqual(
            state.probabilities(qargs=list(range(1, 1 + width)))[0], 1
        )

    def test_validation(self):
        for kwargs in ({"grover_iterations": -1},):
            with self.assertRaises(ValueError):
                bqrlg_parallel(paper_example(), 1, **kwargs)
        with self.assertRaises(ValueError):
            bqrlg_parallel(paper_example(), -1)


if __name__ == "__main__":
    unittest.main()
