from .examples import bdd_to_qc_example1
from .examples import step_example1
from .examples import print_automata
from .examples import testing_delta_to_bdds
from .examples import testing_bqrlg_parrallel
from .examples import efaq1

def main() -> int:
    # bdd_to_qc_example1()
    # step_example1()
    # print_automata(efaq1())
    # testing_delta_to_bdds(efaq1())
    # testing_bqrlg_parrallel(efaq1(), 2)
    testing_bqrlg_parrallel(efaq1(), 1, True)
    return 0

if __name__ == '__main__':
    main()
