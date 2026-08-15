# Copyright © LFV

from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from reqstool.common.snapshot_fingerprint import SnapshotFingerprint
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

    # URN provenance: location type and URI from the LocationResolver
    location_type: Optional[str] = None
    location_uri: Optional[str] = None

    # Resolved file paths (file_type → absolute path), only populated for LocalLocation
    source_paths: Dict[str, str] = Field(default_factory=dict)

    # Identity of the local input files this dataset was parsed from, for staleness detection
    # by long-lived servers. Empty for non-local locations (version-pinned, materialized to tmp).
    fingerprint: SnapshotFingerprint = Field(default_factory=SnapshotFingerprint)


class CombinedRawDataset(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    initial_model_urn: str
    urn_parsing_order: List[str] = Field(default_factory=list)
    parsing_graph: Dict[str, List[Tuple[str, str]]] = Field(default_factory=dict)
    raw_datasets: Dict[str, RawDataset] = Field(default_factory=dict)

    # Aggregated resolved file paths: urn → file_type → absolute path (LSP only, LocalLocation only)
    urn_source_paths: Dict[str, Dict[str, str]] = Field(default_factory=dict)

    # Merged fingerprint of every local input file parsed into this dataset
    fingerprint: SnapshotFingerprint = Field(default_factory=SnapshotFingerprint)
