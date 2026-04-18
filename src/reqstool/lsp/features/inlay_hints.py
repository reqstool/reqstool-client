# Copyright © LFV


from lsprotocol import types

from reqstool.lsp.annotation_parser import find_all_annotations
from reqstool.lsp.project_state import ProjectState


def handle_inlay_hints(
    uri: str,
    range_: types.Range,
    text: str,
    language_id: str,
    project: ProjectState | None,
) -> list[types.InlayHint]:
    if project is None or not project.ready:
        return []

    annotations = find_all_annotations(text, language_id)
    result: list[types.InlayHint] = []

    for match in annotations:
        if match.line < range_.start.line or match.line > range_.end.line:
            continue

        if match.kind == "Requirements":
            item = project.get_requirement(match.raw_id)
            title = item.title if item is not None else None
        else:
            item = project.get_svc(match.raw_id)
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
