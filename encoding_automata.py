from math import log2
from math import ceil

from utilities import DBG

from typing import TypeAlias

Symbol : TypeAlias = str
Symbols : TypeAlias = set[Symbol]
State : TypeAlias = str
States : TypeAlias = set[State]
NFADelta : TypeAlias = dict[tuple[State, Symbol], set[State]]
DFADelta : TypeAlias = dict[tuple[State, Symbol], State]
QuantumState : TypeAlias = str
EncS : TypeAlias = dict[Symbol, QuantumState]
EncK : TypeAlias = dict[State, QuantumState]
EFAQDelta : TypeAlias = dict[QuantumState, QuantumState]

# A DFA is a 5-tuple
#   <\Sigma, K, \Delta, k_{ini}, A>
# where
# - \Sigma is a set of input symbols
# - K is a finite set of states
# - \Delta : K \times \Sigma \rightarrow K
# is a state transition function
# - k_{ini} \in K is the initial state
# - A \subset K is a set of accept states

# A NFA is a 5-tuple
#   <\Sigma, K, \Delta, k_{ini}, A>
# similar to a DFA but
# - \Delta : K \times \Sigma \rightarrow 2^{K}

# Non-deterministic finite automata
# Note: we assume len(symbols) and len(states) are powers of two
# otherwise, we can add enough of these two an artificial
# reject state
class NFA:
    def __init__(self, symbols : Symbols, states : States,
                 transition : NFADelta,
                 initial_state : Symbol, final_states: Symbols):
        self.symbols = symbols
        self.states = states
        self.transition = transition
        self.initial_state = initial_state
        self.final_states = final_states

        self.num_symbols = len(symbols)
        self.num_states = len(states)

    def _print(self):
        print(">> Symbols:", self.symbols)
        print(">> States:", self.states)
        print(">> Transitions:", self.transition)
        print(">> Initial state:", self.initial_state)
        print(">> Final states:", self.final_states)

# Deterministic finite automata
# with NDCs
# Observations:
# - We also need to assume that |\sigma| \times |NDCs| is
# a power of two as well, i.e., |NCDs| is a power of two
class DFA:
    def __init__(self, nfa : NFA):
        self.states = nfa.states

        # ------------------------------------------------------------
        # Encode transition from nfa using
        # NDCs
        max_ndc = 1
        num_bits_ndc = 0
        self.transition : DFADelta = dict()
        for (state, symbol), next_states in nfa.transition.items():
            ndc = 0
            for next_state in next_states:
                self.transition[(state, symbol+str(ndc))] = next_state
                ndc += 1
                if max_ndc < ndc:
                    max_ndc = 2*max_ndc
                    num_bits_ndc += 1

        self.num_ndc = max_ndc
        self.num_bits_ndc = num_bits_ndc

        # Missing paths with NDCs
        # are directed to the same state
        self.symbols : Symbols = set()
        for symb in nfa.symbols:
            for ndc in range(max_ndc):
                symb_ndc = symb+str(ndc)
                self.symbols.add(symb_ndc)
                for state in nfa.states:
                    entry = (state, symb_ndc)
                    if entry not in self.transition:
                        self.transition[entry] = state
        # ------------------------------------------------------------

        self.raw_symbols = nfa.symbols

        self.initial_state = nfa.initial_state
        self.final_states = nfa.final_states

        # This keep track of the NFA symbols,
        # not the DFA + NDC symbols
        self.num_symbols = nfa.num_symbols
        self.num_states = nfa.num_states

    def _print(self):
        print(">> Symbols:", self.symbols)
        print(">> States:", self.states)
        print(">> Transitions:", self.transition)
        print(">> Initial state:", self.initial_state)
        print(">> Final states:", self.final_states)

# Encoding Finite-state Automata
# for Quantum Circuits
# The first self.num_states bits in the image of self.transition
# correspond to state bits, the next self.num_symbols bits correspond
# to symbols bits
# Observations:
# - The EFAQ is unique up to encK and encS
class EFAQ:
    def __init__(self, dfa : DFA):
        enc_raw_S : EncS = dict()
        fill_raw_S = ceil(log2(dfa.num_symbols))
        for counter, x in enumerate(dfa.raw_symbols):
            enc_raw_S[x] = bin(counter)[2:].zfill(fill_raw_S)

        encS : EncS = dict()
        fillNDC = dfa.num_bits_ndc
        fillS = fill_raw_S + fillNDC
        for x in dfa.raw_symbols:
            for y in range(dfa.num_ndc):
                encS[x+str(y)] = enc_raw_S[x] + bin(y)[2:].zfill(fillNDC)

        encK : EncK = dict()
        fillK = ceil(log2(dfa.num_states))
        for counter, x in enumerate(dfa.states):
            encK[x] = bin(counter)[2:].zfill(fillK)

        DBG(">> encK", encK)
        DBG(">> encS", encS)

        self.symbols = {encS[x] for x in dfa.symbols}
        self.states = {encK[x] for x in dfa.states}

        self.transition : EFAQDelta  = dict()
        for state in dfa.states:
            for symbol in dfa.symbols:
                _input = encK[state] + encS[symbol]
                _output = encK[dfa.transition[(state, symbol)]] + encS[symbol]
                self.transition[_input] = _output

        self.initial_state = encK[dfa.initial_state]
        self.final_states = {encK[x] for x in dfa.final_states}

        self.num_symbols = dfa.num_symbols
        self.num_states = dfa.num_states

    def _print(self):
        print(">> Symbols:", self.symbols)
        print(">> States:", self.states)
        print(">> Transitions:", self.transition)
        print(">> Initial state:", self.initial_state)
        print(">> Final states:", self.final_states)
