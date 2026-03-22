# Copyright © LFV

from reqstool.lsp.project_state import ProjectState


def test_build_standard_ms001(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    state = ProjectState(reqstool_path=path)
    try:
        state.build()
        assert state.ready
        assert state.error is None
        assert state.get_initial_urn() == "ms-001"
    finally:
        state.close()


def test_build_basic_ms101(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_basic/baseline/ms-101")
    state = ProjectState(reqstool_path=path)
    try:
        state.build()
        assert state.ready
        assert state.error is None
    finally:
        state.close()


def test_get_all_requirement_ids(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    state = ProjectState(reqstool_path=path)
    try:
        state.build()
        req_ids = state.get_all_requirement_ids()
        assert len(req_ids) > 0
        assert "REQ_010" in req_ids
    finally:
        state.close()


def test_get_all_svc_ids(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    state = ProjectState(reqstool_path=path)
    try:
        state.build()
        svc_ids = state.get_all_svc_ids()
        assert len(svc_ids) > 0
    finally:
        state.close()


def test_get_requirement(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    state = ProjectState(reqstool_path=path)
    try:
        state.build()
        req = state.get_requirement("REQ_010")
        assert req is not None
        assert req.title == "Title REQ_010"
    finally:
        state.close()


def test_get_requirement_not_found(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    state = ProjectState(reqstool_path=path)
    try:
        state.build()
        req = state.get_requirement("REQ_NONEXISTENT")
        assert req is None
    finally:
        state.close()


def test_get_svc(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    state = ProjectState(reqstool_path=path)
    try:
        state.build()
        svc_ids = state.get_all_svc_ids()
        if svc_ids:
            svc = state.get_svc(svc_ids[0])
            assert svc is not None
    finally:
        state.close()


def test_rebuild(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    state = ProjectState(reqstool_path=path)
    try:
        state.build()
        assert state.ready
        state.rebuild()
        assert state.ready
        assert state.get_initial_urn() == "ms-001"
    finally:
        state.close()


def test_close_idempotent(local_testdata_resources_rootdir_w_path):
    path = local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")
    state = ProjectState(reqstool_path=path)
    state.build()
    state.close()
    assert not state.ready
    state.close()  # should not raise


def test_queries_when_not_ready():
    state = ProjectState(reqstool_path="/nonexistent")
    assert not state.ready
    assert state.get_initial_urn() is None
    assert state.get_requirement("REQ_010") is None
    assert state.get_svc("SVC_010") is None
    assert state.get_svcs_for_req("REQ_010") == []
    assert state.get_mvrs_for_svc("SVC_010") == []
    assert state.get_all_requirement_ids() == []
    assert state.get_all_svc_ids() == []


def test_build_nonexistent_path():
    state = ProjectState(reqstool_path="/nonexistent/path")
    state.build()
    assert not state.ready
    assert state.error is not None
