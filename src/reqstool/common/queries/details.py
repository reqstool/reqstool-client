# Copyright © LFV

from __future__ import annotations

from reqstool.common.models.urn_id import UrnId
from reqstool.storage.requirements_repository import RequirementsRepository


def _svc_test_summary(svc_urn_id: UrnId, repo: RequirementsRepository) -> dict:
    test_results = repo.get_test_results_for_svc(svc_urn_id)
    return {
        "passed": sum(1 for t in test_results if t.status.value == "passed"),
        "failed": sum(1 for t in test_results if t.status.value == "failed"),
        "skipped": sum(1 for t in test_results if t.status.value == "skipped"),
        "missing": sum(1 for t in test_results if t.status.value == "missing"),
    }


def get_requirement_details(
    raw_id: str,
    repo: RequirementsRepository,
    urn_source_paths: dict[str, dict[str, str]] | None = None,
) -> dict | None:
    initial_urn = repo.get_initial_urn()
    urn_id = UrnId.assure_urn_id(initial_urn, raw_id)
    all_reqs = repo.get_all_requirements()
    req = all_reqs.get(urn_id)
    if req is None:
        return None

    svc_urn_ids = repo.get_svcs_for_req(req.id)
    all_svcs = repo.get_all_svcs()
    svcs = [all_svcs[uid] for uid in svc_urn_ids if uid in all_svcs]

    impls = repo.get_annotations_impls_for_req(req.id)
    references = [str(ref_id) for rd in (req.references or []) for ref_id in rd.requirement_ids]

    paths = urn_source_paths or {}
    return {
        "type": "requirement",
        "id": req.id.id,
        "urn": req.id.urn,
        "title": req.title,
        "significance": req.significance.value,
        "description": req.description,
        "rationale": req.rationale or "",
        "revision": str(req.revision),
        "lifecycle": {
            "state": req.lifecycle.state.value,
            "reason": req.lifecycle.reason or "",
        },
        "categories": [c.value for c in req.categories],
        "implementation": req.implementation.value,
        "references": references,
        "implementations": [{"element_kind": a.element_kind, "fqn": a.fully_qualified_name} for a in impls],
        "svcs": [
            {
                "id": s.id.id,
                "urn": s.id.urn,
                "title": s.title,
                "verification": s.verification.value,
                "lifecycle_state": s.lifecycle.state.value,
                "test_summary": _svc_test_summary(s.id, repo),
            }
            for s in svcs
        ],
        "location": repo.get_urn_location(req.id.urn),
        "source_paths": paths.get(req.id.urn, {}),
    }


def get_svc_details(
    raw_id: str,
    repo: RequirementsRepository,
    urn_source_paths: dict[str, dict[str, str]] | None = None,
) -> dict | None:
    initial_urn = repo.get_initial_urn()
    urn_id = UrnId.assure_urn_id(initial_urn, raw_id)
    all_svcs = repo.get_all_svcs()
    svc = all_svcs.get(urn_id)
    if svc is None:
        return None

    mvr_urn_ids = repo.get_mvrs_for_svc(svc.id)
    all_mvrs = repo.get_all_mvrs()
    mvrs = [all_mvrs[uid] for uid in mvr_urn_ids if uid in all_mvrs]

    test_annotations = repo.get_annotations_tests_for_svc(svc.id)
    test_results = repo.get_test_results_for_svc(svc.id)

    all_reqs = repo.get_all_requirements()

    paths = urn_source_paths or {}
    return {
        "type": "svc",
        "id": svc.id.id,
        "urn": svc.id.urn,
        "title": svc.title,
        "description": svc.description or "",
        "verification": svc.verification.value,
        "instructions": svc.instructions or "",
        "revision": str(svc.revision),
        "lifecycle": {
            "state": svc.lifecycle.state.value,
            "reason": svc.lifecycle.reason or "",
        },
        "requirement_ids": [
            {
                "id": r.id,
                "urn": r.urn,
                "title": all_reqs[r].title if r in all_reqs else "",
                "lifecycle_state": all_reqs[r].lifecycle.state.value if r in all_reqs else "",
            }
            for r in svc.requirement_ids
        ],
        "test_annotations": [{"element_kind": a.element_kind, "fqn": a.fully_qualified_name} for a in test_annotations],
        "test_results": [{"fqn": t.fully_qualified_name, "status": t.status.value} for t in test_results],
        "test_summary": {
            "passed": sum(1 for t in test_results if t.status.value == "passed"),
            "failed": sum(1 for t in test_results if t.status.value == "failed"),
            "skipped": sum(1 for t in test_results if t.status.value == "skipped"),
            "missing": sum(1 for t in test_results if t.status.value == "missing"),
        },
        "mvrs": [
            {
                "id": m.id.id,
                "urn": m.id.urn,
                "passed": m.passed,
                "comment": m.comment or "",
            }
            for m in mvrs
        ],
        "location": repo.get_urn_location(svc.id.urn),
        "source_paths": paths.get(svc.id.urn, {}),
    }


def get_mvr_details(
    raw_id: str,
    repo: RequirementsRepository,
    urn_source_paths: dict[str, dict[str, str]] | None = None,
) -> dict | None:
    initial_urn = repo.get_initial_urn()
    urn_id = UrnId.assure_urn_id(initial_urn, raw_id)
    all_mvrs = repo.get_all_mvrs()
    mvr = all_mvrs.get(urn_id)
    if mvr is None:
        return None

    paths = urn_source_paths or {}
    return {
        "type": "mvr",
        "id": mvr.id.id,
        "urn": mvr.id.urn,
        "passed": mvr.passed,
        "comment": mvr.comment or "",
        "svc_ids": [{"id": s.id, "urn": s.urn} for s in mvr.svc_ids],
        "location": repo.get_urn_location(mvr.id.urn),
        "source_paths": paths.get(mvr.id.urn, {}),
    }
