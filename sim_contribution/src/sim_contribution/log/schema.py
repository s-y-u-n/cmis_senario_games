from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from sim_contribution.observation.types import PhaseAStats


@dataclass(frozen=True)
class Player:
    player_id: int


@dataclass(frozen=True)
class TeamLog:
    match_id: int
    team_id: int
    members: Tuple[int, ...]
    v_true: float
    y_obs: float
    z: float
    rank: str
    breakdown: Dict[str, float]

    def to_dict(self) -> dict:
        return {
            "match_id": self.match_id,
            "team_id": self.team_id,
            "members": list(self.members),
            "v_true": self.v_true,
            "y_obs": self.y_obs,
            "z": self.z,
            "rank": self.rank,
            "breakdown": dict(self.breakdown),
        }


@dataclass(frozen=True)
class MatchLog:
    match_id: int
    teams: List[TeamLog]

    def to_dict(self) -> dict:
        return {
            "match_id": self.match_id,
            "teams": [team.to_dict() for team in self.teams],
        }


@dataclass(frozen=True)
class SeasonLog:
    matches: List[MatchLog]
    phase_a_stats: PhaseAStats

    def to_dict(self) -> dict:
        return {
            "matches": [match.to_dict() for match in self.matches],
            "phase_a_stats": self.phase_a_stats.to_dict(),
        }
