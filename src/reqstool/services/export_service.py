# Copyright © LFV

import logging
from typing import Dict, List, Optional

from reqstool.common.models.urn_id import UrnId
from reqstool.storage.requirements_repository import RequirementsRepository

logger = logging.getLogger(__name__)


class ExportService:
    def __init__(self, repository: RequirementsRepository):
        self._repo = repository

    def to_export_dict(
        self,
        req_ids: Optional[List[str]] = None,
        svc_ids: Optional[List[str]] = None,
    ) -> dict:
        initial_urn = self._repo.get_initial_urn()
        all_reqs = self._repo.get_all_requirements()
        all_svcs = self._repo.get_all_svcs()
        all_mvrs = self._repo.get_all_mvrs()
        annotations_impls = self._repo.get_annotations_impls()
        annotations_tests = self._repo.get_annotations_tests()
        automated_test_results = self._repo.get_automated_test_results()

        # Apply --req-ids / --svc-ids filtering if provided
        if req_ids or svc_ids:
            resolved_req_ids = self._resolve_ids(req_ids, initial_urn, all_reqs, "Requirement ID")
            resolved_svc_ids = self._resolve_ids(svc_ids, initial_urn, all_svcs, "SVC ID")

            # Include SVCs related to kept requirements
            for req_uid in resolved_req_ids:
                for svc_uid in self._repo.get_svcs_for_req(req_uid):
                    if svc_uid in all_svcs:
                        resolved_svc_ids.add(svc_uid)

            # Include MVRs related to kept SVCs
            kept_mvr_ids = set()
            for svc_uid in resolved_svc_ids:
                for mvr_uid in self._repo.get_mvrs_for_svc(svc_uid):
                    if mvr_uid in all_mvrs:
                        kept_mvr_ids.add(mvr_uid)

            # If --svc-ids but no --req-ids, include requirements referenced by kept SVCs
            if svc_ids and not req_ids:
                for svc_uid in resolved_svc_ids:
                    if svc_uid in all_svcs:
                        for rid in all_svcs[svc_uid].requirement_ids:
                            if rid in all_reqs:
                                resolved_req_ids.add(rid)

            all_reqs = {k: v for k, v in all_reqs.items() if k in resolved_req_ids}
            all_svcs = {k: v for k, v in all_svcs.items() if k in resolved_svc_ids}
            all_mvrs = {k: v for k, v in all_mvrs.items() if k in kept_mvr_ids}
            annotations_impls = {k: v for k, v in annotations_impls.items() if k in resolved_req_ids}
            annotations_tests = {k: v for k, v in annotations_tests.items() if k in resolved_svc_ids}
            automated_test_results = {k: v for k, v in automated_test_results.items() if k in resolved_svc_ids}

        # Build output dict conforming to export_output.schema.json
        requirements = {}
        for uid, req in all_reqs.items():
            req_dict = {
                "urn": uid.urn,
                "id": uid.id,
                "title": req.title,
                "significance": req.significance.value,
                "description": req.description,
                "rationale": req.rationale,
                "lifecycle": {
                    "state": req.lifecycle.state.value,
                    "reason": req.lifecycle.reason,
                },
                "implementation_type": req.implementation.value,
                "categories": [cat.value for cat in req.categories],
                "revision": {
                    "major": req.revision.major,
                    "minor": req.revision.minor,
                    "patch": req.revision.micro,
                },
            }
            if req.references:
                req_dict["references"] = [
                    {"requirement_ids": [str(rid) for rid in sorted(ref.requirement_ids)]} for ref in req.references
                ]
            requirements[str(uid)] = req_dict

        svcs = {}
        for uid, svc in all_svcs.items():
            svcs[str(uid)] = {
                "urn": uid.urn,
                "id": uid.id,
                "title": svc.title,
                "description": svc.description,
                "verification": svc.verification.value,
                "instructions": svc.instructions,
                "lifecycle": {
                    "state": svc.lifecycle.state.value,
                    "reason": svc.lifecycle.reason,
                },
                "revision": {
                    "major": svc.revision.major,
                    "minor": svc.revision.minor,
                    "patch": svc.revision.micro,
                },
                "requirement_ids": [str(rid) for rid in svc.requirement_ids],
            }

        mvrs = {}
        for uid, mvr in all_mvrs.items():
            mvr_dict = {
                "urn": uid.urn,
                "id": uid.id,
                "passed": mvr.passed,
                "svc_ids": [str(sid) for sid in mvr.svc_ids],
            }
            if mvr.comment is not None:
                mvr_dict["comment"] = mvr.comment
            mvrs[str(uid)] = mvr_dict

        impl_annotations = {}
        for uid, anns in annotations_impls.items():
            impl_annotations[str(uid)] = [
                {"element_kind": a.element_kind, "fully_qualified_name": a.fully_qualified_name} for a in anns
            ]

        test_annotations = {}
        for uid, anns in annotations_tests.items():
            test_annotations[str(uid)] = [
                {"element_kind": a.element_kind, "fully_qualified_name": a.fully_qualified_name} for a in anns
            ]

        test_results = {}
        for uid, tests in automated_test_results.items():
            test_results[str(uid)] = [
                {"fully_qualified_name": t.fully_qualified_name, "status": t.status.value} for t in tests
            ]

        return {
            "metadata": {
                "initial_urn": self._repo.get_initial_urn(),
                "urn_parsing_order": self._repo.get_urn_parsing_order(),
                "import_graph": self._repo.get_import_graph(),
                "filtered": self._repo.is_filtered(),
            },
            "requirements": requirements,
            "svcs": svcs,
            "mvrs": mvrs,
            "annotations": {
                "implementations": impl_annotations,
                "tests": test_annotations,
            },
            "test_results": test_results,
        }

    def _resolve_ids(self, raw_ids, default_urn, lookup_dict, label) -> set:
        resolved = set()
        if not raw_ids:
            return resolved
        for raw_id in raw_ids:
            uid = UrnId.assure_urn_id(urn=default_urn, id=raw_id)
            if uid not in lookup_dict:
                logger.warning(f"{label} '{raw_id}' (resolved to '{uid}') not found in dataset")
            else:
                resolved.add(uid)
        return resolved
