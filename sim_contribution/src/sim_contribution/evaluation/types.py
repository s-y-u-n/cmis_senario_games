from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from sim_contribution.log.schema import SeasonLog, TeamLog
from sim_contribution.players.types import TrueParams
from sim_contribution.schedule.types import Partition


@dataclass(frozen=True)
class StrategyResult:
    name: str
    partition: Partition
    teams: List[TeamLog]
    total_y: float
    rank_counts: Dict[str, int]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "partition": [list(team) for team in self.partition],
            "teams": [team.to_dict() for team in self.teams],
            "total_y": self.total_y,
            "rank_counts": dict(self.rank_counts),
        }


@dataclass(frozen=True)
class ExperimentReport:
    season_log: SeasonLog
    true_params: TrueParams
    strategy_results: List[StrategyResult]

    def to_dict(self) -> dict:
        return {
            "season_log": self.season_log.to_dict(),
            "strategy_results": [result.to_dict() for result in self.strategy_results],
        }
