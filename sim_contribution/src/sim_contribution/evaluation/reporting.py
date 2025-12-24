from __future__ import annotations

import csv
import json
import os
from typing import Dict, List

from sim_contribution.evaluation.types import ExperimentReport, StrategyResult
from sim_contribution.log.schema import SeasonLog, TeamLog
from sim_contribution.players.types import TrueParams
from sim_contribution.config import Config
from sim_contribution.indices.empirical_interaction import compute_empirical_interaction_scores
from sim_contribution.indices.pair_profile import compute_pair_profile
from sim_contribution.observation.ranking import RANK_ORDER


def _team_log_row(team: TeamLog) -> Dict[str, object]:
    row = {
        "match_id": team.match_id,
        "team_id": team.team_id,
        "members": ",".join(str(m) for m in team.members),
        "v_true": team.v_true,
        "y_obs": team.y_obs,
        "z": team.z,
        "rank": team.rank,
    }
    for key in ["base", "diversity", "affinity", "cooperation", "comm_cost"]:
        row[key] = team.breakdown.get(key, 0.0)
    return row


def save_phase_a_logs(season_log: SeasonLog, outdir: str) -> None:
    os.makedirs(outdir, exist_ok=True)
    json_path = os.path.join(outdir, "phase_a_log.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(season_log.to_dict(), f, indent=2)

    csv_path = os.path.join(outdir, "phase_a_teams.csv")
    rows: List[Dict[str, object]] = []
    for match in season_log.matches:
        for team in match.teams:
            rows.append(_team_log_row(team))
    if rows:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)


def save_phase_b_logs(strategy_results: List[StrategyResult], outdir: str) -> None:
    os.makedirs(outdir, exist_ok=True)
    json_path = os.path.join(outdir, "phase_b_results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump([result.to_dict() for result in strategy_results], f, indent=2)

    for result in strategy_results:
        csv_path = os.path.join(outdir, f"phase_b_{result.name}.csv")
        rows = [_team_log_row(team) for team in result.teams]
        if not rows:
            continue
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)


def save_true_params(true_params: TrueParams, outdir: str) -> None:
    os.makedirs(outdir, exist_ok=True)
    players = [
        {
            "player_id": p.player_id,
            "ability": p.ability,
            "cooperativeness": p.cooperativeness,
            "skill": p.skill.tolist(),
        }
        for p in true_params.players
    ]
    payload = {
        "players": players,
        "affinity": true_params.affinity.tolist(),
    }
    path = os.path.join(outdir, "true_params.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def save_phase_a_indices(season_log: SeasonLog, config: Config, outdir: str) -> None:
    os.makedirs(outdir, exist_ok=True)

    # Observed team stats
    obs: Dict[tuple[int, ...], Dict[str, object]] = {}
    size_y: Dict[int, List[float]] = {}
    for match in season_log.matches:
        for team in match.teams:
            key = tuple(sorted(int(m) for m in team.members))
            entry = obs.setdefault(
                key,
                {
                    "size": len(key),
                    "n_obs": 0,
                    "sum_y": 0.0,
                    "sum_z": 0.0,
                    "rank_counts": {r: 0 for r in RANK_ORDER},
                },
            )
            entry["n_obs"] = int(entry["n_obs"]) + 1
            entry["sum_y"] = float(entry["sum_y"]) + float(team.y_obs)
            entry["sum_z"] = float(entry["sum_z"]) + float(team.z)
            entry["rank_counts"][team.rank] = int(entry["rank_counts"][team.rank]) + 1
            size_y.setdefault(len(key), []).append(float(team.y_obs))

    size_base = {k: (sum(v) / len(v) if v else 0.0) for k, v in size_y.items()}

    interaction_scores = compute_empirical_interaction_scores(season_log, config)
    pair_profiles = compute_pair_profile(season_log, config)

    # Unified coalition list (size 1..3). For undefined metrics, use None (-> null in JSON).
    def _all_coalitions() -> List[tuple[int, ...]]:
        players = list(range(config.n_players))
        coalitions: List[tuple[int, ...]] = []
        for i in players:
            coalitions.append((i,))
        for i in players:
            for j in range(i + 1, config.n_players):
                coalitions.append((i, j))
        for i in players:
            for j in range(i + 1, config.n_players):
                for k in range(j + 1, config.n_players):
                    coalitions.append((i, j, k))
        return coalitions

    rows: List[Dict[str, object]] = []
    for coalition in _all_coalitions():
        size = len(coalition)
        observed = obs.get(coalition)

        n_obs = int(observed["n_obs"]) if observed else 0
        mean_y = (float(observed["sum_y"]) / n_obs) if observed and n_obs > 0 else None
        mean_z = (float(observed["sum_z"]) / n_obs) if observed and n_obs > 0 else None
        base_same_size = float(size_base.get(size, 0.0)) if observed and n_obs > 0 else None
        raw = (mean_y - base_same_size) if (mean_y is not None and base_same_size is not None) else None
        w = (n_obs / (n_obs + config.interaction_alpha)) if observed and n_obs > 0 else None
        score = float(interaction_scores[coalition]) if coalition in interaction_scores else None

        pair_vec = pair_profiles.get((coalition[0], coalition[1])) if size == 2 else None

        rank_counts = observed["rank_counts"] if observed else {r: 0 for r in RANK_ORDER}
        row: Dict[str, object] = {
            "members": ",".join(str(int(m)) for m in coalition),
            "size": size,
            "n_obs": n_obs,
            "mean_y_obs": mean_y,
            "mean_z": mean_z,
            "base_same_size_mean_y": base_same_size,
            "interaction_raw": raw,
            "interaction_w": w,
            "interaction_score": score,
            "pair_A": int(pair_vec[0]) if pair_vec is not None else None,
            "pair_B": int(pair_vec[1]) if pair_vec is not None else None,
            "pair_C": int(pair_vec[2]) if pair_vec is not None else None,
            "pair_D": int(pair_vec[3]) if pair_vec is not None else None,
            "pair_E": int(pair_vec[4]) if pair_vec is not None else None,
            "rank_A": int(rank_counts["A"]),
            "rank_B": int(rank_counts["B"]),
            "rank_C": int(rank_counts["C"]),
            "rank_D": int(rank_counts["D"]),
            "rank_E": int(rank_counts["E"]),
        }
        rows.append(row)

    json_path = os.path.join(outdir, "phase_a_indices.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

    csv_path = os.path.join(outdir, "phase_a_indices.csv")
    if rows:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)


def summarize_results(strategy_results: List[StrategyResult]) -> str:
    lines = []
    for result in strategy_results:
        lines.append(f"Strategy: {result.name}")
        lines.append(f"  total_y: {result.total_y:.3f}")
        lines.append(f"  ranks: {result.rank_counts}")
        lines.append("  partition: " + " | ".join(
            ",".join(str(m) for m in team) for team in result.partition
        ))
    return "\n".join(lines)


def save_all_outputs(report: ExperimentReport, outdir: str) -> None:
    save_phase_a_logs(report.season_log, outdir)
    save_phase_b_logs(report.strategy_results, outdir)
    save_true_params(report.true_params, outdir)
