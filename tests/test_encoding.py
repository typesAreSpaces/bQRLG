import itertools
import json
import os
import subprocess
import sys
import unittest
from copy import deepcopy

from qiskit.quantum_info import Statevector

from bqrlg import DFA, EFAQ, NFA, bqrlg_parallel, bqrlg_series
from bqrlg.bqrlg import delta_to_bdds


def accepts_nfa(nfa, word):
    states = {nfa.initial_state}
    for symbol in word:
        states = {nxt for state in states for nxt in nfa.delta.get((state, symbol), ())}
    return bool(states & nfa.final_states)


def accepts_dfa(dfa, word):
    states = {dfa.initial_state}
    for symbol in word:
        states = {
            dfa.delta[state, symbol + str(choice)]
            for state in states
            for choice in range(dfa.num_ndcs)
        }
    return bool(states & dfa.final_states)


class EncodingTests(unittest.TestCase):
    def test_missing_transitions_and_spare_choices_preserve_language(self):
        nfa = NFA(
            {"a", "b"},
            {"s", "f", "t", "r"},
            {
                ("s", "a"): {"f"},
                ("s", "b"): set(),
                ("t", "a"): {"s", "f", "t"},
                ("t", "b"): {"r"},
                ("r", "a"): {"r"},
                ("r", "b"): {"r"},
            },
            "s",
            {"f"},
        )
        dfa = DFA(nfa)
        self.assertFalse(accepts_dfa(dfa, "ba"))
        self.assertTrue(all(dfa.delta["s", "a" + str(c)] == "f" for c in range(4)))
        for length in range(5):
            for word in itertools.product(sorted(nfa.symbols), repeat=length):
                self.assertEqual(accepts_nfa(nfa, word), accepts_dfa(dfa, word), word)
        e = EFAQ(dfa)
        for length in (1, 2):
            qc = bqrlg_parallel(e, length).remove_final_measurements(inplace=False)
            sv = Statevector.from_instruction(qc)
            # Previously ba could reach an accepting state; all length-two
            # words now reject because f has no outgoing NFA transitions.
            if length == 2:
                probs = sv.probabilities_dict(
                    qargs=list(reversed(range(e.num_bits_states)))
                )
                self.assertAlmostEqual(
                    sum(p for k, p in probs.items() if k in e.final_states), 0
                )

    def test_deterministic_widths_and_decoder(self):
        nfa = NFA(
            {"a", "b"},
            {"s", "f"},
            {(state, symbol): {"f"} for state in ("s", "f") for symbol in ("a", "b")},
            "s",
            {"f"},
        )
        e = EFAQ(DFA(nfa), {"a": "0", "b": "1"}, {"s": "0", "f": "1"})
        self.assertEqual(e.num_bits_ndcs, 0)
        self.assertEqual(e.dec_raw_S, {"0": "a", "1": "b"})
        self.assertTrue(all(len(k) == len(v) == 2 for k, v in e.delta.items()))
        qc = bqrlg_parallel(e, 2).remove_final_measurements(inplace=False)
        self.assertAlmostEqual(
            Statevector.from_instruction(qc).probabilities(qargs=[0])[1], 1
        )

    def test_singleton_alphabet_and_state(self):
        for accepting in (set(), {"s"}):
            e = EFAQ(DFA(NFA({"a"}, {"s"}, {("s", "a"): {"s"}}, "s", accepting)))
            self.assertEqual(e.num_bits_symbols, 0)
            self.assertEqual(e.num_bits_ndcs, 0)
            self.assertEqual(e.dec_raw_S, {"": "a"})
            for bound in (0, 2):
                qc = bqrlg_parallel(e, bound).remove_final_measurements(inplace=False)
                sv = Statevector.from_instruction(qc)
                probs = sv.probabilities_dict(
                    qargs=list(reversed(range(e.num_bits_states)))
                )
                self.assertAlmostEqual(
                    sum(p for k, p in probs.items() if k in e.final_states),
                    bool(accepting),
                )

    def test_unused_binary_codes_reject(self):
        states = {"s", "f", "r"}
        symbols = {"a", "b", "c"}
        nfa = NFA(
            symbols, states, {(s, a): {s} for s in states for a in symbols}, "s", {"f"}
        )
        e = EFAQ(DFA(nfa))
        self.assertEqual(len(e.delta), 1 << (e.num_bits_states + e.num_bits_symbols))
        for key, value in e.delta.items():
            state, symbol = key[:2], key[2:]
            if state not in e.states or symbol not in e.symbols:
                self.assertEqual(value, e.reject_state + symbol)
        self.assertNotIn(e.reject_state, e.final_states)
        # The fourth binary symbol is padding, so only 3/4 of each
        # uniform input superposition stays in the accepting state.
        e.initial_state = next(code for code, name in e.dec_K.items() if name == "f")
        qc = bqrlg_parallel(e, 2).remove_final_measurements(inplace=False)
        probs = Statevector.from_instruction(qc).probabilities_dict(qargs=[1, 0])
        self.assertAlmostEqual(
            sum(p for k, p in probs.items() if k in e.final_states), 9 / 16
        )

    def test_fnr_uses_the_encoded_reject_sink_by_default(self):
        nfa = NFA(
            {"a", "b"},
            {"s", "f"},
            {("s", "a"): {"f"}, ("f", "a"): {"f"}, ("f", "b"): {"f"}},
            "s",
            {"f"},
        )
        dfa = DFA(nfa)
        e = EFAQ(
            dfa, {"a": "0", "b": "1"}, {"s": "10", "f": "01", dfa.reject_state: "11"}
        )
        qc = bqrlg_parallel(e, 1, amplification_schedule=["fnr"])
        state = Statevector.from_instruction(
            qc.remove_final_measurements(inplace=False)
        )
        self.assertAlmostEqual(state.probabilities_dict(qargs=[1, 0])["01"], 1)

    def test_encodings_and_overrides_do_not_mutate_inputs(self):
        nfa = NFA(
            {"a", "b"},
            {"s", "f"},
            {(s, a): {"f"} for s in ("s", "f") for a in ("a", "b")},
            "s",
            {"f"},
        )
        dfa = DFA(nfa)
        symbols = {}
        states = {}
        before = deepcopy(dfa.delta)
        override = {(s, a): "s" for s, a in dfa.delta}
        EFAQ(dfa, symbols, states, override)
        self.assertEqual((symbols, states, dfa.delta), ({}, {}, before))
        e = EFAQ(dfa)
        self.assertEqual(e.delta, EFAQ(DFA(nfa)).delta)

    def test_hash_seed_does_not_change_encoding_or_choice_assignments(self):
        script = """
import json
from bqrlg import NFA, DFA, EFAQ
states = {"start", "left", "right", "finish"}
symbols = {"a", "b"}
delta = {(s, a): {"left", "right", "finish"} for s in states for a in symbols}
e = EFAQ(DFA(NFA(symbols, states, delta, "start", {"finish"})))
print(json.dumps([e.dec_raw_S, e.dec_K, e.delta], sort_keys=True))
"""
        outputs = [
            subprocess.check_output(
                [sys.executable, "-c", script],
                text=True,
                env={**os.environ, "PYTHONHASHSEED": str(seed)},
            )
            for seed in (1, 99)
        ]
        self.assertEqual(json.loads(outputs[0]), json.loads(outputs[1]))

    def test_encoding_validation(self):
        nfa = NFA(
            {"a", "b"},
            {"s", "f"},
            {(s, a): {"f"} for s in ("s", "f") for a in ("a", "b")},
            "s",
            {"f"},
        )
        dfa = DFA(nfa)
        for symbols, states, override in (
            ({"a": "0", "b": "0"}, None, None),
            ({"a": "x", "b": "1"}, None, None),
            ({"a": "00", "b": "01"}, None, None),
            ({"a": "0"}, None, None),
            (None, {"s": "0", "f": "0"}, None),
            (None, None, {("s", "a0"): "f"}),
            (None, None, {k: "unknown" for k in dfa.delta}),
        ):
            with self.assertRaises(ValueError):
                EFAQ(dfa, symbols, states, override)

    def test_nfa_validation(self):
        for symbols, states, delta, initial, accepting in (
            (set(), {"s"}, {}, "s", set()),
            ({"a"}, set(), {}, "s", set()),
            ({"a"}, {"s"}, {}, "missing", set()),
            ({"a"}, {"s"}, {}, "s", {"missing"}),
            ({"a"}, {"s"}, {("s", "a"): {"missing"}}, "s", set()),
            ({"a"}, {"s"}, {("s", "b"): {"s"}}, "s", set()),
        ):
            with self.assertRaises(ValueError):
                NFA(symbols, states, delta, initial, accepting)

    def test_malformed_efaq_transition_is_rejected(self):
        from test_grover import paper_example

        e = paper_example()
        key = next(iter(e.delta))
        e.delta[key + "0"] = e.delta.pop(key)
        with self.assertRaises(ValueError):
            delta_to_bdds(e)

    def test_serial_builder_fails_explicitly(self):
        with self.assertRaises(NotImplementedError):
            bqrlg_series(None, 2)


if __name__ == "__main__":
    unittest.main()
