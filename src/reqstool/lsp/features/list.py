# Copyright © LFV

from __future__ import annotations

from reqstool.lsp.project_state import ProjectState


def get_list(project: ProjectState) -> dict:
    reqs = project._repo.get_all_requirements() if project._repo else {}
    svcs = project._repo.get_all_svcs() if project._repo else {}
    mvrs = project._repo.get_all_mvrs() if project._repo else {}

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
