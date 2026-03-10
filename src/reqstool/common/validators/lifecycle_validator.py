# Copyright © LFV

from collections import namedtuple
import logging
from typing import Union
from reqstool.common.models.lifecycle import LIFECYCLESTATE, lifecycle_state_sort_order
from reqstool.common.models.urn_id import UrnId
from reqstool.models.annotations import AnnotationData
from reqstool.models.combined_indexed_dataset import CombinedIndexedDataset
from reqstool.models.requirements import RequirementData
from reqstool.models.svcs import SVCData
from reqstool_python_decorators.decorators.decorators import Requirements


Warning = namedtuple("Warning", ["state", "message"])


@Requirements("REQ_037", "REQ_038")
class LifecycleValidator:
    """
    Logs warnings if any requirement or SVC is used despite being marked deprecated or obsolete.
    """

    def __init__(self, cid: CombinedIndexedDataset):
        self._cid = cid
        self.warnings: list[Warning] = []

        self._validate()

    def _validate(self):
        self._check_defunct_annotations(self._cid.annotations_impls, self._cid.requirements)
        self._check_defunct_annotations(self._cid.annotations_tests, self._cid.svcs)
        self._check_mvr_references()
        self._check_svc_references()

        self.warnings.sort(key=lambda warning: lifecycle_state_sort_order[warning.state])
        for warning in self.warnings:
            logging.warning(warning.message)

    def _check_defunct_annotations(
        self,
        annotations: dict[UrnId, list[AnnotationData]],
        collection_to_check: dict[UrnId, Union[RequirementData, SVCData]],
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

    def _check_mvr_references(self):
        """
        Creates warnings if any MVR contains a reference to defunct SVCs
        """
        mvrs_from_svc = self._cid.mvrs_from_svc
        svcs = self._cid.svcs

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

    def _check_svc_references(self):
        """
        Creates warnings if any defunct requirement is referenced by active SVCs
        """
        reqs = self._cid.requirements
        svcs_from_req = self._cid.svcs_from_req
        svcs = self._cid.svcs

        for urn_id, referenced_urn_ids in svcs_from_req.items():
            if urn_id not in reqs:
                continue
            state = reqs[urn_id].lifecycle.state
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
