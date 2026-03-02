# Copyright © LFV

from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Dict, List, Set

from packaging.version import Version

from reqstool.common.dataclasses.lifecycle import LIFECYCLESTATE, LifecycleData
from reqstool.common.dataclasses.urn_id import UrnId
from reqstool.filters.requirements_filters import RequirementFilter
from reqstool.models.implementations import ImplementationDataInterface
from reqstool.models.imports import ImportDataInterface


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
class SIGNIFANCETYPES(Enum):
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


@dataclass
class ReferenceData:
    requirement_ids: Set[UrnId] = field(default_factory=set)


@dataclass
class RequirementData:
    id: UrnId
    title: str
    significance: SIGNIFANCETYPES
    description: str
    rationale: str
    revision: Version
    lifecycle: LifecycleData = field(default_factory=lambda: LifecycleData(state=LIFECYCLESTATE.EFFECTIVE, reason=None))
    implementation: IMPLEMENTATION = field(default=IMPLEMENTATION.IN_CODE)
    categories: List[CATEGORIES] = field(default_factory=list)
    references: List[ReferenceData] = field(default_factory=list)


@dataclass
class MetaData:
    urn: str
    variant: VARIANTS
    title: str
    url: str


@dataclass
class RequirementsData:
    metadata: MetaData
    implementations: List[ImplementationDataInterface] = field(default_factory=list)
    imports: List[ImportDataInterface] = field(default_factory=list)
    # key: urn
    filters: Dict[str, RequirementFilter] = field(default_factory=dict)
    requirements: Dict[str, RequirementData] = field(default_factory=dict)
