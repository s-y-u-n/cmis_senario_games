"""Empirical interaction scores computed from observed Phase A logs.

This is an observational, decision-making proxy. It is NOT the true contribution
metric used in later research, and it should not be interpreted as such.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple

from sim_contribution.config import Config
from sim_contribution.indices.types import InteractionScores
from sim_contribution.log.schema import SeasonLog


def _collect_team_observations(season_log: SeasonLog) -> Dict[Tuple[int, ...], List[float]]:
    observations: Dict[Tuple[int, ...], List[float]] = defaultdict(list)
    for match in season_log.matches:
        for team in match.teams:
            key = tuple(sorted(team.members))
            observations[key].append(team.y_obs)
    return observations


def compute_empirical_interaction_scores(
    season_log: SeasonLog, config: Config
) -> InteractionScores:
    observations = _collect_team_observations(season_log)

    size_totals: Dict[int, List[float]] = defaultdict(list)
    for team_key, values in observations.items():
        size_totals[len(team_key)].extend(values)

    size_means: Dict[int, float] = {
        size: (sum(vals) / len(vals) if vals else 0.0) for size, vals in size_totals.items()
    }

    scores: InteractionScores = {}
    for team_key, values in observations.items():
        n_obs = len(values)
        mean_y = sum(values) / n_obs if n_obs > 0 else 0.0
        base = size_means.get(len(team_key), 0.0)
        raw = mean_y - base
        w = n_obs / (n_obs + config.interaction_alpha)
        score = w * raw
        scores[team_key] = score

    return scores
