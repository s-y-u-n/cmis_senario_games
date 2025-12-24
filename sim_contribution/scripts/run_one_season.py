from __future__ import annotations

import argparse
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_ROOT = os.path.join(PROJECT_ROOT, "src")
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from sim_contribution.config import Config
from sim_contribution.evaluation.reporting import save_all_outputs, save_phase_a_indices, summarize_results
from sim_contribution.evaluation.runner import run_experiment
from sim_contribution.viz.plots import plot_all


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--outdir", type=str, default="outputs")
    args = parser.parse_args()

    config = Config()
    report = run_experiment(args.seed, config)

    outdir = os.path.abspath(args.outdir)
    save_all_outputs(report, outdir)
    save_phase_a_indices(report.season_log, config, outdir)
    plot_all(report.true_params, report.season_log, report.strategy_results, config, outdir)

    print(summarize_results(report.strategy_results))


if __name__ == "__main__":
    main()
