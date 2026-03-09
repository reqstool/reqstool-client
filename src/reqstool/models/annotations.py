# Copyright © LFV

from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field

from reqstool.common.dataclasses.urn_id import UrnId


class AnnotationData(BaseModel):
    element_kind: str  # FIELD, METHOD, CLASS, ENUM, INTERFACE, RECORD
    fully_qualified_name: str


class AnnotationsData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    implementations: Dict[UrnId, List[AnnotationData]] = Field(default_factory=dict)
    tests: Dict[UrnId, List[AnnotationData]] = Field(default_factory=dict)
