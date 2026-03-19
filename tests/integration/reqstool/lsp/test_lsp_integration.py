from __future__ import annotations

import os
from pathlib import Path

import pytest
from lsprotocol import types

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="module")]


def _find_position_in_file(file_path: str, search_text: str) -> types.Position:
    """Find the line and character position of search_text in a file."""
    with open(file_path) as f:
        for line_no, line in enumerate(f):
            col = line.find(search_text)
            if col != -1:
                return types.Position(line=line_no, character=col)
    raise ValueError(f"{search_text!r} not found in {file_path}")


def _open_document(client, file_path: str, language_id: str) -> str:
    """Send didOpen for a file and return its URI."""
    uri = Path(file_path).as_uri()
    with open(file_path) as f:
        text = f.read()
    client.text_document_did_open(
        types.DidOpenTextDocumentParams(
            text_document=types.TextDocumentItem(
                uri=uri,
                language_id=language_id,
                version=1,
                text=text,
            )
        )
    )
    return uri


# ---------------------------------------------------------------------------
# 1. Initialize capabilities
# ---------------------------------------------------------------------------


async def test_initialize_capabilities(lsp_client):
    """Server responds with hover, completion, definition, documentSymbol providers."""
    client, result = lsp_client
    caps = result.capabilities

    assert caps.hover_provider is not None
    assert caps.completion_provider is not None
    assert caps.definition_provider is not None
    assert caps.document_symbol_provider is not None


# ---------------------------------------------------------------------------
# 2 & 3. Source diagnostics
# ---------------------------------------------------------------------------


async def test_source_diagnostics_valid_ids(lsp_client, fixture_dir):
    """didOpen requirements_example.py -> no error diagnostics for known IDs."""
    client, _ = lsp_client
    src_path = os.path.join(fixture_dir, "src", "requirements_example.py")

    client.clear_diagnostics()
    uri = _open_document(client, src_path, "python")
    diagnostics = await client.wait_for_diagnostics(uri)

    errors = [d for d in diagnostics if d.severity == types.DiagnosticSeverity.Error]
    assert len(errors) == 0, f"Unexpected error diagnostics: {[e.message for e in errors]}"


async def test_source_diagnostics_deprecated(lsp_client, fixture_dir):
    """didOpen requirements_example.py -> warnings for deprecated/obsolete IDs."""
    client, _ = lsp_client
    src_path = os.path.join(fixture_dir, "src", "requirements_example.py")

    client.clear_diagnostics()
    uri = _open_document(client, src_path, "python")
    diagnostics = await client.wait_for_diagnostics(uri)

    warnings = [d for d in diagnostics if d.severity == types.DiagnosticSeverity.Warning]
    warning_messages = [w.message for w in warnings]

    assert any(
        "REQ_SKIPPED_TEST" in m and "deprecated" in m for m in warning_messages
    ), f"Expected deprecation warning for REQ_SKIPPED_TEST, got: {warning_messages}"
    assert any(
        "REQ_OBSOLETE" in m and "obsolete" in m for m in warning_messages
    ), f"Expected obsolete warning for REQ_OBSOLETE, got: {warning_messages}"


# ---------------------------------------------------------------------------
# 4 & 5. Hover
# ---------------------------------------------------------------------------


async def test_hover_requirement(lsp_client, fixture_dir):
    """Hover at REQ_PASS -> markdown with 'Greeting message', 'shall'."""
    client, _ = lsp_client
    src_path = os.path.join(fixture_dir, "src", "requirements_example.py")
    uri = _open_document(client, src_path, "python")

    pos = _find_position_in_file(src_path, "REQ_PASS")
    pos.character += 1  # inside the quoted ID string

    result = await client.text_document_hover_async(
        types.HoverParams(
            text_document=types.TextDocumentIdentifier(uri=uri),
            position=pos,
        )
    )

    assert result is not None, "Expected hover result for REQ_PASS"
    assert isinstance(result.contents, types.MarkupContent)
    assert "Greeting message" in result.contents.value
    assert "shall" in result.contents.value


async def test_hover_svc(lsp_client, fixture_dir):
    """Hover at SVC_010 in test_svcs.py -> markdown with 'automated-test'."""
    client, _ = lsp_client
    src_path = os.path.join(fixture_dir, "src", "test_svcs.py")
    uri = _open_document(client, src_path, "python")

    pos = _find_position_in_file(src_path, "SVC_010")
    pos.character += 1

    result = await client.text_document_hover_async(
        types.HoverParams(
            text_document=types.TextDocumentIdentifier(uri=uri),
            position=pos,
        )
    )

    assert result is not None, "Expected hover result for SVC_010"
    assert isinstance(result.contents, types.MarkupContent)
    assert "automated-test" in result.contents.value


# ---------------------------------------------------------------------------
# 6 & 7. Completion
# ---------------------------------------------------------------------------


async def test_completion_requirements(lsp_client, fixture_dir):
    """Inside @Requirements(" -> items include all 7 REQ IDs."""
    client, _ = lsp_client
    src_path = os.path.join(fixture_dir, "src", "requirements_example.py")
    uri = _open_document(client, src_path, "python")

    pos = _find_position_in_file(src_path, "REQ_PASS")
    pos.character += 1

    result = await client.text_document_completion_async(
        types.CompletionParams(
            text_document=types.TextDocumentIdentifier(uri=uri),
            position=pos,
        )
    )

    assert result is not None, "Expected completion result"
    labels = {item.label for item in result.items}
    expected_ids = {
        "REQ_PASS",
        "REQ_MANUAL_FAIL",
        "REQ_NOT_IMPLEMENTED",
        "REQ_FAILING_TEST",
        "REQ_MISSING_TEST",
    }
    assert expected_ids.issubset(labels), f"Missing REQ IDs in completion. Got: {labels}"
    assert "REQ_SKIPPED_TEST" not in labels, "Deprecated REQ should not appear in completion"
    assert "REQ_OBSOLETE" not in labels, "Obsolete REQ should not appear in completion"


async def test_completion_svcs(lsp_client, fixture_dir):
    """Inside @SVCs(" -> items include SVC_010 through SVC_070."""
    client, _ = lsp_client
    src_path = os.path.join(fixture_dir, "src", "test_svcs.py")
    uri = _open_document(client, src_path, "python")

    pos = _find_position_in_file(src_path, "SVC_010")
    pos.character += 1

    result = await client.text_document_completion_async(
        types.CompletionParams(
            text_document=types.TextDocumentIdentifier(uri=uri),
            position=pos,
        )
    )

    assert result is not None, "Expected completion result"
    labels = {item.label for item in result.items}
    expected_ids = {"SVC_010", "SVC_020", "SVC_021", "SVC_022", "SVC_030", "SVC_040", "SVC_060"}
    assert expected_ids.issubset(labels), f"Missing SVC IDs in completion. Got: {labels}"
    assert "SVC_050" not in labels, "Deprecated SVC should not appear in completion"
    assert "SVC_070" not in labels, "Obsolete SVC should not appear in completion"


# ---------------------------------------------------------------------------
# 8. Go-to-definition: source -> YAML
# ---------------------------------------------------------------------------


async def test_goto_definition_source_to_yaml(lsp_client, fixture_dir):
    """Definition at REQ_PASS in .py -> location in requirements.yml."""
    client, _ = lsp_client
    src_path = os.path.join(fixture_dir, "src", "requirements_example.py")
    uri = _open_document(client, src_path, "python")

    pos = _find_position_in_file(src_path, "REQ_PASS")
    pos.character += 1

    result = await client.text_document_definition_async(
        types.DefinitionParams(
            text_document=types.TextDocumentIdentifier(uri=uri),
            position=pos,
        )
    )

    assert result is not None and len(result) > 0, "Expected definition location"
    req_yml_path = os.path.join(fixture_dir, "requirements.yml")
    target_uris = [loc.uri for loc in result]
    assert any(req_yml_path in u for u in target_uris), f"Expected definition in requirements.yml, got: {target_uris}"


# ---------------------------------------------------------------------------
# 9 & 10. Document symbols
# ---------------------------------------------------------------------------


async def test_document_symbols_requirements(lsp_client, fixture_dir):
    """7 symbols for requirements.yml."""
    client, _ = lsp_client
    req_path = os.path.join(fixture_dir, "requirements.yml")
    uri = _open_document(client, req_path, "yaml")

    result = await client.text_document_document_symbol_async(
        types.DocumentSymbolParams(
            text_document=types.TextDocumentIdentifier(uri=uri),
        )
    )

    assert result is not None
    assert len(result) == 7, f"Expected 7 requirement symbols, got {len(result)}: {[s.name for s in result]}"


async def test_document_symbols_svcs(lsp_client, fixture_dir):
    """9 symbols for software_verification_cases.yml."""
    client, _ = lsp_client
    svc_path = os.path.join(fixture_dir, "software_verification_cases.yml")
    uri = _open_document(client, svc_path, "yaml")

    result = await client.text_document_document_symbol_async(
        types.DocumentSymbolParams(
            text_document=types.TextDocumentIdentifier(uri=uri),
        )
    )

    assert result is not None
    assert len(result) == 9, f"Expected 9 SVC symbols, got {len(result)}: {[s.name for s in result]}"


# ---------------------------------------------------------------------------
# 11. YAML hover — schema description
# ---------------------------------------------------------------------------


async def test_yaml_hover_schema(lsp_client, fixture_dir):
    """Hover on 'significance' key -> description from JSON schema."""
    client, _ = lsp_client
    req_path = os.path.join(fixture_dir, "requirements.yml")
    uri = _open_document(client, req_path, "yaml")

    pos = _find_position_in_file(req_path, "significance")

    result = await client.text_document_hover_async(
        types.HoverParams(
            text_document=types.TextDocumentIdentifier(uri=uri),
            position=pos,
        )
    )

    assert result is not None, "Expected hover result for significance field"
    assert isinstance(result.contents, types.MarkupContent)
    assert "significance" in result.contents.value.lower()


# ---------------------------------------------------------------------------
# 12. YAML completion — enum values
# ---------------------------------------------------------------------------


async def test_yaml_completion_enum(lsp_client, fixture_dir):
    """Completion at 'significance:' position -> 'shall', 'should', 'may'."""
    client, _ = lsp_client
    req_path = os.path.join(fixture_dir, "requirements.yml")
    uri = _open_document(client, req_path, "yaml")

    pos = _find_position_in_file(req_path, "significance: shall")
    pos.character += len("significance: ")

    result = await client.text_document_completion_async(
        types.CompletionParams(
            text_document=types.TextDocumentIdentifier(uri=uri),
            position=pos,
        )
    )

    assert result is not None, "Expected completion result for significance enum"
    labels = {item.label for item in result.items}
    assert {"shall", "should", "may"}.issubset(labels), f"Expected significance enum values, got: {labels}"


# ---------------------------------------------------------------------------
# 13. Go-to-definition: YAML -> YAML
# ---------------------------------------------------------------------------


async def test_goto_definition_yaml_to_yaml(lsp_client, fixture_dir):
    """Definition at REQ_PASS in requirements.yml -> SVC file,
    and SVC_021 in software_verification_cases.yml -> MVR file."""
    client, _ = lsp_client

    # --- REQ_PASS in requirements.yml → software_verification_cases.yml ---
    req_path = os.path.join(fixture_dir, "requirements.yml")
    req_uri = _open_document(client, req_path, "yaml")

    pos = _find_position_in_file(req_path, "id: REQ_PASS")

    result = await client.text_document_definition_async(
        types.DefinitionParams(
            text_document=types.TextDocumentIdentifier(uri=req_uri),
            position=pos,
        )
    )

    assert result is not None and len(result) > 0, "Expected definition locations for REQ_PASS in SVC file"
    svc_yml_path = os.path.join(fixture_dir, "software_verification_cases.yml")
    target_uris = [loc.uri for loc in result]
    assert any(
        svc_yml_path in u for u in target_uris
    ), f"Expected definition in software_verification_cases.yml, got: {target_uris}"

    # --- SVC_021 in software_verification_cases.yml → manual_verification_results.yml ---
    svc_path = os.path.join(fixture_dir, "software_verification_cases.yml")
    svc_uri = _open_document(client, svc_path, "yaml")

    pos = _find_position_in_file(svc_path, "id: SVC_021")

    result = await client.text_document_definition_async(
        types.DefinitionParams(
            text_document=types.TextDocumentIdentifier(uri=svc_uri),
            position=pos,
        )
    )

    assert result is not None and len(result) > 0, "Expected definition locations for SVC_021 in MVR file"
    mvr_yml_path = os.path.join(fixture_dir, "manual_verification_results.yml")
    target_uris = [loc.uri for loc in result]
    assert any(
        mvr_yml_path in u for u in target_uris
    ), f"Expected definition in manual_verification_results.yml, got: {target_uris}"
