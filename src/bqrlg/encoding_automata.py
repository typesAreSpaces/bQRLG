from typing import TypeAlias

Symbol: TypeAlias = str
Symbols: TypeAlias = set[Symbol]
State: TypeAlias = str
States: TypeAlias = set[State]
NFADelta: TypeAlias = dict[tuple[State, Symbol], set[State]]
DFADelta: TypeAlias = dict[tuple[State, Symbol], State]
# Computational Basis State
CBState: TypeAlias = str
EncS: TypeAlias = dict[Symbol, CBState]
EncK: TypeAlias = dict[State, CBState]
DecS: TypeAlias = dict[CBState, Symbol]
DecK: TypeAlias = dict[CBState, State]
EFAQDelta: TypeAlias = dict[CBState, CBState]


def _width(size: int) -> int:
    return (size - 1).bit_length()


def _bits(value: int, width: int) -> str:
    return format(value, f"0{width}b") if width else ""


def _encoding(items: set[str], supplied: dict[str, str] | None, width: int, label: str):
    codes = (
        dict(supplied)
        if supplied
        else {item: _bits(index, width) for index, item in enumerate(sorted(items))}
    )
    if set(codes) != items:
        raise ValueError(f"{label} encoding must cover exactly {sorted(items)}")
    if any(
        not isinstance(code, str)
        or len(code) != width
        or any(bit not in "01" for bit in code)
        for code in codes.values()
    ):
        raise ValueError(f"{label} encodings must be binary strings of width {width}")
    if len(set(codes.values())) != len(codes):
        raise ValueError(f"{label} encodings must be unique")
    return codes


class NFA:
    """An epsilon-free NFA; absent transitions reject the input."""

    def __init__(
        self,
        symbols: Symbols,
        states: States,
        delta: NFADelta,
        initial_state: State,
        final_states: States,
    ):
        self.symbols = set(symbols)
        self.states = set(states)
        self.delta = {key: set(destinations) for key, destinations in delta.items()}
        self.initial_state = initial_state
        self.final_states = set(final_states)
        if not self.symbols or not self.states:
            raise ValueError("An NFA needs nonempty symbol and state sets")
        if any(not isinstance(x, str) for x in self.symbols | self.states):
            raise ValueError("Symbols and states must be strings")
        if initial_state not in self.states or not self.final_states <= self.states:
            raise ValueError("Initial and accepting states must belong to states")
        for (state, symbol), destinations in self.delta.items():
            if state not in self.states or symbol not in self.symbols:
                raise ValueError(
                    "Transition sources and symbols must belong to the NFA"
                )
            if not destinations <= self.states:
                raise ValueError("Transition destinations must belong to states")
        self.num_symbols = len(self.symbols)
        self.num_states = len(self.states)

    def _print(self) -> None:
        print(">> Symbols:", self.symbols)
        print(">> States:", self.states)
        print(">> Transitions:", self.delta)
        print(">> Initial state:", self.initial_state)
        print(">> Final states:", self.final_states)


class DFA:
    """Resolve NFA choices over an extended alphabet without changing its language.

    Unused choice codes repeat valid successors cyclically. Missing transitions
    and binary-padding codes reject. Choice assignment is deterministic, but
    repeating successors does not in general sample them uniformly.
    """

    def __init__(self, nfa: NFA):
        self.states = set(nfa.states)
        self.raw_symbols = set(nfa.symbols)
        self.initial_state = nfa.initial_state
        self.final_states = set(nfa.final_states)
        needs_sink = (
            len(self.states) == 1
            or len(self.states) & (len(self.states) - 1) != 0
            or len(self.raw_symbols) & (len(self.raw_symbols) - 1) != 0
            or any(
                not nfa.delta.get((state, symbol))
                for state in self.states
                for symbol in self.raw_symbols
            )
        )
        self.reject_state: State | None = next(
            (
                state
                for state in sorted(self.states - self.final_states)
                if all(
                    nfa.delta.get((state, symbol)) == {state}
                    for symbol in self.raw_symbols
                )
            ),
            None,
        )
        if needs_sink and self.reject_state is None:
            sink = "__reject__"
            while sink in self.states:
                sink += "_"
            self.reject_state = sink
            self.states.add(sink)
        max_choices = max((len(v) for v in nfa.delta.values()), default=1)
        self.num_bits_ndcs = _width(max(1, max_choices))
        self.num_ndcs = 1 << self.num_bits_ndcs
        self.symbols = {
            symbol + str(choice)
            for symbol in self.raw_symbols
            for choice in range(self.num_ndcs)
        }
        if len(self.symbols) != len(self.raw_symbols) * self.num_ndcs:
            raise ValueError("Symbol names collide after appending choice indices")
        self.delta: DFADelta = {}
        for state in sorted(self.states):
            for symbol in sorted(self.raw_symbols):
                successors = sorted(nfa.delta.get((state, symbol), ()))
                if not successors:
                    assert self.reject_state is not None
                    successors = [self.reject_state]
                for choice in range(self.num_ndcs):
                    self.delta[state, symbol + str(choice)] = successors[
                        choice % len(successors)
                    ]
        self.num_symbols = len(self.raw_symbols)
        self.num_states = len(self.states)

    def _print(self) -> None:
        print(">> Symbols:", self.symbols)
        print(">> States:", self.states)
        print(">> Transitions:", self.delta)
        print(">> Initial state:", self.initial_state)
        print(">> Final states:", self.final_states)


class EFAQ:
    """Binary encoding with a total transition table, including padding codes.

    State registers have at least one bit; singleton alphabets and deterministic
    choice registers use zero bits. Explicit encodings must cover every DFA
    state, including any rejecting sink added during NFA conversion.
    """

    def __init__(
        self,
        dfa: DFA,
        enc_raw_S: EncS | None = None,
        enc_K: EncK | None = None,
        opt_delta: DFADelta | None = None,
    ):
        delta = dict(opt_delta) if opt_delta else dict(dfa.delta)
        expected = {(state, symbol) for state in dfa.states for symbol in dfa.symbols}
        if set(delta) != expected:
            raise ValueError(
                "DFA transition table must cover every state and extended symbol"
            )
        if any(destination not in dfa.states for destination in delta.values()):
            raise ValueError("DFA transition destinations must belong to states")
        self.num_bits_symbols = _width(dfa.num_symbols)
        self.num_bits_states = max(1, _width(dfa.num_states))
        self.num_bits_ndcs = dfa.num_bits_ndcs
        symbols = _encoding(dfa.raw_symbols, enc_raw_S, self.num_bits_symbols, "Symbol")
        states = _encoding(dfa.states, enc_K, self.num_bits_states, "State")
        self.dec_raw_S: DecS = {code: symbol for symbol, code in symbols.items()}
        self.dec_K: DecK = {code: state for state, code in states.items()}
        self.reject_state = (
            states[dfa.reject_state] if dfa.reject_state is not None else None
        )
        extended = {
            symbol + str(choice): symbols[symbol] + _bits(choice, self.num_bits_ndcs)
            for symbol in sorted(dfa.raw_symbols)
            for choice in range(dfa.num_ndcs)
        }
        self.symbols = set(extended.values())
        self.states = set(states.values())
        self.initial_state = states[dfa.initial_state]
        self.final_states = {states[state] for state in dfa.final_states}
        self.num_symbols = dfa.num_symbols
        self.num_states = dfa.num_states
        self.delta: EFAQDelta = {}
        input_width = self.num_bits_symbols + self.num_bits_ndcs
        for state_index in range(1 << self.num_bits_states):
            state_code = _bits(state_index, self.num_bits_states)
            for symbol_index in range(1 << input_width):
                symbol_code = _bits(symbol_index, input_width)
                self.delta[state_code + symbol_code] = (
                    self.reject_state + symbol_code
                    if self.reject_state is not None
                    else ""
                )
        for state in sorted(dfa.states):
            for symbol in sorted(dfa.symbols):
                encoded_symbol = extended[symbol]
                self.delta[states[state] + encoded_symbol] = (
                    states[delta[state, symbol]] + encoded_symbol
                )
        if any(not output for output in self.delta.values()):
            raise ValueError("Unused binary codes require a designated rejecting sink")
        if self.reject_state is not None:
            # A designated reject must stay absorbing even with an override.
            for symbol in dfa.symbols:
                if delta[dfa.reject_state, symbol] != dfa.reject_state:
                    raise ValueError("The designated rejecting sink must be absorbing")

    def _print(self) -> None:
        print(">> Symbols:", self.symbols)
        print(">> States:", self.states)
        print(">> Transitions:", self.delta)
        print(">> Initial state:", self.initial_state)
        print(">> Final states:", self.final_states)
