# Copyright © LFV

from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from reqstool.models.annotations import AnnotationsData
from reqstool.models.mvrs import MVRsData
from reqstool.models.requirements import RequirementsData
from reqstool.models.svcs import SVCsData
from reqstool.models.test_data import TestsData


class RawDataset(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    requirements_data: Optional[RequirementsData] = None

    svcs_data: Optional[SVCsData] = None

    annotations_data: Optional[AnnotationsData] = None

    automated_tests: Optional[TestsData] = None

    mvrs_data: Optional[MVRsData] = None


class CombinedRawDataset(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    initial_model_urn: str
    urn_parsing_order: List[str] = Field(default_factory=list)
    parsing_graph: Dict[str, List[Tuple[str, str]]] = Field(default_factory=dict)
    raw_datasets: Dict[str, RawDataset] = Field(default_factory=dict)
