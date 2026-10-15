from .examples import efaq1, testing_bqrlg_parrallel


def main() -> int:
    testing_bqrlg_parrallel(efaq1(), 2, True)
    return 0


if __name__ == "__main__":
    main()
