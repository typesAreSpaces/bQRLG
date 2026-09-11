from encoding import NFA, DFA, EFAQ
from tests import simple_qc, bdd_2_qc_example1

def main() -> int:
    # a = EFAQ(DFA(NFA([0, 1], [0, 1], "todo", 0, [1])))
    # simple_qc()
    bdd_2_qc_example1()
    return 0

if __name__ == '__main__':
    main()
