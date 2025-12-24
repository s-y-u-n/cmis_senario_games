from __future__ import annotations

from sim_contribution.config import Config
from sim_contribution.evaluation.types import ExperimentReport
from sim_contribution.viz.plots import plot_all


def build_dashboard(report: ExperimentReport, config: Config, outdir: str) -> None:
    plot_all(report.true_params, report.season_log, report.strategy_results, config, outdir)
