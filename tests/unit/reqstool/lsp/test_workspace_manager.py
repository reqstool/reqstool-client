# Copyright © LFV

import os

from reqstool.lsp.root_discovery import DiscoveredProject, discover_root_projects, _find_roots
from reqstool.lsp.workspace_manager import WorkspaceManager, uri_to_path
from reqstool.models.requirements import VARIANTS


# -- root_discovery tests --


def test_discover_root_ms001(local_testdata_resources_rootdir_w_path):
    workspace = local_testdata_resources_rootdir_w_path("test_standard/baseline")
    roots = discover_root_projects(workspace)
    # ms-001 imports sys-001, so sys-001 is referenced. But ms-001 also imports sys-001
    # meaning sys-001 is referenced by ms-001's imports.
    # ms-001 is not referenced by anyone, so it should be a root.
    urns = {r.urn for r in roots}
    assert "ms-001" in urns


def test_discover_root_basic(local_testdata_resources_rootdir_w_path):
    workspace = local_testdata_resources_rootdir_w_path("test_basic/baseline")
    roots = discover_root_projects(workspace)
    assert len(roots) >= 1
    urns = {r.urn for r in roots}
    assert "ms-101" in urns


def test_discover_empty_folder(tmp_path):
    roots = discover_root_projects(str(tmp_path))
    assert roots == []


def test_discover_no_requirements_yml(tmp_path):
    (tmp_path / "some_file.txt").write_text("hello")
    roots = discover_root_projects(str(tmp_path))
    assert roots == []


def test_discover_single_project(tmp_path):
    req_dir = tmp_path / "my-project"
    req_dir.mkdir()
    (req_dir / "requirements.yml").write_text("metadata:\n  urn: my-proj\n  variant: microservice\n  title: Test\n")
    roots = discover_root_projects(str(tmp_path))
    assert len(roots) == 1
    assert roots[0].urn == "my-proj"
    assert roots[0].variant == VARIANTS.MICROSERVICE


def test_discover_external_not_root(tmp_path):
    ext_dir = tmp_path / "ext-001"
    ext_dir.mkdir()
    (ext_dir / "requirements.yml").write_text("metadata:\n  urn: ext-001\n  variant: external\n  title: External\n")
    roots = discover_root_projects(str(tmp_path))
    assert roots == []


def test_find_roots_referenced_project_excluded():
    sys_project = DiscoveredProject(
        path="/workspace/sys-001",
        urn="sys-001",
        variant=VARIANTS.SYSTEM,
        imported_urns=frozenset(),
        implemented_urns=frozenset({"../ms-001"}),
    )
    ms_project = DiscoveredProject(
        path="/workspace/ms-001",
        urn="ms-001",
        variant=VARIANTS.MICROSERVICE,
        imported_urns=frozenset({"../sys-001"}),
        implemented_urns=frozenset(),
    )
    roots = _find_roots([sys_project, ms_project])
    # Both reference each other — neither is unreferenced.
    # Fallback: all non-external projects are returned.
    assert len(roots) == 2


def test_find_roots_system_is_root():
    sys_project = DiscoveredProject(
        path="/workspace/sys-001",
        urn="sys-001",
        variant=VARIANTS.SYSTEM,
        imported_urns=frozenset(),
        implemented_urns=frozenset({"../ms-001"}),
    )
    ms_project = DiscoveredProject(
        path="/workspace/ms-001",
        urn="ms-001",
        variant=VARIANTS.MICROSERVICE,
        imported_urns=frozenset(),
        implemented_urns=frozenset(),
    )
    roots = _find_roots([sys_project, ms_project])
    # sys-001 references ms-001 via implementations, so ms-001 is referenced.
    # sys-001 is not referenced by anyone → it's the root.
    assert len(roots) == 1
    assert roots[0].urn == "sys-001"


# -- workspace_manager tests --


def test_uri_to_path():
    assert uri_to_path("file:///home/user/project") == "/home/user/project"
    assert uri_to_path("/home/user/project") == "/home/user/project"


def test_uri_to_path_encoded():
    assert uri_to_path("file:///home/user/my%20project") == "/home/user/my project"


def test_workspace_manager_add_folder(local_testdata_resources_rootdir_w_path):
    workspace = local_testdata_resources_rootdir_w_path("test_standard/baseline")
    folder_uri = "file://" + workspace
    manager = WorkspaceManager()
    try:
        projects = manager.add_folder(folder_uri)
        assert len(projects) >= 1
        assert any(p.ready for p in projects)
        assert len(manager.all_projects()) >= 1
    finally:
        manager.close_all()


def test_workspace_manager_remove_folder(local_testdata_resources_rootdir_w_path):
    workspace = local_testdata_resources_rootdir_w_path("test_standard/baseline")
    folder_uri = "file://" + workspace
    manager = WorkspaceManager()
    try:
        manager.add_folder(folder_uri)
        assert len(manager.all_projects()) >= 1
        manager.remove_folder(folder_uri)
        assert len(manager.all_projects()) == 0
    finally:
        manager.close_all()


def test_workspace_manager_project_for_file(local_testdata_resources_rootdir_w_path):
    workspace = local_testdata_resources_rootdir_w_path("test_standard/baseline")
    folder_uri = "file://" + workspace
    manager = WorkspaceManager()
    try:
        manager.add_folder(folder_uri)
        req_file_uri = "file://" + os.path.join(workspace, "ms-001", "requirements.yml")
        project = manager.project_for_file(req_file_uri)
        assert project is not None
        assert project.ready
    finally:
        manager.close_all()


def test_workspace_manager_is_static_yaml():
    assert WorkspaceManager.is_static_yaml("file:///path/to/requirements.yml")
    assert WorkspaceManager.is_static_yaml("file:///path/to/software_verification_cases.yml")
    assert WorkspaceManager.is_static_yaml("file:///path/to/manual_verification_results.yml")
    assert WorkspaceManager.is_static_yaml("file:///path/to/reqstool_config.yml")
    assert not WorkspaceManager.is_static_yaml("file:///path/to/annotations.yml")
    assert not WorkspaceManager.is_static_yaml("file:///path/to/some_file.py")


def test_workspace_manager_rebuild_all(local_testdata_resources_rootdir_w_path):
    workspace = local_testdata_resources_rootdir_w_path("test_standard/baseline")
    folder_uri = "file://" + workspace
    manager = WorkspaceManager()
    try:
        manager.add_folder(folder_uri)
        manager.rebuild_all()
        assert any(p.ready for p in manager.all_projects())
    finally:
        manager.close_all()


def test_workspace_manager_close_all_empty():
    manager = WorkspaceManager()
    manager.close_all()  # should not raise
