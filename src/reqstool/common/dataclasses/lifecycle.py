# Copyright © LFV

from __future__ import annotations

from enum import Enum, unique
from typing import Optional

from pydantic import BaseModel, ConfigDict


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


class LifecycleData(BaseModel):
    model_config = ConfigDict(frozen=True)

    reason: Optional[str] = None
    state: LIFECYCLESTATE = LIFECYCLESTATE.EFFECTIVE

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> LifecycleData:
        if data is None:
            return cls(state=LIFECYCLESTATE.EFFECTIVE, reason=None)
        return cls(
            state=LIFECYCLESTATE(data["state"]),
            reason=data.get("reason"),
        )
