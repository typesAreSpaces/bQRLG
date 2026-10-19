"""Run the three Figure 14 configurations and save their circuits and comparison."""

import argparse
import json
from copy import deepcopy
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from qiskit import ClassicalRegister, transpile
from qiskit_aer import AerSimulator

from .bqrlg import bqrlg_parallel
from .examples import efaq3

CONFIGURATIONS = (
    ("no_amplification", "No amplification", ("none", "none"), "crimson"),
    ("grover", "Grover + Grover", ("grover", "grover"), "royalblue"),
    ("fnr_grover", "FnR + Grover", ("fnr", "grover"), "limegreen"),
)


def figure14_automaton(panel):
    """Panel (a) uses EFAQ3; panel (b) removes Figure 15's two edges."""
    efaq = deepcopy(efaq3())
    if panel == "b":
        # From state 1: every p rejects; every q goes to state 2.
        # Duplicate q's surviving branch across NDCs, as in the paper's
        # description that half of the first-step runs reach state 2.
        for choice in ("0", "1"):
            for symbol, next_state in (("0", "00"), ("1", "10")):
                suffix = symbol + choice
                efaq.delta["01" + suffix] = next_state + suffix
    elif panel != "a":
        raise ValueError("panel must be a or b")
    return efaq


def simulate(qc, shots, seed):
    """Return sampled counts and exact probabilities in state/symbol order."""
    measured = [None] * qc.num_clbits
    for instruction in qc.data:
        if instruction.operation.name == "measure":
            c = qc.find_bit(instruction.clbits[0]).index
            measured[c] = qc.find_bit(instruction.qubits[0]).index
    if any(q is None for q in measured):
        raise ValueError("Every classical bit must have a final measurement")
    simulation = qc.remove_final_measurements(inplace=False)
    simulation.save_probabilities_dict(measured)
    simulation.add_register(ClassicalRegister(len(measured), "readout"))
    simulation.measure(measured, range(len(measured)))
    simulator = AerSimulator(method="matrix_product_state", max_parallel_threads=1)
    compiled = transpile(
        simulation, simulator, optimization_level=0, seed_transpiler=seed
    )
    result = simulator.run(compiled, shots=shots, seed_simulator=seed).result()
    if not result.success:
        raise RuntimeError(result.status)
    # EFAQ encodings put the MSB first in q0,q1. Reverse Qiskit's display
    # order to obtain final-state encoding, first symbol, second symbol.
    counts = {
        key.replace(" ", "")[::-1]: int(value)
        for key, value in result.get_counts().items()
    }
    probabilities = {
        format(int(key), f"0{len(measured)}b")[::-1]: float(value)
        for key, value in result.data()["probabilities"].items()
        if value > 1e-12
    }
    return dict(sorted(counts.items())), dict(sorted(probabilities.items()))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", choices=("a", "b", "both"), default="both")
    parser.add_argument("--shots", type=int, default=1024)
    parser.add_argument("--seed", type=int, default=2023)
    parser.add_argument(
        "--fnr-iterations",
        type=int,
        default=2,
        help="Two first-step corrections remove all reject branches in panel b",
    )
    parser.add_argument(
        "--skip-circuits",
        action="store_true",
        help="Save the comparison histogram and data without circuit PNGs",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "figures",
    )
    args = parser.parse_args(argv)
    if args.shots < 1 or args.fnr_iterations < 0:
        parser.error("shots must be positive and fnr-iterations nonnegative")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    panels = ("a", "b") if args.panel == "both" else (args.panel,)
    report = {
        "shots": args.shots,
        "seed": args.seed,
        "fnr_iterations": args.fnr_iterations,
        "label_order": "final state (2 bits), first symbol, second symbol",
        "note": "Fresh samples; bit labels follow the paper prose, not its inconsistent printed bins. "
        "Two FnR iterations reproduce panel b's fully accepting green series; "
        "the paper does not specify its iteration count.",
        "panels": {},
    }
    for panel in panels:
        efaq = figure14_automaton(panel)
        runs = {}
        for key, label, schedule, _ in CONFIGURATIONS:
            qc = bqrlg_parallel(
                efaq,
                2,
                amplification_schedule=schedule,
                fnr_iterations=args.fnr_iterations,
                reject_state="00",
            )
            counts, probabilities = simulate(qc, args.shots, args.seed)
            acceptance = sum(
                p
                for outcome, p in probabilities.items()
                if outcome[:2] in efaq.final_states
            )
            runs[key] = {
                "label": label,
                "schedule": list(schedule),
                "counts": counts,
                "probabilities": probabilities,
                "acceptance_probability": acceptance,
                "qubits": qc.num_qubits,
            }
            print(f"Panel {panel}, {label}: acceptance = {acceptance:.6f}; {counts}")
            if not args.skip_circuits:
                figure = qc.draw(output="mpl", fold=35)
                try:
                    figure.savefig(
                        args.output_dir / f"figure14_{panel}_{key}_circuit.png",
                        dpi=160,
                        bbox_inches="tight",
                    )
                finally:
                    plt.close(figure)
        report["panels"][panel] = runs
    figure, axes = plt.subplots(
        1, len(panels), figsize=(8 * len(panels), 5), squeeze=False
    )
    for panel, ax in zip(panels, axes[0]):
        runs = report["panels"][panel]
        labels = sorted(
            {outcome for run in runs.values() for outcome in run["probabilities"]}
        )
        for index, (key, label, _, color) in enumerate(CONFIGURATIONS):
            xs = [i + (index - 1) * 0.25 for i in range(len(labels))]
            values = [runs[key]["counts"].get(outcome, 0) for outcome in labels]
            ax.bar(xs, values, width=0.25, label=label, color=color)
        ax.set_xticks(range(len(labels)), labels, rotation=60)
        ax.set(
            xlabel="Final state | first symbol | second symbol",
            ylabel="Count",
            title=f"({panel}) {'EFAQ3 / Figure 13' if panel == 'a' else 'Modified EFAQ3 / Figure 15'}",
        )
        ax.set_ylim(
            0,
            max(1, max(v for r in runs.values() for v in r["counts"].values())) * 1.15,
        )
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        ax.set_axisbelow(True)
        ax.legend()
    figure.suptitle(f"Figure 14 reconstruction — {args.shots} shots per configuration")
    figure.tight_layout()
    figure.savefig(args.output_dir / "figure14.png", dpi=200, bbox_inches="tight")
    plt.close(figure)
    (args.output_dir / "figure14_results.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(f"Saved comparison and results to {args.output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
