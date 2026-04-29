# Copyright © LFV


from reqstool.storage.requirements_repository import RequirementsRepository


def get_requirements_list(
    repo: RequirementsRepository, urn: str | None = None, lifecycle_state: str | None = None
) -> list[dict]:
    return [
        {
            "id": r.id.id,
            "title": r.title,
            "lifecycle_state": r.lifecycle.state.value,
        }
        for r in repo.get_all_requirements(urn=urn, lifecycle_state=lifecycle_state).values()
    ]


def get_svcs_list(repo: RequirementsRepository, urn: str | None = None, lifecycle_state: str | None = None) -> list[dict]:
    return [
        {
            "id": s.id.id,
            "title": s.title,
            "lifecycle_state": s.lifecycle.state.value,
            "verification": s.verification.value,
        }
        for s in repo.get_all_svcs(urn=urn, lifecycle_state=lifecycle_state).values()
    ]


def get_mvrs_list(repo: RequirementsRepository, urn: str | None = None, passed: bool | None = None) -> list[dict]:
    return [
        {
            "id": m.id.id,
            "passed": m.passed,
        }
        for m in repo.get_all_mvrs(urn=urn, passed=passed).values()
    ]


def get_list(repo: RequirementsRepository, urn: str | None = None) -> dict:
    return {
        "requirements": get_requirements_list(repo, urn=urn),
        "svcs": get_svcs_list(repo, urn=urn),
        "mvrs": get_mvrs_list(repo, urn=urn),
    }


def get_urns_list(repo: RequirementsRepository, urn_source_paths: dict[str, dict[str, str]] | None = None) -> list[dict]:
    paths = urn_source_paths or {}
    result = []
    for urn in repo.get_urn_parsing_order():
        info = repo.get_urn_info(urn)
        if info:
            info["file_paths"] = paths.get(urn, {})
            result.append(info)
    return result
