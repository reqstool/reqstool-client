# Copyright © LFV

from typing import Tuple

from reqstool.common.validators.lifecycle_validator import LifecycleValidator
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.location import LocationInterface
from reqstool.model_generators.combined_raw_datasets_generator import CombinedRawDatasetsGenerator
from reqstool.models.raw_datasets import CombinedRawDataset
from reqstool.storage.database import RequirementsDatabase
from reqstool.storage.filter_processor import DatabaseFilterProcessor
from reqstool.storage.requirements_repository import RequirementsRepository


def build_database(
    location: LocationInterface,
    semantic_validator: SemanticValidator,
    filter_data: bool = True,
) -> Tuple[RequirementsDatabase, CombinedRawDataset]:
    db = RequirementsDatabase()

    crdg = CombinedRawDatasetsGenerator(
        initial_location=location,
        semantic_validator=semantic_validator,
        database=db,
    )
    crd = crdg.combined_raw_datasets

    if filter_data:
        DatabaseFilterProcessor(db, crd.raw_datasets).apply_filters()

    repo = RequirementsRepository(db)
    LifecycleValidator(repo)

    return db, crd
