# Copyright © LFV

from unittest.mock import MagicMock


from reqstool.common.filter_parser import parse_filters
from reqstool.common.models.urn_id import UrnId
from reqstool.filters.requirements_filters import RequirementFilter
from reqstool.filters.svcs_filters import SVCFilter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

URN = "ms-001"


def _noop_validate(data):
    """No-op validator used where validation behaviour is not under test."""
    pass


# ---------------------------------------------------------------------------
# Empty / missing filters section
# ---------------------------------------------------------------------------


def test_parse_filters_no_filters_key_returns_empty_dict():
    data = {"metadata": {"urn": URN}}
    result = parse_filters(
        data=data, ids_key="requirement_ids", filter_cls=RequirementFilter, validate_fn=_noop_validate
    )
    assert result == {}


def test_parse_filters_empty_filters_section_returns_empty_dict():
    data = {"filters": {}}
    result = parse_filters(
        data=data, ids_key="requirement_ids", filter_cls=RequirementFilter, validate_fn=_noop_validate
    )
    assert result == {}


# ---------------------------------------------------------------------------
# includes only
# ---------------------------------------------------------------------------


def test_parse_filters_requirement_ids_includes_only():
    data = {
        "filters": {
            URN: {
                "requirement_ids": {
                    "includes": ["REQ_001", "REQ_002"],
                }
            }
        }
    }
    result = parse_filters(
        data=data, ids_key="requirement_ids", filter_cls=RequirementFilter, validate_fn=_noop_validate
    )

    assert URN in result
    req_filter = result[URN]
    assert isinstance(req_filter, RequirementFilter)
    assert req_filter.urn_ids_imports == {UrnId(urn=URN, id="REQ_001"), UrnId(urn=URN, id="REQ_002")}
    assert req_filter.urn_ids_excludes is None
    assert req_filter.custom_imports is None
    assert req_filter.custom_exclude is None


def test_parse_filters_svc_ids_includes_only():
    data = {
        "filters": {
            URN: {
                "svc_ids": {
                    "includes": ["SVC_001"],
                }
            }
        }
    }
    result = parse_filters(data=data, ids_key="svc_ids", filter_cls=SVCFilter, validate_fn=_noop_validate)

    assert URN in result
    svc_filter = result[URN]
    assert isinstance(svc_filter, SVCFilter)
    assert svc_filter.urn_ids_imports == {UrnId(urn=URN, id="SVC_001")}
    assert svc_filter.urn_ids_excludes is None


# ---------------------------------------------------------------------------
# excludes only
# ---------------------------------------------------------------------------


def test_parse_filters_requirement_ids_excludes_only():
    data = {
        "filters": {
            URN: {
                "requirement_ids": {
                    "excludes": ["REQ_003"],
                }
            }
        }
    }
    result = parse_filters(
        data=data, ids_key="requirement_ids", filter_cls=RequirementFilter, validate_fn=_noop_validate
    )

    req_filter = result[URN]
    assert req_filter.urn_ids_imports is None
    assert req_filter.urn_ids_excludes == {UrnId(urn=URN, id="REQ_003")}


# ---------------------------------------------------------------------------
# custom includes / excludes
# ---------------------------------------------------------------------------


def test_parse_filters_custom_includes_only():
    data = {
        "filters": {
            URN: {
                "custom": {
                    "includes": "significance == SHALL",
                }
            }
        }
    }
    result = parse_filters(
        data=data, ids_key="requirement_ids", filter_cls=RequirementFilter, validate_fn=_noop_validate
    )

    req_filter = result[URN]
    assert req_filter.urn_ids_imports is None
    assert req_filter.urn_ids_excludes is None
    assert req_filter.custom_imports == "significance == SHALL"
    assert req_filter.custom_exclude is None


def test_parse_filters_custom_excludes_only():
    data = {
        "filters": {
            URN: {
                "custom": {
                    "excludes": "significance == MAY",
                }
            }
        }
    }
    result = parse_filters(
        data=data, ids_key="requirement_ids", filter_cls=RequirementFilter, validate_fn=_noop_validate
    )

    req_filter = result[URN]
    assert req_filter.custom_imports is None
    assert req_filter.custom_exclude == "significance == MAY"


def test_parse_filters_custom_includes_and_excludes():
    data = {
        "filters": {
            URN: {
                "custom": {
                    "includes": "significance == SHALL",
                    "excludes": "significance == MAY",
                }
            }
        }
    }
    result = parse_filters(
        data=data, ids_key="requirement_ids", filter_cls=RequirementFilter, validate_fn=_noop_validate
    )

    req_filter = result[URN]
    assert req_filter.custom_imports == "significance == SHALL"
    assert req_filter.custom_exclude == "significance == MAY"


# ---------------------------------------------------------------------------
# Validator is called
# ---------------------------------------------------------------------------


def test_parse_filters_calls_validate_fn():
    data = {"filters": {}}
    mock_validate = MagicMock()

    parse_filters(data=data, ids_key="requirement_ids", filter_cls=RequirementFilter, validate_fn=mock_validate)

    mock_validate.assert_called_once_with(data)


def test_parse_filters_calls_validate_fn_even_when_no_filters_key():
    data = {}
    mock_validate = MagicMock()

    parse_filters(data=data, ids_key="requirement_ids", filter_cls=RequirementFilter, validate_fn=mock_validate)

    mock_validate.assert_called_once_with(data)


# ---------------------------------------------------------------------------
# Multiple URN entries
# ---------------------------------------------------------------------------


def test_parse_filters_multiple_urns():
    urn_a = "sys-001"
    urn_b = "ms-001"
    data = {
        "filters": {
            urn_a: {
                "requirement_ids": {
                    "includes": ["REQ_001"],
                }
            },
            urn_b: {
                "requirement_ids": {
                    "excludes": ["REQ_002"],
                }
            },
        }
    }
    result = parse_filters(
        data=data, ids_key="requirement_ids", filter_cls=RequirementFilter, validate_fn=_noop_validate
    )

    assert urn_a in result
    assert urn_b in result
    assert result[urn_a].urn_ids_imports == {UrnId(urn=urn_a, id="REQ_001")}
    assert result[urn_b].urn_ids_excludes == {UrnId(urn=urn_b, id="REQ_002")}


# ---------------------------------------------------------------------------
# Qualified IDs (urn:id format) are handled correctly
# ---------------------------------------------------------------------------


def test_parse_filters_qualified_id_is_preserved():
    data = {
        "filters": {
            URN: {
                "requirement_ids": {
                    "includes": [f"{URN}:REQ_010"],
                }
            }
        }
    }
    result = parse_filters(
        data=data, ids_key="requirement_ids", filter_cls=RequirementFilter, validate_fn=_noop_validate
    )

    req_filter = result[URN]
    assert UrnId(urn=URN, id="REQ_010") in req_filter.urn_ids_imports
