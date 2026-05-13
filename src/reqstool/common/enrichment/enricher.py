# Copyright © LFV

import re
from dataclasses import dataclass
from typing import Optional

from reqstool.models.mvrs import MVRData
from reqstool.models.requirements import RequirementData
from reqstool.models.svcs import SVCData

_UPPERCASE_VALUES = frozenset({"shall", "should", "may"})


@dataclass(frozen=True)
class EnrichmentConfig:
    trigger: str  # 'colon-header' | 'inline'
    title_only: bool  # True → skip block injection
    drop_stubs: bool
    skip_code_spans: bool


BUILT_IN_PRESETS: dict[str, EnrichmentConfig] = {
    "openspec:spec": EnrichmentConfig("colon-header", False, True, True),
    "openspec:delta-spec": EnrichmentConfig("colon-header", False, True, True),
    "openspec:design": EnrichmentConfig("inline", True, False, True),
    "openspec:proposal": EnrichmentConfig("inline", True, False, True),
    "openspec:tasks": EnrichmentConfig("inline", True, False, True),
}


@dataclass
class _EntityInfo:
    inline_text: str
    block_lines: list


def _format_value(value: str) -> str:
    if value == "N/A":
        return "N/A"
    if value in _UPPERCASE_VALUES:
        return value.upper()
    return value.replace("-", " ").title()


def _block_field(label: str, value: str) -> list:
    lines = value.splitlines()
    if not lines:
        return []
    result = [f"> **{label}**: {lines[0]}"]
    for line in lines[1:]:
        result.append(f"> {line}" if line.strip() else ">")
    return result


def _req_block_lines(req: RequirementData) -> list:
    lines = []
    lines.append(f"> **Significance**: {_format_value(req.significance.value)}")
    if req.description:
        lines.extend(_block_field("Description", req.description))
    if req.rationale:
        lines.extend(_block_field("Rationale", req.rationale))
    if req.categories:
        cats = ", ".join(sorted(_format_value(c.value) for c in req.categories))
        lines.append(f"> **Categories**: {cats}")
    if req.references:
        refs = []
        for ref_data in req.references:
            for uid in sorted(ref_data.requirement_ids, key=str):
                refs.append(uid.id)
        if refs:
            lines.append(f"> **References**: {', '.join(refs)}")
    lines.append(f"> **Implementation**: {_format_value(req.implementation.value)}")
    lines.append(f"> **Revision**: {req.revision}")
    lines.append(f"> **Lifecycle**: {_format_value(req.lifecycle.state.value)}")
    return lines


def _svc_block_lines(svc: SVCData) -> list:
    lines = []
    if svc.description:
        lines.extend(_block_field("Description", svc.description))
    lines.append(f"> **Verification**: {_format_value(svc.verification.value)}")
    if svc.instructions:
        lines.extend(_block_field("Instructions", svc.instructions))
    if svc.requirement_ids:
        reqs = ", ".join(uid.id for uid in svc.requirement_ids)
        lines.append(f"> **Requirements**: {reqs}")
    lines.append(f"> **Revision**: {svc.revision}")
    lines.append(f"> **Lifecycle**: {_format_value(svc.lifecycle.state.value)}")
    return lines


def _mvr_block_lines(mvr: MVRData) -> list:
    lines = []
    if mvr.comment:
        lines.extend(_block_field("Comment", mvr.comment))
    if mvr.svc_ids:
        svcs = ", ".join(uid.id for uid in mvr.svc_ids)
        lines.append(f"> **SVCs**: {svcs}")
    return lines


def _build_lookup(
    requirements: dict,
    svcs: dict,
    mvrs: dict,
    config: EnrichmentConfig,
) -> dict:
    lookup: dict[str, _EntityInfo] = {}
    for urn_id, req in requirements.items():
        block = [] if config.title_only else _req_block_lines(req)
        lookup[urn_id.id] = _EntityInfo(inline_text=req.title, block_lines=block)
    for urn_id, svc in svcs.items():
        block = [] if config.title_only else _svc_block_lines(svc)
        lookup[urn_id.id] = _EntityInfo(inline_text=svc.title, block_lines=block)
    for urn_id, mvr in mvrs.items():
        inline = "PASSED" if mvr.passed else "FAILED"
        block = [] if config.title_only else _mvr_block_lines(mvr)
        lookup[urn_id.id] = _EntityInfo(inline_text=inline, block_lines=block)
    return lookup


def _make_pattern(lookup: dict) -> re.Pattern:
    if not lookup:
        return re.compile(r"(?!)")
    sorted_ids = sorted(lookup.keys(), key=len, reverse=True)
    alternation = "|".join(re.escape(id_str) for id_str in sorted_ids)
    return re.compile(r"\b(?:" + alternation + r")\b")


def _in_backtick_span(line: str, pos: int) -> bool:
    in_span = False
    span_start = -1
    i = 0
    while i < len(line):
        if line[i] == "`":
            if not in_span:
                span_start = i + 1
                in_span = True
            else:
                if span_start <= pos < i:
                    return True
                in_span = False
        i += 1
    return False


def _is_stub(line: str, id_str: str) -> bool:
    return bool(
        re.match(
            r"^\s*The system SHALL (?:implement|pass)\s+" + re.escape(id_str) + r"\.?\s*$",
            line,
        )
    )


def enrich_text(  # noqa: C901
    text: str,
    requirements: dict,
    svcs: dict,
    mvrs: dict,
    config: EnrichmentConfig,
) -> str:
    lookup = _build_lookup(requirements, svcs, mvrs, config)
    if not lookup:
        return text
    pattern = _make_pattern(lookup)

    output = []
    in_fenced_block = False
    last_enriched_id: Optional[str] = None

    for line in text.splitlines(keepends=True):
        stripped = line.rstrip("\n\r")
        trailing = line[len(stripped):]  # noqa: E203

        # Fenced block state machine
        if stripped.strip().startswith("```") or stripped.strip().startswith("~~~"):
            in_fenced_block = not in_fenced_block
            output.append(line)
            last_enriched_id = None
            continue

        if in_fenced_block:
            output.append(line)
            continue

        if config.trigger == "colon-header":
            # Drop stub on the line immediately following an enriched header
            if last_enriched_id is not None:
                if _is_stub(stripped, last_enriched_id):
                    last_enriched_id = None
                    continue
                last_enriched_id = None

            matches = [m for m in pattern.finditer(stripped) if not _in_backtick_span(stripped, m.start())]
            if matches:
                last_match = matches[-1]
                id_str = last_match.group(0)
                before = stripped[: last_match.start()]  # noqa: E203
                after = stripped[last_match.end():].rstrip()
                if ":" in before and not after:
                    info = lookup[id_str]
                    output.append(stripped + f" — {info.inline_text}" + trailing)
                    for bl in info.block_lines:
                        output.append(bl + "  \n")  # trailing spaces = Markdown hard line break
                    last_enriched_id = id_str
                    continue

            output.append(line)

        else:  # inline
            matches = [m for m in pattern.finditer(stripped) if not _in_backtick_span(stripped, m.start())]
            if not matches:
                output.append(line)
                continue
            result = stripped
            for m in reversed(matches):
                id_str = m.group(0)
                info = lookup[id_str]
                result = result[: m.end()] + f" — {info.inline_text}" + result[m.end():]  # noqa: E203
            output.append(result + trailing)

    return "".join(output)
