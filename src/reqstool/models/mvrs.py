# Copyright © LFV

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from reqstool.common.dataclasses.urn_id import UrnId


class MVRData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    id: UrnId
    comment: Optional[str] = None
    passed: bool
    svc_ids: List[UrnId] = Field(default_factory=list)


class MVRsData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    results: Dict[UrnId, MVRData] = Field(default_factory=dict)
