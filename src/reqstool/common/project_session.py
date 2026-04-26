# Copyright © LFV


import logging

from reqstool.common.validators.lifecycle_validator import LifecycleValidator
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.locations.location import LocationInterface
from reqstool.model_generators.combined_raw_datasets_generator import CombinedRawDatasetsGenerator
from reqstool.model_generators.parsing_config import ParsingConfig
from reqstool.storage.database import RequirementsDatabase
from reqstool.storage.database_filter_processor import DatabaseFilterProcessor
from reqstool.storage.requirements_repository import RequirementsRepository

logger = logging.getLogger(__name__)


class ProjectSession:
    """Long-lived database session for a reqstool project loaded from any LocationInterface.

    Keeps the SQLite database open for the lifetime of the session (unlike the
    build_database() context manager which closes on exit). Suitable for servers
    (MCP, LSP) that need persistent read access after a one-time build.
    """

    def __init__(self, location: LocationInterface, parsing_config: ParsingConfig = ParsingConfig()):
        self._location = location
        self._parsing_config = parsing_config
        self._db: RequirementsDatabase | None = None
        self._repo: RequirementsRepository | None = None
        self._urn_source_paths: dict[str, dict[str, str]] = {}
        self._ready: bool = False
        self._error: str | None = None

    @property
    def ready(self) -> bool:
        return self._ready

    @property
    def error(self) -> str | None:
        return self._error

    @property
    def repo(self) -> RequirementsRepository | None:
        return self._repo

    @property
    def urn_source_paths(self) -> dict[str, dict[str, str]]:
        return self._urn_source_paths

    def build(self) -> None:
        self.close()
        self._error = None
        db = RequirementsDatabase()
        try:
            holder = ValidationErrorHolder()
            semantic_validator = SemanticValidator(validation_error_holder=holder)

            crdg = CombinedRawDatasetsGenerator(
                initial_location=self._location,
                semantic_validator=semantic_validator,
                database=db,
                parsing_config=self._parsing_config,
            )
            crd = crdg.combined_raw_datasets

            DatabaseFilterProcessor(db, crd.raw_datasets).apply_filters()
            LifecycleValidator(RequirementsRepository(db))

            self._db = db
            self._repo = RequirementsRepository(db)
            self._urn_source_paths = dict(crd.urn_source_paths)
            self._ready = True
            logger.info("Built project session for %s", self._location)
        except SystemExit as e:
            logger.warning("build() called sys.exit(%s) for %s", e.code, self._location)
            self._error = f"Pipeline error (exit code {e.code})"
            db.close()
        except Exception as e:
            logger.error("Failed to build project session for %s: %s", self._location, e)
            self._error = str(e)
            db.close()

    def rebuild(self) -> None:
        self.build()

    def close(self) -> None:
        if self._db is not None:
            self._db.close()
            self._db = None
        self._repo = None
        self._urn_source_paths = {}
        self._ready = False
