# Copyright © LFV


from reqstool.storage.requirements_repository import RequirementsRepository


def get_list(repo: RequirementsRepository) -> dict:
    reqs = repo.get_all_requirements()
    svcs = repo.get_all_svcs()
    mvrs = repo.get_all_mvrs()

    return {
        "requirements": [
            {
                "id": r.id.id,
                "title": r.title,
                "lifecycle_state": r.lifecycle.state.value,
            }
            for r in reqs.values()
        ],
        "svcs": [
            {
                "id": s.id.id,
                "title": s.title,
                "lifecycle_state": s.lifecycle.state.value,
                "verification": s.verification.value,
            }
            for s in svcs.values()
        ],
        "mvrs": [
            {
                "id": m.id.id,
                "passed": m.passed,
            }
            for m in mvrs.values()
        ],
    }
