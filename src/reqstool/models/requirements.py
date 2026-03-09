# Copyright © LFV

from enum import Enum, unique
from typing import Annotated, Dict, List, Optional, Set

from packaging.version import Version
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from reqstool.common.dataclasses.lifecycle import LIFECYCLESTATE, LifecycleData
from reqstool.common.dataclasses.urn_id import UrnId
from reqstool.filters.requirements_filters import RequirementFilter
from reqstool.models.implementations import ImplementationDataInterface
from reqstool.models.imports import ImportDataInterface


def _coerce_version(v):
    if isinstance(v, str):
        return Version(v)
    return v


VersionField = Annotated[Version, BeforeValidator(_coerce_version)]


@unique
class VARIANTS(Enum):
    SYSTEM = "system"
    MICROSERVICE = "microservice"
    EXTERNAL = "external"


@unique
class TYPES(Enum):
    REQUIREMENTS = "requirements"
    SOFTWARE_VERIFICATION_CASES = "software_verification_cases"
    EXTERNAL = "manual_verification_results"


@unique
class SIGNIFICANCETYPES(Enum):
    SHALL = "shall"
    SHOULD = "should"
    MAY = "may"

    def __lt__(self, other):
        if self.__class__ is other.__class__:
            return self._member_names_.index(self.name) < other._member_names_.index(other.name)
        return NotImplemented


@unique
class CATEGORIES(Enum):
    FUNCTIONAL_SUITABILITY = "functional-suitability"
    PERFORMANCE_EFFICIENCY = "performance-efficiency"
    COMPATIBILITY = "compatibility"
    INTERACTION_CAPABILITY = "interaction-capability"
    RELIABILITY = "reliability"
    SECURITY = "security"
    MAINTAINABILITY = "maintainability"
    FLEXIBILITY = "flexibility"
    SAFETY = "safety"


@unique
class IMPLEMENTATION(Enum):
    IN_CODE = "in-code"
    NOT_APPLICABLE = "N/A"


class ReferenceData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    requirement_ids: Set[UrnId] = Field(default_factory=set)


class RequirementData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: UrnId
    title: str
    significance: SIGNIFICANCETYPES
    description: str
    rationale: Optional[str] = None
    revision: VersionField
    lifecycle: LifecycleData = Field(
        default_factory=lambda: LifecycleData(state=LIFECYCLESTATE.EFFECTIVE, reason=None)
    )
    implementation: IMPLEMENTATION = IMPLEMENTATION.IN_CODE
    categories: List[CATEGORIES] = Field(default_factory=list)
    references: Optional[List[ReferenceData]] = Field(default_factory=list)


class MetaData(BaseModel):
    urn: str
    variant: VARIANTS
    title: str
    url: Optional[str] = None


class RequirementsData(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    metadata: MetaData
    implementations: List[ImplementationDataInterface] = Field(default_factory=list)
    imports: List[ImportDataInterface] = Field(default_factory=list)
    # key: urn
    filters: Dict[str, RequirementFilter] = Field(default_factory=dict)
    requirements: Dict[UrnId, RequirementData] = Field(default_factory=dict)
