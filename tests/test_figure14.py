import unittest

from bqrlg.__main__ import CONFIGURATIONS, figure14_automaton, simulate
from bqrlg.bqrlg import bqrlg_parallel


class Figure14Tests(unittest.TestCase):
    def test_exact_distributions(self):
        expected = {
            "a": {
                "no_amplification": {
                    "0100": 1 / 4,
                    "1001": 1 / 8,
                    "1010": 1 / 8,
                    "1011": 1 / 16,
                    "1101": 1 / 8,
                    "1110": 1 / 8,
                    "1111": 3 / 16,
                },
                "grover": {"1110": 1 / 2, "1111": 1 / 2},
                "fnr_grover": {"1101": 1 / 2, "1110": 1 / 8, "1111": 3 / 8},
            },
            "b": {
                "no_amplification": {
                    "0000": 1 / 4,
                    "0001": 1 / 4,
                    "1010": 1 / 4,
                    "1011": 1 / 8,
                    "1111": 1 / 8,
                },
                "grover": {"0000": 1 / 4, "0001": 1 / 4, "1111": 1 / 2},
                "fnr_grover": {"1111": 1.0},
            },
        }
        for panel in ("a", "b"):
            for key, _, schedule, _ in CONFIGURATIONS:
                with self.subTest(panel=panel, configuration=key):
                    qc = bqrlg_parallel(
                        figure14_automaton(panel),
                        2,
                        amplification_schedule=schedule,
                        fnr_iterations=2,
                    )
                    counts, probabilities = simulate(qc, 64, 2023)
                    self.assertEqual(sum(counts.values()), 64)
                    self.assertEqual(set(probabilities), set(expected[panel][key]))
                    for outcome, p in expected[panel][key].items():
                        self.assertAlmostEqual(probabilities[outcome], p)

    def test_single_fnr_iteration_is_not_claimed_to_be_complete(self):
        qc = bqrlg_parallel(
            figure14_automaton("b"),
            2,
            amplification_schedule=("fnr", "grover"),
            fnr_iterations=1,
        )
        _, probs = simulate(qc, 32, 2023)
        self.assertAlmostEqual(
            sum(p for k, p in probs.items() if k.startswith("11")), 3 / 4
        )

    def test_schedule_validation(self):
        e = figure14_automaton("a")
        for options in (
            {"amplification_schedule": ("fnr",)},
            {"amplification_schedule": ("none", "bad")},
            {"amplification_schedule": ("fnr", "grover"), "enable_grover": True},
            {"amplification_schedule": ("fnr", "grover"), "reject_state": "0"},
        ):
            with self.assertRaises(ValueError):
                bqrlg_parallel(e, 2, **options)


if __name__ == "__main__":
    unittest.main()
