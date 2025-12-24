from __future__ import annotations

from typing import Callable, Dict, List
import numpy as np

from sim_contribution.config import Config
from sim_contribution.log.schema import MatchLog, SeasonLog, TeamLog
from sim_contribution.observation.noise import add_noise
from sim_contribution.observation.ranking import assign_rank, compute_phase_a_stats, z_score
from sim_contribution.players.param_generator import generate_true_params
from sim_contribution.players.types import TrueParams
from sim_contribution.production.team_value import compute_team_value
from sim_contribution.schedule.generator import generate_schedule
from sim_contribution.schedule.types import Partition
from sim_contribution.strategies.greedy_interaction import greedy_interaction_partition
from sim_contribution.strategies.lexcel_weber_pairing import lexcel_weber_pairing
from sim_contribution.strategies.random_partition import random_partition
from sim_contribution.evaluation.types import ExperimentReport, StrategyResult


def run_phase_a(seed: int, config: Config) -> tuple[SeasonLog, TrueParams]:
    rng = np.random.default_rng(seed)
    true_params = generate_true_params(rng, config)
    schedule = generate_schedule(rng, config)

    raw_matches = []
    all_y = []

    for match_id, partition in enumerate(schedule):
        team_entries = []
        for team_id, members in enumerate(partition):
            team_value = compute_team_value(members, true_params, config)
            y_obs = add_noise(team_value.value, rng, config.noise_sigma)
            team_entries.append(
                {
                    "match_id": match_id,
                    "team_id": team_id,
                    "members": tuple(members),
                    "v_true": team_value.value,
                    "y_obs": y_obs,
                    "breakdown": team_value.breakdown,
                }
            )
            all_y.append(y_obs)
        raw_matches.append(team_entries)

    phase_a_stats = compute_phase_a_stats(all_y, config)

    matches: List[MatchLog] = []
    for match_id, team_entries in enumerate(raw_matches):
        teams: List[TeamLog] = []
        for entry in team_entries:
            z = z_score(entry["y_obs"], phase_a_stats)
            rank = assign_rank(z, phase_a_stats.thresholds)
            teams.append(
                TeamLog(
                    match_id=entry["match_id"],
                    team_id=entry["team_id"],
                    members=entry["members"],
                    v_true=entry["v_true"],
                    y_obs=entry["y_obs"],
                    z=z,
                    rank=rank,
                    breakdown=entry["breakdown"],
                )
            )
        matches.append(MatchLog(match_id=match_id, teams=teams))

    season_log = SeasonLog(matches=matches, phase_a_stats=phase_a_stats)
    return season_log, true_params


def propose_partition(
    strategy_fn: Callable[[SeasonLog, np.random.Generator, Config], Partition],
    season_log: SeasonLog,
    rng: np.random.Generator,
    config: Config,
) -> Partition:
    return strategy_fn(season_log, rng, config)


def evaluate_partition(
    partition: Partition,
    true_params: TrueParams,
    phase_a_stats,
    rng: np.random.Generator,
    config: Config,
    name: str,
) -> StrategyResult:
    teams: List[TeamLog] = []
    total_y = 0.0
    rank_counts: Dict[str, int] = {"A": 0, "B": 0, "C": 0, "D": 0, "E": 0}

    for team_id, members in enumerate(partition):
        team_value = compute_team_value(members, true_params, config)
        y_obs = add_noise(team_value.value, rng, config.noise_sigma)
        z = z_score(y_obs, phase_a_stats)
        rank = assign_rank(z, phase_a_stats.thresholds)
        team_log = TeamLog(
            match_id=0,
            team_id=team_id,
            members=tuple(members),
            v_true=team_value.value,
            y_obs=y_obs,
            z=z,
            rank=rank,
            breakdown=team_value.breakdown,
        )
        teams.append(team_log)
        total_y += y_obs
        rank_counts[rank] += 1

    return StrategyResult(
        name=name,
        partition=partition,
        teams=teams,
        total_y=total_y,
        rank_counts=rank_counts,
    )


def _strategy_random(season_log: SeasonLog, rng: np.random.Generator, config: Config) -> Partition:
    return random_partition(config.n_players, rng, config)


def _strategy_greedy(season_log: SeasonLog, rng: np.random.Generator, config: Config) -> Partition:
    return greedy_interaction_partition(season_log, rng, config)


def _strategy_lexcel(season_log: SeasonLog, rng: np.random.Generator, config: Config) -> Partition:
    return lexcel_weber_pairing(season_log, rng, config)


def run_experiment(seed: int, config: Config) -> ExperimentReport:
    season_log, true_params = run_phase_a(seed, config)

    strategy_fns = {
        "random": _strategy_random,
        "greedy_interaction": _strategy_greedy,
        "lexcel_weber": _strategy_lexcel,
    }

    rng = np.random.default_rng(seed + 1000)
    results: List[StrategyResult] = []
    for name, fn in strategy_fns.items():
        rng_strategy = np.random.default_rng(rng.integers(0, 2**32 - 1))
        partition = propose_partition(fn, season_log, rng_strategy, config)
        eval_result = evaluate_partition(
            partition,
            true_params,
            season_log.phase_a_stats,
            rng_strategy,
            config,
            name,
        )
        results.append(eval_result)

    return ExperimentReport(season_log=season_log, true_params=true_params, strategy_results=results)
