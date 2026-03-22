# Copyright © LFV

from unittest.mock import MagicMock

from reqstool.lsp.server import _find_details


def _make_ls(projects):
    ls = MagicMock()
    ls.workspace_manager.all_projects.return_value = projects
    return ls


def test_find_details_returns_first_match():
    fn = MagicMock(side_effect=[None, {"type": "requirement", "id": "REQ_010"}])
    p1 = MagicMock()
    p1.ready = True
    p2 = MagicMock()
    p2.ready = True
    ls = _make_ls([p1, p2])

    result = _find_details("REQ_010", fn, ls)
    assert result == {"type": "requirement", "id": "REQ_010"}
    assert fn.call_count == 2


def test_find_details_skips_not_ready():
    fn = MagicMock(return_value={"type": "requirement", "id": "REQ_010"})
    p_not_ready = MagicMock()
    p_not_ready.ready = False
    p_ready = MagicMock()
    p_ready.ready = True
    ls = _make_ls([p_not_ready, p_ready])

    result = _find_details("REQ_010", fn, ls)
    assert result == {"type": "requirement", "id": "REQ_010"}
    fn.assert_called_once_with("REQ_010", p_ready)


def test_find_details_unknown_id_returns_none():
    fn = MagicMock(return_value=None)
    p = MagicMock()
    p.ready = True
    ls = _make_ls([p])

    result = _find_details("REQ_NONEXISTENT", fn, ls)
    assert result is None


def test_find_details_no_projects_returns_none():
    fn = MagicMock()
    ls = _make_ls([])

    result = _find_details("REQ_010", fn, ls)
    assert result is None
    fn.assert_not_called()
