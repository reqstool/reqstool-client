# Copyright © LFV


from lsprotocol import types

from reqstool.lsp.annotation_parser import find_all_annotations
from reqstool.lsp.project_state import ProjectState
from reqstool.lsp.workspace_manager import WorkspaceManager


def handle_inlay_hints(
    uri: str,
    range_: types.Range,
    text: str,
    language_id: str,
    project: ProjectState | None,
    workspace_manager: WorkspaceManager | None = None,
) -> list[types.InlayHint]:
    if project is None or not project.ready:
        return []

    annotations = find_all_annotations(text, language_id)
    result: list[types.InlayHint] = []

    for match in annotations:
        if match.line < range_.start.line or match.line > range_.end.line:
            continue

        p = workspace_manager.resolve_project(match.raw_id, project) if workspace_manager else project
        if match.kind == "Requirements":
            item = p.get_requirement(match.raw_id)
            title = item.title if item is not None else None
        else:
            item = p.get_svc(match.raw_id)
            title = item.title if item is not None else None

        if title is None:
            continue

        result.append(
            types.InlayHint(
                position=types.Position(line=match.line, character=match.end_col),
                label=f" \u2190 {title}",
                kind=types.InlayHintKind.Type,
                padding_left=True,
            )
        )

    return result
