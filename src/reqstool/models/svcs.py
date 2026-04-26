# Copyright © LFV

from enum import Enum, unique
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from reqstool.common.models.lifecycle import LIFECYCLESTATE, LifecycleData
from reqstool.common.models.urn_id import UrnId
from reqstool.filters.svcs_filters import SVCFilter
from reqstool.models.requirements import VersionField


@unique
class VERIFICATIONTYPES(Enum):
    AUTOMATED_TEST = "automated-test"
    MANUAL_TEST = "manual-test"
    REVIEW = "review"
    PLATFORM = "platform"
    OTHER = "other"


class SVCData(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    id: UrnId
    title: str
    description: Optional[str] = None
    verification: VERIFICATIONTYPES
    instructions: Optional[str] = None
    revision: VersionField
    lifecycle: LifecycleData = Field(default_factory=lambda: LifecycleData(state=LIFECYCLESTATE.EFFECTIVE, reason=None))
    requirement_ids: List[UrnId] = Field(default_factory=list)
    source_line: Optional[int] = None


class SVCsData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # key: svc_id
    cases: Dict[UrnId, SVCData] = Field(default_factory=dict)
    # key: urn
    filters: Dict[str, SVCFilter] = Field(default_factory=dict)
