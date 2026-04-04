# Copyright © LFV

import os
import tempfile

from reqstool.lsp.root_discovery import discover_root_projects


def _write_requirements_yml(directory: str, urn: str, variant: str = "microservice") -> None:
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, "requirements.yml")
    with open(path, "w") as f:
        f.write(f"metadata:\n  urn: {urn}\n  variant: {variant}\n")


def test_reqstoolignore_skips_directory():
    """A directory containing .reqstoolignore must not yield any projects."""
    with tempfile.TemporaryDirectory() as tmp:
        # Real project
        real = os.path.join(tmp, "docs", "reqstool")
        _write_requirements_yml(real, "my-project")

        # Test fixture directory with .reqstoolignore
        fixture_root = os.path.join(tmp, "tests", "resources")
        os.makedirs(fixture_root, exist_ok=True)
        open(os.path.join(fixture_root, ".reqstoolignore"), "w").close()

        fixture = os.path.join(fixture_root, "fixture-a")
        _write_requirements_yml(fixture, "fixture-a")

        roots = discover_root_projects(tmp)
        urns = {p.urn for p in roots}
        assert "my-project" in urns
        assert "fixture-a" not in urns


def test_reqstoolignore_at_workspace_root_skips_all():
    """A .reqstoolignore at the workspace root itself means nothing is discovered."""
    with tempfile.TemporaryDirectory() as tmp:
        open(os.path.join(tmp, ".reqstoolignore"), "w").close()
        _write_requirements_yml(os.path.join(tmp, "docs", "reqstool"), "my-project")
        roots = discover_root_projects(tmp)
        assert roots == []


def test_no_reqstoolignore_discovers_all_roots():
    """Without .reqstoolignore, all non-referenced projects are roots."""
    with tempfile.TemporaryDirectory() as tmp:
        _write_requirements_yml(os.path.join(tmp, "docs", "reqstool"), "project-a")
        _write_requirements_yml(os.path.join(tmp, "services", "svc-b", "docs", "reqstool"), "project-b")

        roots = discover_root_projects(tmp)
        urns = {p.urn for p in roots}
        assert "project-a" in urns
        assert "project-b" in urns
