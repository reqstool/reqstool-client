# Copyright © LFV


from contextlib import contextmanager
from typing import Generator

from reqstool.common.utils import TempDirectoryManager
from reqstool.common.validators.lifecycle_validator import LifecycleValidator
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.location import LocationInterface
from reqstool.model_generators.combined_raw_datasets_generator import CombinedRawDatasetsGenerator
from reqstool.model_generators.parsing_config import ParsingConfig
from reqstool.models.raw_datasets import CombinedRawDataset
from reqstool.storage.database import RequirementsDatabase
from reqstool.storage.database_filter_processor import DatabaseFilterProcessor
from reqstool.storage.requirements_repository import RequirementsRepository


@contextmanager
def build_database(
    location: LocationInterface,
    semantic_validator: SemanticValidator,
    filter_data: bool = True,
    tmpdir_manager: TempDirectoryManager = None,
    parsing_config: ParsingConfig = ParsingConfig(),
) -> Generator[tuple[RequirementsDatabase, CombinedRawDataset], None, None]:
    _owns_tmpdir = tmpdir_manager is None
    if _owns_tmpdir:
        tmpdir_manager = TempDirectoryManager()
    db = RequirementsDatabase()
    try:
        crdg = CombinedRawDatasetsGenerator(
            initial_location=location,
            semantic_validator=semantic_validator,
            database=db,
            tmpdir_manager=tmpdir_manager,
            parsing_config=parsing_config,
        )
        crd = crdg.combined_raw_datasets

        if filter_data:
            DatabaseFilterProcessor(db, crd.raw_datasets).apply_filters()

        LifecycleValidator(RequirementsRepository(db))

        yield db, crd
    finally:
        db.close()
        if _owns_tmpdir:
            tmpdir_manager.cleanup()
