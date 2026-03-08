# Copyright © LFV

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Optional


@unique
class LIFECYCLESTATE(Enum):
    DRAFT = "draft"
    EFFECTIVE = "effective"
    DEPRECATED = "deprecated"
    OBSOLETE = "obsolete"


lifecycle_state_sort_order = {
    LIFECYCLESTATE.OBSOLETE: 0,
    LIFECYCLESTATE.DEPRECATED: 1,
    LIFECYCLESTATE.EFFECTIVE: 2,
    LIFECYCLESTATE.DRAFT: 3,
}


@dataclass
class LifecycleData:
    reason: str = field(default=str)
    state: LIFECYCLESTATE = field(default=LIFECYCLESTATE.EFFECTIVE)

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> LifecycleData:
        if data is None:
            return cls(state=LIFECYCLESTATE.EFFECTIVE, reason=None)
        return cls(
            state=LIFECYCLESTATE(data["state"]),
            reason=data.get("reason"),
        )
