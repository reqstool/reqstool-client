# Copyright © LFV


import logging
import os

from reqstool.common.models.urn_id import UrnId
from reqstool.common.project_session import ProjectSession
from reqstool.locations.local_location import LocalLocation
from reqstool.model_generators.parsing_config import ParsingConfig
from reqstool.models.annotations import AnnotationData
from reqstool.models.mvrs import MVRData
from reqstool.models.requirements import RequirementData
from reqstool.models.svcs import SVCData
from reqstool.models.test_data import TestData

logger = logging.getLogger(__name__)


class ProjectState(ProjectSession):
    def __init__(self, reqstool_path: str):
        super().__init__(
            LocalLocation(path=reqstool_path),
            parsing_config=ParsingConfig(include_line_numbers=True),
        )
        self._reqstool_path = reqstool_path

    @property
    def reqstool_path(self) -> str:
        return self._reqstool_path

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

    def _urn_for_yaml_path(self, file_path: str, file_type: str) -> str | None:
        norm_target = os.path.normpath(file_path)
        for urn, paths in self._urn_source_paths.items():
            stored = paths.get(file_type)
            if stored is not None and os.path.normpath(stored) == norm_target:
                return urn
        return None

    def get_requirements_for_yaml(self, file_path: str) -> list[RequirementData]:
        if not self._ready or self._repo is None:
            return []
        urn = self._urn_for_yaml_path(file_path, "requirements")
        if urn is None:
            return []
        return [r for r in self._repo.get_all_requirements().values() if r.id.urn == urn]

    def get_svcs_for_yaml(self, file_path: str) -> list[SVCData]:
        if not self._ready or self._repo is None:
            return []
        urn = self._urn_for_yaml_path(file_path, "svcs")
        if urn is None:
            return []
        return [s for s in self._repo.get_all_svcs().values() if s.id.urn == urn]

    def get_mvrs_for_yaml(self, file_path: str) -> list[MVRData]:
        if not self._ready or self._repo is None:
            return []
        urn = self._urn_for_yaml_path(file_path, "mvrs")
        if urn is None:
            return []
        return [m for m in self._repo.get_all_mvrs().values() if m.id.urn == urn]
