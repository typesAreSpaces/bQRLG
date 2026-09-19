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
# Computational Basis State
CBState : TypeAlias = str
EncS : TypeAlias = dict[Symbol, CBState]
EncK : TypeAlias = dict[State, CBState]
DecS : TypeAlias = dict[CBState, Symbol]
DecK : TypeAlias = dict[CBState, State]
EFAQDelta : TypeAlias = dict[CBState, CBState]

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
                 delta : NFADelta,
                 initial_state : Symbol, final_states: Symbols):
        self.symbols = symbols
        self.states = states
        self.delta = delta
        self.initial_state = initial_state
        self.final_states = final_states

        self.num_symbols = len(symbols)
        self.num_states = len(states)

    def _print(self) -> None:
        print(">> Symbols:", self.symbols)
        print(">> States:", self.states)
        print(">> Transitions:", self.delta)
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
        # Encode delta from nfa using
        # NDCs
        max_ndc = 1
        num_bits_ndcs = 0
        self.delta : DFADelta = dict()
        for (state, symbol), next_states in nfa.delta.items():
            ndc = 0
            for next_state in next_states:
                self.delta[(state, symbol + str(ndc))] = next_state
                ndc += 1
                if max_ndc < ndc:
                    max_ndc = 2*max_ndc
                    num_bits_ndcs += 1

        self.num_ndcs = max_ndc
        self.num_bits_ndcs = num_bits_ndcs

        # Missing paths with NDCs
        # are directed to the same state
        self.symbols : Symbols = set()
        for symb in nfa.symbols:
            for ndc in range(max_ndc):
                symb_ndc = symb + str(ndc)
                self.symbols.add(symb_ndc)
                for state in nfa.states:
                    entry = (state, symb_ndc)
                    if entry not in self.delta:
                        self.delta[entry] = state
        # ------------------------------------------------------------

        self.raw_symbols = nfa.symbols

        self.initial_state = nfa.initial_state
        self.final_states = nfa.final_states

        # This keep track of the NFA symbols,
        # not the DFA + NDC symbols
        self.num_symbols = nfa.num_symbols
        self.num_states = nfa.num_states

    def _print(self) -> None:
        print(">> Symbols:", self.symbols)
        print(">> States:", self.states)
        print(">> Transitions:", self.delta)
        print(">> Initial state:", self.initial_state)
        print(">> Final states:", self.final_states)

# Encoding Finite-state Automata
# for Quantum Circuits
# About the image of self.delta:
# - The first self.num_bits_states bits
# correspond to the binary encoding for states, 
# - Then, for each symbol_i, we have 
# self.num_bits_symbols_i + nds bits 
# Observations:
# - The EFAQ is unique up to 
#   - enc_K
#   - enc_raw_S
#   - dfa.delta, i.e., up to assignment of NDCs
class EFAQ:
    def __init__(self, dfa : DFA, 
                 enc_raw_S : EncS = dict(), 
                 enc_K : EncK = dict(),
                 opt_delta : DFADelta = dict()):
        if opt_delta:
            dfa.delta = opt_delta
        self.num_bits_symbols = ceil(log2(dfa.num_symbols))
        if not enc_raw_S:
            for counter, x in enumerate(dfa.raw_symbols):
                enc_raw_S[x] = bin(counter)[2:].zfill(self.num_bits_symbols)
        self.dec_raw_S : DecS = {v: k for k, v in enc_raw_S.items()}

        enc_S : EncS = dict()
        self.num_bits_ndcs = dfa.num_bits_ndcs
        for x in dfa.raw_symbols:
            for y in range(dfa.num_ndcs):
                enc_S[x + str(y)] = enc_raw_S[x] \
                        + bin(y)[2:].zfill(self.num_bits_ndcs)

        self.num_bits_states = ceil(log2(dfa.num_states))
        self.dec_raw_S : DecS = dict()
        if not enc_K:
            for counter, x in enumerate(dfa.states):
                enc_K[x] = bin(counter)[2:].zfill(self.num_bits_states)
        self.dec_K : DecK = {v: k for k, v in enc_K.items()}

        DBG(">> enc_raw_S", enc_raw_S)
        DBG(">> enc_K", enc_K)

        self.symbols = {enc_S[x] for x in dfa.symbols}
        self.states = {enc_K[x] for x in dfa.states}

        self.delta : EFAQDelta  = dict()
        for state in dfa.states:
            for symbol in dfa.symbols:
                _input = enc_K[state] + enc_S[symbol]
                _output = enc_K[dfa.delta[(state, symbol)]] + enc_S[symbol]
                self.delta[_input] = _output

        self.initial_state = enc_K[dfa.initial_state]
        self.final_states = {enc_K[x] for x in dfa.final_states}

        self.num_symbols = dfa.num_symbols
        self.num_states = dfa.num_states

    def _print(self) -> None:
        print(">> Symbols:", self.symbols)
        print(">> States:", self.states)
        print(">> Transitions:", self.delta)
        print(">> Initial state:", self.initial_state)
        print(">> Final states:", self.final_states)
