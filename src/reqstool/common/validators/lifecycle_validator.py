# Copyright © LFV

from __future__ import annotations

from collections import namedtuple
import logging

from reqstool.common.models.lifecycle import LIFECYCLESTATE, lifecycle_state_sort_order
from reqstool.common.models.urn_id import UrnId
from reqstool.models.annotations import AnnotationData
from reqstool.models.requirements import RequirementData
from reqstool.models.svcs import SVCData
from reqstool.storage.requirements_repository import RequirementsRepository
from reqstool_python_decorators.decorators.decorators import Requirements

logger = logging.getLogger(__name__)

Warning = namedtuple("Warning", ["state", "message"])


@Requirements("REQ_037", "REQ_038")
class LifecycleValidator:
    """
    Logs warnings if any requirement or SVC is used despite being marked deprecated or obsolete.
    """

    def __init__(self, repo: RequirementsRepository):
        self._repo = repo
        self.warnings: list[Warning] = []

        self._validate()

    def _validate(self):
        requirements = self._repo.get_all_requirements()
        svcs = self._repo.get_all_svcs()
        annotations_impls = self._repo.get_annotations_impls()
        annotations_tests = self._repo.get_annotations_tests()

        self._check_defunct_annotations(annotations_impls, requirements)
        self._check_defunct_annotations(annotations_tests, svcs)
        self._check_mvr_references(svcs)
        self._check_svc_references(requirements, svcs)

        self.warnings.sort(key=lambda warning: lifecycle_state_sort_order[warning.state])
        for warning in self.warnings:
            logger.warning(warning.message)

    def _check_defunct_annotations(
        self,
        annotations: dict[UrnId, list[AnnotationData]],
        collection_to_check: dict[UrnId, RequirementData | SVCData],
    ):
        """
        Creates warnings for defunct requirements or SVCs that are annotated in the code.
        """
        for urn_id in annotations:
            if urn_id not in collection_to_check:
                continue
            state = collection_to_check[urn_id].lifecycle.state
            if state in (LIFECYCLESTATE.DEPRECATED, LIFECYCLESTATE.OBSOLETE):
                self.warnings.append(
                    Warning(state, f"Urn {urn_id} is used in an annotation despite being {state.value}.")
                )

    def _check_mvr_references(self, svcs: dict[UrnId, SVCData]):
        """
        Creates warnings if any MVR contains a reference to defunct SVCs
        """
        all_mvrs = self._repo.get_all_mvrs()

        # Build mvrs_from_svc index
        mvrs_from_svc: dict[UrnId, list[UrnId]] = {}
        for mvr_uid, mvr_data in all_mvrs.items():
            for svc_uid in mvr_data.svc_ids:
                mvrs_from_svc.setdefault(svc_uid, []).append(mvr_uid)

        for urn_id, related_urn_ids in mvrs_from_svc.items():
            if urn_id not in svcs:
                continue
            state = svcs[urn_id].lifecycle.state
            if state in (LIFECYCLESTATE.DEPRECATED, LIFECYCLESTATE.OBSOLETE):
                plural = "s" if len(related_urn_ids) > 1 else ""
                self.warnings.append(
                    Warning(
                        state,
                        f"The SVC {urn_id} is marked as {state.value} but the MVR{plural} "
                        f"{self._format_list(related_urn_ids)} references it.",
                    )
                )

    def _check_svc_references(self, requirements: dict[UrnId, RequirementData], svcs: dict[UrnId, SVCData]):
        """
        Creates warnings if any defunct requirement is referenced by active SVCs
        """
        # Build svcs_from_req index
        svcs_from_req: dict[UrnId, list[UrnId]] = {}
        for svc_uid, svc_data in svcs.items():
            for req_uid in svc_data.requirement_ids:
                svcs_from_req.setdefault(req_uid, []).append(svc_uid)

        for urn_id, referenced_urn_ids in svcs_from_req.items():
            if urn_id not in requirements:
                continue
            state = requirements[urn_id].lifecycle.state
            if state in (LIFECYCLESTATE.DEPRECATED, LIFECYCLESTATE.OBSOLETE):
                svcs_in_use = [
                    id
                    for id in referenced_urn_ids
                    if id in svcs and svcs[id].lifecycle.state in (LIFECYCLESTATE.EFFECTIVE, LIFECYCLESTATE.DRAFT)
                ]
                if len(svcs_in_use) > 0:
                    plural = "s" if len(svcs_in_use) > 1 else ""
                    self.warnings.append(
                        Warning(
                            state,
                            f"The requirement {urn_id} is marked as {state.value} but the SVC{plural} "
                            f"{self._format_list(svcs_in_use)} references it.",
                        )
                    )

    def _format_list(self, items: list[UrnId]):
        return ", ".join(map(str, items))
