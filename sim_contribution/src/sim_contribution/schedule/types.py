from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

Team = Tuple[int, ...]
Partition = List[Team]
Schedule = List[Partition]


@dataclass(frozen=True)
class MatchSchedule:
    match_id: int
    teams: Partition
