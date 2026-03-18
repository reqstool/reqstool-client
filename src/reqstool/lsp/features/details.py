# Copyright © LFV

from __future__ import annotations

from reqstool.lsp.project_state import ProjectState


def get_requirement_details(raw_id: str, project: ProjectState) -> dict | None:
    req = project.get_requirement(raw_id)
    if req is None:
        return None
    svcs = project.get_svcs_for_req(raw_id)
    impls = project.get_impl_annotations_for_req(raw_id)
    references = [str(ref_id) for rd in (req.references or []) for ref_id in rd.requirement_ids]
    return {
        "type": "requirement",
        "id": req.id.id,
        "urn": str(req.id),
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
                "urn": str(s.id),
                "title": s.title,
                "verification": s.verification.value,
            }
            for s in svcs
        ],
    }


def get_svc_details(raw_id: str, project: ProjectState) -> dict | None:
    svc = project.get_svc(raw_id)
    if svc is None:
        return None
    mvrs = project.get_mvrs_for_svc(raw_id)
    test_annotations = project.get_test_annotations_for_svc(raw_id)
    test_results = project.get_test_results_for_svc(raw_id)
    return {
        "type": "svc",
        "id": svc.id.id,
        "urn": str(svc.id),
        "title": svc.title,
        "description": svc.description or "",
        "verification": svc.verification.value,
        "instructions": svc.instructions or "",
        "revision": str(svc.revision),
        "lifecycle": {
            "state": svc.lifecycle.state.value,
            "reason": svc.lifecycle.reason or "",
        },
        "requirement_ids": [{"id": r.id, "urn": str(r)} for r in svc.requirement_ids],
        "test_annotations": [{"element_kind": a.element_kind, "fqn": a.fully_qualified_name} for a in test_annotations],
        "test_results": [{"fqn": t.fully_qualified_name, "status": t.status.value} for t in test_results],
        "mvrs": [
            {
                "id": m.id.id,
                "urn": str(m.id),
                "passed": m.passed,
                "comment": m.comment or "",
            }
            for m in mvrs
        ],
    }


def get_mvr_details(raw_id: str, project: ProjectState) -> dict | None:
    mvr = project.get_mvr(raw_id)
    if mvr is None:
        return None
    return {
        "type": "mvr",
        "id": mvr.id.id,
        "urn": str(mvr.id),
        "passed": mvr.passed,
        "comment": mvr.comment or "",
        "svc_ids": [{"id": s.id, "urn": str(s)} for s in mvr.svc_ids],
    }
