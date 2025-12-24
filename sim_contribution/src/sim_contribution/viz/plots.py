from __future__ import annotations

import os
from typing import List
import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sim_contribution.evaluation.types import StrategyResult
from sim_contribution.log.schema import SeasonLog, TeamLog
from sim_contribution.players.types import TrueParams
from sim_contribution.config import Config


def _save(fig: plt.Figure, outdir: str, filename: str) -> None:
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, filename)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_player_attributes(true_params: TrueParams, config: Config, outdir: str) -> None:
    abilities = [p.ability for p in true_params.players]
    cooper = [p.cooperativeness for p in true_params.players]
    skills = true_params.skills()
    affinity = true_params.affinity

    fig, axes = plt.subplots(3, 2, figsize=(12, 11))

    axes[0, 0].bar(range(len(abilities)), abilities, color="#4C78A8")
    axes[0, 0].set_title("Ability (a_i)")
    axes[0, 0].set_xlabel("Player")

    axes[0, 1].bar(range(len(cooper)), cooper, color="#F58518")
    axes[0, 1].set_title("Cooperativeness (c_i)")
    axes[0, 1].set_xlabel("Player")

    im1 = axes[1, 0].imshow(skills, aspect="auto", cmap="viridis")
    axes[1, 0].set_title("Skill vectors (s_i)")
    axes[1, 0].set_xlabel("Skill dimension")
    axes[1, 0].set_ylabel("Player")
    fig.colorbar(im1, ax=axes[1, 0], shrink=0.8)

    max_abs = np.max(np.abs(affinity)) if affinity.size else 1.0
    im2 = axes[1, 1].imshow(affinity, cmap="coolwarm", vmin=-max_abs, vmax=max_abs)
    axes[1, 1].set_title("Affinity matrix (h_ij)")
    axes[1, 1].set_xlabel("Player")
    axes[1, 1].set_ylabel("Player")
    fig.colorbar(im2, ax=axes[1, 1], shrink=0.8)

    axes[2, 0].axis("off")
    weights_text = "\n".join(
        [
            "Model weights (for tuning)",
            f"- ability weight: 1.0",
            f"- skill/diversity weight (lambda_div): {config.lambda_div}",
            f"- affinity weight: 1.0 (scale via sigma_h={config.sigma_h})",
            f"- cooperation weight (lambda_coop): {config.lambda_coop}",
            f"- g(|T|): {dict(config.g_map)}",
        ]
    )
    axes[2, 0].text(0.0, 1.0, weights_text, va="top", ha="left", fontsize=10, family="monospace")

    axes[2, 1].axis("off")

    _save(fig, outdir, "players.png")


def plot_phase_a_teams(season_log: SeasonLog, outdir: str) -> None:
    rows = []
    for match in season_log.matches:
        for team in match.teams:
            rows.append(
                [
                    team.match_id,
                    team.team_id,
                    ",".join(str(m) for m in team.members),
                    f"{team.y_obs:.2f}",
                    team.rank,
                ]
            )

    fig, ax = plt.subplots(figsize=(12, 8))
    ax.axis("off")
    table = ax.table(
        cellText=rows,
        colLabels=["match", "team", "members", "y", "rank"],
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.2)
    ax.set_title("Phase A teams")

    _save(fig, outdir, "phase_a_teams.png")


def _stacked_breakdown(ax: plt.Axes, teams: List[TeamLog], title: str) -> None:
    components = ["base", "diversity", "affinity", "cooperation", "comm_cost"]
    colors = {
        "base": "#4C78A8",
        "diversity": "#54A24B",
        "affinity": "#E45756",
        "cooperation": "#F58518",
        "comm_cost": "#72B7B2",
    }
    x = np.arange(len(teams))
    bottom_pos = np.zeros(len(teams))
    bottom_neg = np.zeros(len(teams))

    for comp in components:
        vals = np.array([t.breakdown.get(comp, 0.0) for t in teams])
        pos = np.clip(vals, 0, None)
        neg = np.clip(vals, None, 0)
        ax.bar(x, pos, bottom=bottom_pos, label=comp, color=colors.get(comp))
        ax.bar(x, neg, bottom=bottom_neg, label="_nolegend_", color=colors.get(comp))
        bottom_pos += pos
        bottom_neg += neg

    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"T{idx}" for idx in range(len(teams))])
    ax.set_title(title)


def plot_phase_a_breakdowns(season_log: SeasonLog, outdir: str) -> None:
    all_teams = [team for match in season_log.matches for team in match.teams]
    if not all_teams:
        return

    sorted_teams = sorted(all_teams, key=lambda t: t.y_obs)
    bottom = sorted_teams[:3]
    top = sorted_teams[-3:]
    selected = top + bottom

    fig, ax = plt.subplots(figsize=(10, 6))
    _stacked_breakdown(ax, selected, "Phase A breakdowns (top/bottom teams)")
    ax.legend(loc="upper right", fontsize=8)
    _save(fig, outdir, "phase_a_breakdown.png")


def plot_phase_b_partitions(strategy_results: List[StrategyResult], outdir: str) -> None:
    if not strategy_results:
        return

    fig, axes = plt.subplots(len(strategy_results), 1, figsize=(10, 4 * len(strategy_results)))
    if len(strategy_results) == 1:
        axes = [axes]

    for ax, result in zip(axes, strategy_results):
        _stacked_breakdown(ax, result.teams, f"Phase B: {result.name}")
        ax.set_xticklabels(
            [
                ",".join(str(m) for m in team.members)
                for team in result.teams
            ],
            rotation=30,
            ha="right",
        )
        ax.legend(loc="upper right", fontsize=8)

    _save(fig, outdir, "phase_b_partitions.png")


def plot_phase_b_summary(strategy_results: List[StrategyResult], outdir: str) -> None:
    names = [r.name for r in strategy_results]
    totals = [r.total_y for r in strategy_results]

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].bar(names, totals, color="#54A24B")
    axes[0].set_title("Phase B total y")
    axes[0].set_ylabel("sum y")

    rank_order = ["A", "B", "C", "D", "E"]
    x = np.arange(len(names))
    bottom = np.zeros(len(names))
    for rank in rank_order:
        vals = np.array([r.rank_counts.get(rank, 0) for r in strategy_results])
        axes[1].bar(x, vals, bottom=bottom, label=rank)
        bottom += vals
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(names)
    axes[1].set_title("Phase B rank distribution")
    axes[1].legend(fontsize=8)

    _save(fig, outdir, "phase_b_summary.png")


def plot_all(
    true_params: TrueParams,
    season_log: SeasonLog,
    strategy_results: List[StrategyResult],
    config: Config,
    outdir: str,
) -> None:
    plot_player_attributes(true_params, config, outdir)
    plot_phase_a_teams(season_log, outdir)
    plot_phase_a_breakdowns(season_log, outdir)
    plot_phase_b_partitions(strategy_results, outdir)
    plot_phase_b_summary(strategy_results, outdir)
