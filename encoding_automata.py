from math import log
from math import ceil

from utilities import DBG

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
class NFA:
    def __init__(self, symbols : set[str], states : set[str], 
                 transition : dict[tuple[str, str], set[str]],
                 initial_state : str, final_states: set[str]):
        self.symbols = symbols 
        self.states = states
        self.transition = transition
        self.initial_state = initial_state
        self.final_states = final_states

    def _print(self):
        print(">> Symbols:", self.symbols)
        print(">> States:", self.states)
        print(">> Transitions:", self.transition)
        print(">> Initial state:", self.initial_state)
        print(">> Final states:", self.final_states)

# Deterministic finite automata
# with NDCs
class DFA:
    def __init__(self, nfa : NFA):
        self.states = nfa.states

        # Encode transition from nfa using
        # NDCs
        max_ndc = 0
        self.transition : dict[tuple[str, str], str] = dict()
        for (state, symbol), next_states in nfa.transition.items():
            ndc = 0
            for next_state in next_states:
                self.transition[(state, symbol+str(ndc))] = next_state
                ndc += 1
                if max_ndc < ndc:
                    max_ndc = ndc

        # Missing paths with NDCs
        # are directed to the same state
        self.symbols : set[str] = set()
        for state in nfa.states:
            for symb in nfa.symbols:
                for ndc in range(max_ndc):
                    symb_ndc = symb + str(ndc)
                    self.symbols.add(symb_ndc)
                    entry = (state, symb_ndc)
                    if entry not in self.transition:
                        self.transition[entry] = state

        self.initial_state = nfa.initial_state
        self.final_states = nfa.final_states

    def _print(self):
        print(">> Symbols:", self.symbols)
        print(">> States:", self.states)
        print(">> Transitions:", self.transition)
        print(">> Initial state:", self.initial_state)
        print(">> Final states:", self.final_states)

# Encoding Finite-state Automata 
# for Quantum Circuits
class EFAQ:
    def __init__(self, dfa : DFA):
        encS : dict[str, str] = dict()
        _fillS = ceil(log(len(dfa.symbols))/log(2))
        counter = 0
        for x in dfa.symbols:
            encS[x] = bin(counter)[2:].zfill(_fillS)
            counter += 1

        encK : dict[str, str] = dict()
        _fillK = ceil(log(len(dfa.states))/log(2))
        counter = 0
        for x in dfa.states:
            encK[x] = bin(counter)[2:].zfill(_fillK)
            counter += 1

        # encK = {'y': '1', 'x': '0'}
        # encS = {'q1': '11', 'p0': '00', 'p1': '01', 'q0': '10'}

        DBG(">> encK", encK)
        DBG(">> encS", encS)

        self.symbols = {encS[x] for x in dfa.symbols}
        self.states = {encK[x] for x in dfa.states}

        self.transition : dict[str, str] = dict()
        for state in dfa.states:
            for symbol in dfa.symbols:
                _input = encK[state] + encS[symbol]
                _output = encK[dfa.transition[(state, symbol)]] + encS[symbol]
                self.transition[_input] = _output

        self.initial_state = encK[dfa.initial_state]
        self.final_states = {encK[x] for x in dfa.final_states}

    def _print(self):
        print(">> Symbols:", self.symbols)
        print(">> States:", self.states)
        print(">> Transitions:", self.transition)
        print(">> Initial state:", self.initial_state)
        print(">> Final states:", self.final_states)
