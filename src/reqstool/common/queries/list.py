# Copyright © LFV


from reqstool.storage.requirements_repository import RequirementsRepository


def get_requirements_list(repo: RequirementsRepository) -> list[dict]:
    return [
        {
            "id": r.id.id,
            "title": r.title,
            "lifecycle_state": r.lifecycle.state.value,
        }
        for r in repo.get_all_requirements().values()
    ]


def get_svcs_list(repo: RequirementsRepository) -> list[dict]:
    return [
        {
            "id": s.id.id,
            "title": s.title,
            "lifecycle_state": s.lifecycle.state.value,
            "verification": s.verification.value,
        }
        for s in repo.get_all_svcs().values()
    ]


def get_mvrs_list(repo: RequirementsRepository) -> list[dict]:
    return [
        {
            "id": m.id.id,
            "passed": m.passed,
        }
        for m in repo.get_all_mvrs().values()
    ]


def get_list(repo: RequirementsRepository) -> dict:
    return {
        "requirements": get_requirements_list(repo),
        "svcs": get_svcs_list(repo),
        "mvrs": get_mvrs_list(repo),
    }
