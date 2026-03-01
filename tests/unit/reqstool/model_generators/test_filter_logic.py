# Copyright © LFV

from packaging.version import Version

from reqstool.common.dataclasses.urn_id import UrnId
from reqstool.filters.requirements_filters import RequirementFilter
from reqstool.filters.svcs_filters import SVCFilter
from reqstool.model_generators.combined_indexed_dataset_generator import CombinedIndexedDatasetGenerator
from reqstool.models.requirements import IMPLEMENTATION, SIGNIFANCETYPES, RequirementData
from reqstool.models.svcs import VERIFICATIONTYPES, SVCData

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

URN = "ext-001"
REQ_A = UrnId(urn=URN, id="REQ_A")
REQ_B = UrnId(urn=URN, id="REQ_B")
SVC_A = UrnId(urn=URN, id="SVC_A")
SVC_B = UrnId(urn=URN, id="SVC_B")


def _req(urn_id: UrnId) -> RequirementData:
    return RequirementData(
        id=urn_id,
        title="t",
        significance=SIGNIFANCETYPES.SHALL,
        description="d",
        rationale="r",
        revision=Version("0.0.1"),
        implementation=IMPLEMENTATION.IN_CODE,
    )


def _svc(urn_id: UrnId) -> SVCData:
    return SVCData(
        id=urn_id,
        title="t",
        description="d",
        verification=VERIFICATIONTYPES.AUTOMATED_TEST,
        instructions="",
        revision=Version("0.0.1"),
    )


def _make_gen(requirements: dict = None, svcs: dict = None) -> CombinedIndexedDatasetGenerator:
    """Construct a partial CombinedIndexedDatasetGenerator, bypassing __post_init__."""
    gen = object.__new__(CombinedIndexedDatasetGenerator)
    gen._requirements = requirements or {}
    gen._svcs = svcs or {}
    return gen


# ---------------------------------------------------------------------------
# __get_filtered_out_requirements_for_filter_urn
# ---------------------------------------------------------------------------

_FILTER_REQS = "_CombinedIndexedDatasetGenerator__get_filtered_out_requirements_for_filter_urn"
_FILTER_SVCS = "_CombinedIndexedDatasetGenerator__get_filtered_out_svcs_for_filter_urn"


def test_req_filter_all_none_imports_everything():
    """No filter criteria: nothing is filtered out."""
    gen = _make_gen({REQ_A: _req(REQ_A), REQ_B: _req(REQ_B)})
    result = getattr(gen, _FILTER_REQS)(
        accessible_requirements={REQ_A, REQ_B},
        urn=URN,
        req_filter=RequirementFilter(),
    )
    assert result == []


def test_req_filter_urn_ids_excludes_removes_matching():
    """urn_ids_excludes: matching req is excluded, non-matching is kept."""
    gen = _make_gen({REQ_A: _req(REQ_A), REQ_B: _req(REQ_B)})
    result = getattr(gen, _FILTER_REQS)(
        accessible_requirements={REQ_A, REQ_B},
        urn=URN,
        req_filter=RequirementFilter(urn_ids_excludes={REQ_A}),
    )
    assert REQ_A in result
    assert REQ_B not in result


def test_req_filter_urn_ids_imports_keeps_only_matching():
    """urn_ids_imports: only the listed req survives; the other is filtered out."""
    gen = _make_gen({REQ_A: _req(REQ_A), REQ_B: _req(REQ_B)})
    result = getattr(gen, _FILTER_REQS)(
        accessible_requirements={REQ_A, REQ_B},
        urn=URN,
        req_filter=RequirementFilter(urn_ids_imports={REQ_A}),
    )
    assert REQ_B in result
    assert REQ_A not in result


def test_req_filter_custom_exclude_el_removes_matching():
    """custom_exclude EL: req matching the expression is filtered out."""
    gen = _make_gen({REQ_A: _req(REQ_A), REQ_B: _req(REQ_B)})
    result = getattr(gen, _FILTER_REQS)(
        accessible_requirements={REQ_A, REQ_B},
        urn=URN,
        req_filter=RequirementFilter(custom_exclude=f'ids == "{URN}:{REQ_A.id}"'),
    )
    assert REQ_A in result
    assert REQ_B not in result


def test_req_filter_custom_imports_el_keeps_only_matching():
    """custom_imports EL: only the matching req survives."""
    gen = _make_gen({REQ_A: _req(REQ_A), REQ_B: _req(REQ_B)})
    result = getattr(gen, _FILTER_REQS)(
        accessible_requirements={REQ_A, REQ_B},
        urn=URN,
        req_filter=RequirementFilter(custom_imports=f'ids == "{URN}:{REQ_A.id}"'),
    )
    assert REQ_B in result
    assert REQ_A not in result


def test_req_filter_urn_ids_excludes_combined_with_custom_exclude():
    """urn_ids_excludes OR custom_exclude: req is excluded if either matches."""
    gen = _make_gen({REQ_A: _req(REQ_A), REQ_B: _req(REQ_B)})
    result = getattr(gen, _FILTER_REQS)(
        accessible_requirements={REQ_A, REQ_B},
        urn=URN,
        req_filter=RequirementFilter(
            urn_ids_excludes={REQ_A},
            custom_exclude=f'ids == "{URN}:{REQ_B.id}"',
        ),
    )
    assert REQ_A in result
    assert REQ_B in result


# ---------------------------------------------------------------------------
# __get_filtered_out_svcs_for_filter_urn
# ---------------------------------------------------------------------------


def test_svc_filter_all_none_imports_everything():
    """No filter criteria: nothing is filtered out."""
    gen = _make_gen(svcs={SVC_A: _svc(SVC_A), SVC_B: _svc(SVC_B)})
    result = getattr(gen, _FILTER_SVCS)(
        accessible_svcs={SVC_A, SVC_B},
        urn=URN,
        svc_filter=SVCFilter(),
    )
    assert result == []


def test_svc_filter_urn_ids_excludes_removes_matching():
    """urn_ids_excludes: matching SVC is excluded, non-matching is kept."""
    gen = _make_gen(svcs={SVC_A: _svc(SVC_A), SVC_B: _svc(SVC_B)})
    result = getattr(gen, _FILTER_SVCS)(
        accessible_svcs={SVC_A, SVC_B},
        urn=URN,
        svc_filter=SVCFilter(urn_ids_excludes={SVC_A}),
    )
    assert SVC_A in result
    assert SVC_B not in result


def test_svc_filter_urn_ids_imports_keeps_only_matching():
    """urn_ids_imports: only the listed SVC survives."""
    gen = _make_gen(svcs={SVC_A: _svc(SVC_A), SVC_B: _svc(SVC_B)})
    result = getattr(gen, _FILTER_SVCS)(
        accessible_svcs={SVC_A, SVC_B},
        urn=URN,
        svc_filter=SVCFilter(urn_ids_imports={SVC_A}),
    )
    assert SVC_B in result
    assert SVC_A not in result
