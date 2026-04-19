# Copyright © LFV


import re
from dataclasses import dataclass


@dataclass(frozen=True)
class AnnotationMatch:
    kind: str  # "Requirements" or "SVCs"
    raw_id: str  # e.g. "REQ_010" or "ms-001:REQ_010"
    line: int  # 0-based line number
    start_col: int  # column of ID start
    end_col: int  # column of ID end (exclusive)


# Java/Python: @Requirements("REQ_010", "REQ_011") or @SVCs("SVC_010")
SOURCE_ANNOTATION_RE = re.compile(r"@(Requirements|SVCs)\s*\(")
QUOTED_ID_RE = re.compile(r'"([^"]*)"')

# TypeScript/JavaScript JSDoc: /** @Requirements REQ_010, REQ_011 */
JSDOC_TAG_RE = re.compile(r"@(Requirements|SVCs)\s+(.+)")
BARE_ID_RE = re.compile(r"[\w:./-]+")

SOURCE_LANGUAGES = {"python", "java"}
JSDOC_LANGUAGES = {"javascript", "typescript", "javascriptreact", "typescriptreact"}


def find_all_annotations(text: str, language_id: str) -> list[AnnotationMatch]:
    lines = text.splitlines()
    if language_id in SOURCE_LANGUAGES:
        return _find_source_annotations(lines)
    elif language_id in JSDOC_LANGUAGES:
        return _find_jsdoc_annotations(lines)
    return []


def annotation_at_position(text: str, line: int, character: int, language_id: str) -> AnnotationMatch | None:
    for match in find_all_annotations(text, language_id):
        if match.line == line and match.start_col <= character < match.end_col:
            return match
    return None


def is_inside_annotation(line_text: str, character: int, language_id: str) -> str | None:
    if language_id in SOURCE_LANGUAGES:
        return _is_inside_source_annotation(line_text, character)
    elif language_id in JSDOC_LANGUAGES:
        return _is_inside_jsdoc_annotation(line_text, character)
    return None


def _find_source_annotations(lines: list[str]) -> list[AnnotationMatch]:
    results: list[AnnotationMatch] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        for m in SOURCE_ANNOTATION_RE.finditer(line):
            kind = m.group(1)
            # Collect the full argument text, handling multi-line parens
            paren_start = m.end() - 1  # position of '('
            arg_text, arg_lines = _collect_paren_content(lines, i, paren_start)
            # Find all quoted IDs within the argument text
            offset_in_first_line = m.end()
            _extract_quoted_ids(results, kind, arg_text, arg_lines, lines, i, offset_in_first_line)
        i += 1
    return results


def _collect_paren_content(lines: list[str], start_line: int, paren_col: int) -> tuple[str, list[tuple[int, int]]]:
    """Collect text between parens, possibly spanning multiple lines.

    Returns (full_text_between_parens, list_of_(line_idx, line_start_offset)).
    """
    depth = 0
    parts: list[str] = []
    # Track which line and offset each character in the combined text came from
    line_offsets: list[tuple[int, int]] = []  # (line_index, start_col_in_combined_text)

    combined_len = 0
    for line_idx in range(start_line, len(lines)):
        line = lines[line_idx]
        start_col = paren_col if line_idx == start_line else 0
        for col in range(start_col, len(line)):
            ch = line[col]
            if ch == "(":
                depth += 1
                if depth == 1:
                    line_offsets.append((line_idx, combined_len))
                    continue  # skip the opening paren
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return "".join(parts), line_offsets
            if depth >= 1:
                if not parts or line_offsets[-1][0] != line_idx:
                    line_offsets.append((line_idx, combined_len))
                parts.append(ch)
                combined_len += 1
        if depth >= 1:
            parts.append("\n")
            combined_len += 1
    return "".join(parts), line_offsets


def _extract_quoted_ids(
    results: list[AnnotationMatch],
    kind: str,
    arg_text: str,
    arg_lines: list[tuple[int, int]],
    lines: list[str],
    annotation_line: int,
    offset_in_first_line: int,
) -> None:
    for id_match in QUOTED_ID_RE.finditer(arg_text):
        raw_id = id_match.group(1)
        # Map position in arg_text back to source line/col
        id_start_in_arg = id_match.start(1)
        id_end_in_arg = id_match.end(1)
        src_line, src_col_start = _map_offset_to_source(arg_lines, lines, annotation_line, id_start_in_arg)
        _, src_col_end = _map_offset_to_source(arg_lines, lines, annotation_line, id_end_in_arg)
        results.append(
            AnnotationMatch(
                kind=kind,
                raw_id=raw_id,
                line=src_line,
                start_col=src_col_start,
                end_col=src_col_end,
            )
        )


def _map_offset_to_source(
    arg_lines: list[tuple[int, int]],
    lines: list[str],
    annotation_line: int,
    offset: int,
) -> tuple[int, int]:
    """Map an offset within the combined arg_text back to a (line, col) in the source."""
    # Find which line segment this offset falls into
    target_line = annotation_line
    target_start_offset = 0
    for line_idx, start_offset in arg_lines:
        if start_offset <= offset:
            target_line = line_idx
            target_start_offset = start_offset
        else:
            break

    # Calculate column: find where in the actual source line this offset maps
    chars_into_segment = offset - target_start_offset
    line_text = lines[target_line]

    # Find the start of this segment in the actual line
    if target_line == annotation_line:
        # First line: content starts after @Kind(
        segment_start_col = line_text.index("(", line_text.index("@")) + 1
    else:
        segment_start_col = 0

    # Walk through the line to find the actual column, accounting for the quote char
    col = segment_start_col
    counted = 0
    while col < len(line_text) and counted < chars_into_segment:
        col += 1
        counted += 1

    return target_line, col


def _find_jsdoc_annotations(lines: list[str]) -> list[AnnotationMatch]:
    results: list[AnnotationMatch] = []
    for line_idx, line in enumerate(lines):
        for m in JSDOC_TAG_RE.finditer(line):
            kind = m.group(1)
            ids_text = m.group(2)
            ids_start = m.start(2)
            # Strip trailing */ or whitespace
            ids_text = re.sub(r"\s*\*/\s*$", "", ids_text)
            for id_match in BARE_ID_RE.finditer(ids_text):
                raw_id = id_match.group(0)
                start_col = ids_start + id_match.start()
                end_col = ids_start + id_match.end()
                results.append(
                    AnnotationMatch(
                        kind=kind,
                        raw_id=raw_id,
                        line=line_idx,
                        start_col=start_col,
                        end_col=end_col,
                    )
                )
    return results


def _is_inside_source_annotation(line_text: str, character: int) -> str | None:
    for m in SOURCE_ANNOTATION_RE.finditer(line_text):
        kind = m.group(1)
        paren_pos = m.end() - 1
        # Find closing paren on same line
        depth = 0
        for col in range(paren_pos, len(line_text)):
            if line_text[col] == "(":
                depth += 1
            elif line_text[col] == ")":
                depth -= 1
                if depth == 0:
                    if paren_pos < character <= col:
                        return kind
                    break
        else:
            # No closing paren found on this line — cursor might still be inside
            if character > paren_pos:
                return kind
    return None


def _is_inside_jsdoc_annotation(line_text: str, character: int) -> str | None:
    for m in JSDOC_TAG_RE.finditer(line_text):
        kind = m.group(1)
        line_end = len(line_text.rstrip())
        if m.start(2) <= character <= line_end:
            return kind
    return None
