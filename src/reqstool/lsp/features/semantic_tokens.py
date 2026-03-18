# Copyright © LFV

from __future__ import annotations

from lsprotocol import types

from reqstool.common.models.lifecycle import LIFECYCLESTATE
from reqstool.lsp.annotation_parser import find_all_annotations
from reqstool.lsp.project_state import ProjectState

TOKEN_TYPES = ["reqstoolDraft", "reqstoolValid", "reqstoolDeprecated", "reqstoolObsolete"]
_STATE_TO_IDX = {
    LIFECYCLESTATE.DRAFT: 0,
    LIFECYCLESTATE.EFFECTIVE: 1,
    LIFECYCLESTATE.DEPRECATED: 2,
    LIFECYCLESTATE.OBSOLETE: 3,
}

SEMANTIC_TOKENS_OPTIONS = types.SemanticTokensOptions(
    legend=types.SemanticTokensLegend(token_types=TOKEN_TYPES, token_modifiers=[]),
    full=True,
)


def _encode_tokens(tokens: list[tuple[int, int, int, int]]) -> list[int]:
    """Encode (line, start_col, length, type_idx) tuples into LSP delta-compressed integers."""
    data: list[int] = []
    prev_line, prev_start = 0, 0
    for line, start, length, type_idx in sorted(tokens):
        delta_line = line - prev_line
        delta_start = start - prev_start if delta_line == 0 else start
        data.extend([delta_line, delta_start, length, type_idx, 0])
        prev_line, prev_start = line, start
    return data


def handle_semantic_tokens(
    uri: str,
    text: str,
    language_id: str,
    project: ProjectState | None,
) -> types.SemanticTokens:
    if project is None or not project.ready:
        return types.SemanticTokens(data=[])

    annotations = find_all_annotations(text, language_id)
    tokens: list[tuple[int, int, int, int]] = []

    for match in annotations:
        if match.kind == "Requirements":
            item = project.get_requirement(match.raw_id)
            state = item.lifecycle.state if item is not None else LIFECYCLESTATE.EFFECTIVE
        else:
            item = project.get_svc(match.raw_id)
            state = item.lifecycle.state if item is not None else LIFECYCLESTATE.EFFECTIVE

        type_idx = _STATE_TO_IDX.get(state, 0)
        length = match.end_col - match.start_col
        tokens.append((match.line, match.start_col, length, type_idx))

    return types.SemanticTokens(data=_encode_tokens(tokens))
