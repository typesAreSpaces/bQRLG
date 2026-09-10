# <\Sigma, K, \Delta, k_{ini}, A>
# \Sigma is a set of input symbols
# K is a finite set of states
# \Delta : K \times \Sigma \rightarrow K
# is a state transition function
# k_{ini} \in K is the initial state
# A \subset K is a set of accept states

# Non-deterministic finite automata
class NFA:
    def __init__(self, symbols, states, transition, initial_state, final_states):
        self.symbols = symbols 
        self.states = states
        self.transition = transition
        self.initial_state = initial_state
        self.final_states = final_states

# Deterministic finite automata
# with NDCs
class DFA:
    def __init__(self, nfa):
        self.symbols = nfa.symbols 
        self.states = nfa.states
        # TODO
        self.transition = nfa.transition
        self.initial_state = nfa.initial_state
        self.final_states = nfa.final_states

# Encoding Finite-state Automata 
# for Quantum Circuits
class EFAQ:
    def __init__(self, dfa):
        # TODO

        self.symbols = dfa.symbols 
        self.states = dfa.states
        self.transition = dfa.transition
        self.initial_state = dfa.initial_state
        self.final_states = dfa.final_states
