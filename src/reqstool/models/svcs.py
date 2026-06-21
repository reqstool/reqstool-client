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


@unique
class VERIFICATIONPHASE(Enum):
    BUILD = "build"
    POST_BUILD = "post-build"


EXPECTS_MVRS = [
    VERIFICATIONTYPES.MANUAL_TEST,
    VERIFICATIONTYPES.REVIEW,
    VERIFICATIONTYPES.PLATFORM,
    VERIFICATIONTYPES.OTHER,
]
EXPECTS_AUTOMATED_TESTS = [VERIFICATIONTYPES.AUTOMATED_TEST]


class SVCData(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    id: UrnId
    title: str
    description: Optional[str] = None
    verification: VERIFICATIONTYPES
    phase: VERIFICATIONPHASE = VERIFICATIONPHASE.BUILD
    instructions: Optional[str] = None
    revision: VersionField
    lifecycle: LifecycleData = Field(default_factory=lambda: LifecycleData(state=LIFECYCLESTATE.EFFECTIVE, reason=None))
    requirement_ids: List[UrnId] = Field(default_factory=list)
    source_line: Optional[int] = None
    source_col_start: Optional[int] = None
    source_col_end: Optional[int] = None


class SVCsData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # key: svc_id
    cases: Dict[UrnId, SVCData] = Field(default_factory=dict)
    # key: urn
    filters: Dict[str, SVCFilter] = Field(default_factory=dict)
