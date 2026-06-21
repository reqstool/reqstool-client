# Copyright © LFV


from reqstool.common.models.urn_id import UrnId
from reqstool.models.requirements import IMPLEMENTATION, NON_CODE_IMPLEMENTATIONS
from reqstool.services.statistics_service import EXPECTS_AUTOMATED_TESTS
from reqstool.storage.requirements_repository import RequirementsRepository


def _compute_meets(req, repo: RequirementsRepository, svc_urn_ids: list, all_passing: bool) -> bool:
    """Return whether a requirement is considered met by this lightweight check.

    For IN_CODE: requires at least one @Requirements annotation, all automated tests
    passing, and no failing MVRs.
    For non-code types: requires at least one SVC, all automated tests passing, and
    no failing MVRs.
    """
    if not svc_urn_ids:
        return False
    if req.implementation == IMPLEMENTATION.IN_CODE:
        if not (len(repo.get_annotations_impls_for_req(req.id)) > 0 and all_passing):
            return False
    elif req.implementation in NON_CODE_IMPLEMENTATIONS:
        if not all_passing:
            return False
    else:
        raise ValueError(f"Unhandled IMPLEMENTATION value: {req.implementation}")
    # Check MVR results using only the effective (latest) verdict per SVC
    for svc_uid in svc_urn_ids:
        effective = repo.get_effective_mvr_for_svc(svc_uid)
        if effective is not None and not effective.passed:
            return False
    return True


def _build_automated_test_summary(svc_urn_ids: list, repo: RequirementsRepository) -> tuple[dict, bool]:
    """Build an automated-test summary across the given SVCs and whether they all pass.

    An SVC whose verification type expects automated tests but has zero recorded test
    executions counts as missing. SVCs verified by other means (e.g. manual test) are only
    counted if they happen to have automated test results attached; their absence is not a
    gap here since they are verified via MVRs instead (checked separately by the caller).
    A skipped test also means the requirement is not (yet) met.
    """
    test_summary = {"passed": 0, "failed": 0, "skipped": 0, "missing": 0}
    all_svcs = repo.get_all_svcs()
    for svc_uid in svc_urn_ids:
        svc = all_svcs.get(svc_uid)
        results = repo.get_test_results_for_svc(svc_uid)
        if not results:
            if svc is not None and svc.verification in EXPECTS_AUTOMATED_TESTS:
                test_summary["missing"] += 1
            continue
        for t in results:
            key = t.status.value
            if key in test_summary:
                test_summary[key] += 1
    all_passing = test_summary["failed"] == 0 and test_summary["missing"] == 0 and test_summary["skipped"] == 0
    return test_summary, all_passing


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

    all_mvrs = repo.get_all_mvrs()
    mvr_urn_ids = repo.get_mvrs_for_svc(svc.id)
    mvrs = [all_mvrs[uid] for uid in mvr_urn_ids if uid in all_mvrs]
    superseded_ids = {m.id for m in repo.get_superseded_mvrs_for_svc(svc.id)}

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
                "date": m.date.isoformat() if m.date is not None else "",
                "comment": m.comment or "",
                "superseded": m.id in superseded_ids,
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
        "date": mvr.date.isoformat() if mvr.date is not None else "",
        "comment": mvr.comment or "",
        "svc_ids": [{"id": s.id, "urn": s.urn} for s in mvr.svc_ids],
        "location": repo.get_urn_location(mvr.id.urn),
        "source_paths": paths.get(mvr.id.urn, {}),
    }


def get_urn_details(
    urn: str,
    repo: RequirementsRepository,
    urn_source_paths: dict[str, dict[str, str]] | None = None,
) -> dict | None:
    info = repo.get_urn_info(urn)
    if info is None:
        return None
    reqs = repo.get_all_requirements(urn=urn)
    svcs = repo.get_all_svcs(urn=urn)
    mvrs = repo.get_all_mvrs(urn=urn)
    impl_anns = repo.get_annotations_impls(urn=urn)
    test_anns = repo.get_annotations_tests(urn=urn)
    paths = urn_source_paths or {}
    return {
        **info,
        "file_paths": paths.get(urn, {}),
        "counts": {
            "requirements": len(reqs),
            "svcs": len(svcs),
            "mvrs": len(mvrs),
            "impl_annotations": sum(len(v) for v in impl_anns.values()),
            "test_annotations": sum(len(v) for v in test_anns.values()),
        },
    }


def get_requirement_status(raw_id: str, repo: RequirementsRepository) -> dict | None:
    """Lightweight status check — avoids the full detail lookup."""
    initial_urn = repo.get_initial_urn()
    urn_id = UrnId.assure_urn_id(initial_urn, raw_id)
    req = repo.get_all_requirements().get(urn_id)
    if req is None:
        return None

    svc_urn_ids = repo.get_svcs_for_req(req.id)
    test_summary, all_passing = _build_automated_test_summary(svc_urn_ids, repo)
    return {
        "id": req.id.id,
        "lifecycle_state": req.lifecycle.state.value,
        "implementation": req.implementation.value,
        "test_summary": test_summary,
        "meets_requirements": _compute_meets(req, repo, svc_urn_ids, all_passing),
    }


def get_requirements_status_all(repo: RequirementsRepository, urn: str | None = None) -> list[dict]:
    """Batch status for all requirements. Optionally scoped to a URN."""
    reqs = repo.get_all_requirements(urn=urn)
    result = []
    for req in reqs.values():
        svc_urn_ids = repo.get_svcs_for_req(req.id)
        test_summary, all_passing = _build_automated_test_summary(svc_urn_ids, repo)
        result.append(
            {
                "id": req.id.id,
                "urn": req.id.urn,
                "lifecycle_state": req.lifecycle.state.value,
                "implementation": req.implementation.value,
                "test_summary": test_summary,
                "meets_requirements": _compute_meets(req, repo, svc_urn_ids, all_passing),
            }
        )
    return result
