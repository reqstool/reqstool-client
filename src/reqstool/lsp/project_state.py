# Copyright © LFV

from __future__ import annotations

import logging

from reqstool.common.models.urn_id import UrnId
from reqstool.common.validators.lifecycle_validator import LifecycleValidator
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.locations.local_location import LocalLocation
from reqstool.model_generators.combined_raw_datasets_generator import CombinedRawDatasetsGenerator
from reqstool.models.annotations import AnnotationData
from reqstool.models.mvrs import MVRData
from reqstool.models.requirements import RequirementData
from reqstool.models.svcs import SVCData
from reqstool.models.test_data import TestData
from reqstool.storage.database import RequirementsDatabase
from reqstool.storage.database_filter_processor import DatabaseFilterProcessor
from reqstool.storage.requirements_repository import RequirementsRepository

logger = logging.getLogger(__name__)


class ProjectState:
    def __init__(self, reqstool_path: str):
        self._reqstool_path = reqstool_path
        self._db: RequirementsDatabase | None = None
        self._repo: RequirementsRepository | None = None
        self._ready: bool = False
        self._error: str | None = None
        self._urn_source_paths: dict[str, dict[str, str]] = {}

    @property
    def ready(self) -> bool:
        return self._ready

    @property
    def error(self) -> str | None:
        return self._error

    @property
    def reqstool_path(self) -> str:
        return self._reqstool_path

    def build(self) -> None:
        self.close()
        self._error = None
        db = RequirementsDatabase()
        try:
            location = LocalLocation(path=self._reqstool_path)
            holder = ValidationErrorHolder()
            semantic_validator = SemanticValidator(validation_error_holder=holder)

            crdg = CombinedRawDatasetsGenerator(
                initial_location=location,
                semantic_validator=semantic_validator,
                database=db,
            )
            crd = crdg.combined_raw_datasets

            DatabaseFilterProcessor(db, crd.raw_datasets).apply_filters()
            LifecycleValidator(RequirementsRepository(db))

            self._db = db
            self._repo = RequirementsRepository(db)
            self._urn_source_paths = dict(crd.urn_source_paths)
            self._ready = True
            logger.info("Built project state for %s", self._reqstool_path)
        except SystemExit as e:
            logger.warning("build_database() called sys.exit(%s) for %s", e.code, self._reqstool_path)
            self._error = f"Pipeline error (exit code {e.code})"
            db.close()
        except Exception as e:
            logger.error("Failed to build project state for %s: %s", self._reqstool_path, e)
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

    def get_initial_urn(self) -> str | None:
        if not self._ready or self._repo is None:
            return None
        return self._repo.get_initial_urn()

    def get_requirement(self, raw_id: str) -> RequirementData | None:
        if not self._ready or self._repo is None:
            return None
        initial_urn = self._repo.get_initial_urn()
        urn_id = UrnId.assure_urn_id(initial_urn, raw_id)
        all_reqs = self._repo.get_all_requirements()
        return all_reqs.get(urn_id)

    def get_svc(self, raw_id: str) -> SVCData | None:
        if not self._ready or self._repo is None:
            return None
        initial_urn = self._repo.get_initial_urn()
        urn_id = UrnId.assure_urn_id(initial_urn, raw_id)
        all_svcs = self._repo.get_all_svcs()
        return all_svcs.get(urn_id)

    def get_svcs_for_req(self, raw_id: str) -> list[SVCData]:
        if not self._ready or self._repo is None:
            return []
        initial_urn = self._repo.get_initial_urn()
        req_urn_id = UrnId.assure_urn_id(initial_urn, raw_id)
        svc_urn_ids = self._repo.get_svcs_for_req(req_urn_id)
        all_svcs = self._repo.get_all_svcs()
        return [all_svcs[uid] for uid in svc_urn_ids if uid in all_svcs]

    def get_mvrs_for_svc(self, raw_id: str) -> list[MVRData]:
        if not self._ready or self._repo is None:
            return []
        initial_urn = self._repo.get_initial_urn()
        svc_urn_id = UrnId.assure_urn_id(initial_urn, raw_id)
        mvr_urn_ids = self._repo.get_mvrs_for_svc(svc_urn_id)
        all_mvrs = self._repo.get_all_mvrs()
        return [all_mvrs[uid] for uid in mvr_urn_ids if uid in all_mvrs]

    def get_all_requirement_ids(self) -> list[str]:
        if not self._ready or self._repo is None:
            return []
        return [uid.id for uid in self._repo.get_all_requirements()]

    def get_mvr(self, raw_id: str) -> MVRData | None:
        if not self._ready or self._repo is None:
            return None
        initial_urn = self._repo.get_initial_urn()
        urn_id = UrnId.assure_urn_id(initial_urn, raw_id)
        return self._repo.get_all_mvrs().get(urn_id)

    def get_all_svc_ids(self) -> list[str]:
        if not self._ready or self._repo is None:
            return []
        return [uid.id for uid in self._repo.get_all_svcs()]

    def get_yaml_paths(self) -> dict[str, dict[str, str]]:
        """Return all URN → file_type → path mappings."""
        return dict(self._urn_source_paths)

    def get_impl_annotations_for_req(self, raw_id: str) -> list[AnnotationData]:
        if not self._ready or self._repo is None:
            return []
        initial_urn = self._repo.get_initial_urn()
        req_urn_id = UrnId.assure_urn_id(initial_urn, raw_id)
        return self._repo.get_annotations_impls_for_req(req_urn_id)

    def get_test_annotations_for_svc(self, raw_id: str) -> list[AnnotationData]:
        if not self._ready or self._repo is None:
            return []
        initial_urn = self._repo.get_initial_urn()
        svc_urn_id = UrnId.assure_urn_id(initial_urn, raw_id)
        return self._repo.get_annotations_tests_for_svc(svc_urn_id)

    def get_test_results_for_svc(self, raw_id: str) -> list[TestData]:
        if not self._ready or self._repo is None:
            return []
        initial_urn = self._repo.get_initial_urn()
        svc_urn_id = UrnId.assure_urn_id(initial_urn, raw_id)
        return self._repo.get_test_results_for_svc(svc_urn_id)

    def get_urn_location(self, urn: str) -> dict | None:
        if not self._ready or self._repo is None:
            return None
        return self._repo.get_urn_location(urn)

    def get_yaml_path(self, urn: str, file_type: str) -> str | None:
        """Return the resolved file path for a given URN and file type (requirements, svcs, mvrs, annotations)."""
        urn_paths = self._urn_source_paths.get(urn)
        if urn_paths is None:
            return None
        return urn_paths.get(file_type)
