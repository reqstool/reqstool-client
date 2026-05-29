# Copyright © LFV


import pytest

from reqstool.common.exceptions import EnvVarInterpolationError
from reqstool.common.utils import Utils


def test_check_ids_to_filter_plain_ids_get_urn_prepended():
    result = Utils.check_ids_to_filter(ids=["REQ_001", "REQ_002"], current_urn="ms-001")
    assert result == ["ms-001:REQ_001", "ms-001:REQ_002"]


def test_check_ids_to_filter_qualified_id_with_matching_urn_is_kept():
    result = Utils.check_ids_to_filter(ids=["ms-001:REQ_001"], current_urn="ms-001")
    assert result == ["ms-001:REQ_001"]


def test_check_ids_to_filter_qualified_id_with_foreign_urn_is_excluded():
    result = Utils.check_ids_to_filter(ids=["other-urn:REQ_001"], current_urn="ms-001")
    assert result == []


def test_check_ids_to_filter_mixed_ids():
    result = Utils.check_ids_to_filter(ids=["REQ_001", "ms-001:REQ_002", "other-urn:REQ_003"], current_urn="ms-001")
    assert "ms-001:REQ_001" in result
    assert "ms-001:REQ_002" in result
    assert "other-urn:REQ_003" not in result


def test_interpolate_env_vars_substitutes_braced_var(monkeypatch):
    monkeypatch.setenv("REQSTOOL_VERSION", "1.2.3")
    assert Utils.interpolate_env_vars("version: ${REQSTOOL_VERSION}") == "version: 1.2.3"


def test_interpolate_env_vars_uses_default_when_unset(monkeypatch):
    monkeypatch.delenv("REQSTOOL_VERSION", raising=False)
    assert Utils.interpolate_env_vars("version: ${REQSTOOL_VERSION:-9.9.9}") == "version: 9.9.9"


def test_interpolate_env_vars_default_overridden_when_set(monkeypatch):
    monkeypatch.setenv("REQSTOOL_VERSION", "1.2.3")
    assert Utils.interpolate_env_vars("version: ${REQSTOOL_VERSION:-9.9.9}") == "version: 1.2.3"


def test_interpolate_env_vars_unset_without_default_is_hard_error(monkeypatch):
    monkeypatch.delenv("REQSTOOL_MISSING", raising=False)
    with pytest.raises(EnvVarInterpolationError) as exc_info:
        Utils.interpolate_env_vars("version: ${REQSTOOL_MISSING}", source="requirements.yml")
    assert "REQSTOOL_MISSING" in str(exc_info.value)
    assert "requirements.yml" in str(exc_info.value)


def test_interpolate_env_vars_required_form_raises_custom_message(monkeypatch):
    monkeypatch.delenv("REQSTOOL_MISSING", raising=False)
    with pytest.raises(EnvVarInterpolationError) as exc_info:
        Utils.interpolate_env_vars("version: ${REQSTOOL_MISSING:?must be provided}")
    assert "must be provided" in str(exc_info.value)


def test_interpolate_env_vars_leaves_bare_dollar_and_schema_directive_untouched(monkeypatch):
    # bare $VAR is intentionally not expanded: $schema directives, regexes and
    # prices must survive unchanged.
    monkeypatch.delenv("schema", raising=False)
    text = "# yaml-language-server: $schema=https://example/schema.json\n" "note: price $5, regex ^foo$, literal $$"
    assert Utils.interpolate_env_vars(text) == text


def test_interpolate_env_vars_noop_on_text_without_placeholders():
    text = "version: 1.0.0\nname: reqstool\n"
    assert Utils.interpolate_env_vars(text) == text
