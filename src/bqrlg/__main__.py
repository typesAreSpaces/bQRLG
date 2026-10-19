from .examples import efaq1, testing_bqrlg_parrallel
from .examples import efaq3


def main() -> int:
    testing_bqrlg_parrallel(efaq1(), 2, False)
    # testing_bqrlg_parrallel(efaq3(), 1, True)
    return 0


if __name__ == "__main__":
    main()
