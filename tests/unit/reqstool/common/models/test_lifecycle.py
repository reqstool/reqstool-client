from reqstool.common.models.lifecycle import LIFECYCLESTATE, LifecycleData


def test_from_dict_with_state_and_reason():
    result = LifecycleData.from_dict({"state": "deprecated", "reason": "replaced by REQ_002"})
    assert result.state == LIFECYCLESTATE.DEPRECATED
    assert result.reason == "replaced by REQ_002"


def test_from_dict_with_state_only():
    result = LifecycleData.from_dict({"state": "effective"})
    assert result.state == LIFECYCLESTATE.EFFECTIVE
    assert result.reason is None


def test_from_dict_draft_state():
    result = LifecycleData.from_dict({"state": "draft", "reason": "under review"})
    assert result.state == LIFECYCLESTATE.DRAFT
    assert result.reason == "under review"


def test_from_dict_none_returns_default():
    result = LifecycleData.from_dict(None)
    assert result.state == LIFECYCLESTATE.EFFECTIVE
    assert result.reason is None
