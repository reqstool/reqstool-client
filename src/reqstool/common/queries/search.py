# Copyright © LFV

from reqstool.common.models.urn_id import UrnId
from reqstool.services.statistics_service import compute_requirement_status
from reqstool.storage.requirements_repository import RequirementsRepository
from reqstool.storage.search_index import KINDS

MAX_LIMIT = 100


def search_project(
    repo: RequirementsRepository,
    query: str,
    kinds: list[str] | None = None,
    urn: str | None = None,
    lifecycle_state: str | None = None,
    limit: int = 20,
) -> dict:
    """Ranked full-text search. Requirement hits carry the verdict from the shared status computation."""
    unknown = sorted(set(kinds or []) - set(KINDS))
    if unknown:
        raise ValueError(f"Unknown kind(s) {unknown}. Valid: {list(KINDS)}")
    limit = max(1, min(limit, MAX_LIMIT))

    hits, ranked = repo.search(query, kinds=kinds, urn=urn, lifecycle_state=lifecycle_state, limit=limit)

    reqs = repo.get_all_requirements() if any(h.kind == "requirement" for h in hits) else {}
    results = []
    for h in hits:
        entry = {"kind": h.kind, "id": h.id, "urn": h.urn, "snippet": h.snippet}
        urn_id = UrnId(urn=h.urn, id=h.id)
        if h.kind == "requirement":
            req = reqs[urn_id]
            entry["title"] = req.title
            entry["lifecycle_state"] = req.lifecycle.state.value
            entry["completed"] = compute_requirement_status(req, repo).completed
        elif h.kind == "svc":
            svc = repo.get_svc(urn_id)
            entry["title"] = svc.title
            entry["lifecycle_state"] = svc.lifecycle.state.value
        results.append(entry)

    out = {"query": query, "results": results}
    if not ranked:
        out["note"] = "FTS5 is unavailable in this Python build; results are unranked substring matches."
    return out
