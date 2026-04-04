# Copyright © LFV

import os
import tempfile

from reqstool.lsp.root_discovery import discover_root_projects


def _write_requirements_yml(directory: str, urn: str, variant: str = "microservice") -> None:
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, "requirements.yml")
    with open(path, "w") as f:
        f.write(f"metadata:\n  urn: {urn}\n  variant: {variant}\n")


def _write_reqstoolignore(directory: str, content: str = "") -> None:
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, ".reqstoolignore"), "w") as f:
        f.write(content)


# ---------------------------------------------------------------------------
# ** pattern — skip all child directories
# ---------------------------------------------------------------------------


def test_reqstoolignore_wildcard_skips_all_children():
    """The ** pattern skips every child directory."""
    with tempfile.TemporaryDirectory() as tmp:
        _write_requirements_yml(os.path.join(tmp, "docs", "reqstool"), "my-project")

        fixture_root = os.path.join(tmp, "tests", "resources")
        _write_reqstoolignore(fixture_root, "**\n")
        _write_requirements_yml(os.path.join(fixture_root, "fixture-a"), "fixture-a")

        roots = discover_root_projects(tmp)
        urns = {p.urn for p in roots}
        assert "my-project" in urns
        assert "fixture-a" not in urns


def test_reqstoolignore_wildcard_at_workspace_root_skips_all():
    """** at the workspace root blocks discovery of all nested projects."""
    with tempfile.TemporaryDirectory() as tmp:
        _write_reqstoolignore(tmp, "**\n")
        _write_requirements_yml(os.path.join(tmp, "docs", "reqstool"), "my-project")
        assert discover_root_projects(tmp) == []


# ---------------------------------------------------------------------------
# Named patterns — skip only matching child directories
# ---------------------------------------------------------------------------


def test_reqstoolignore_named_patterns_skip_matching_children():
    """Named patterns skip only child directories whose names match."""
    with tempfile.TemporaryDirectory() as tmp:
        _write_requirements_yml(os.path.join(tmp, "docs", "reqstool"), "my-project")

        tests_dir = os.path.join(tmp, "tests")
        _write_reqstoolignore(tests_dir, "fixtures\nresources\n")

        # Skipped — names match patterns
        _write_requirements_yml(os.path.join(tests_dir, "fixtures", "proj-a"), "proj-a")
        _write_requirements_yml(os.path.join(tests_dir, "resources", "proj-b"), "proj-b")

        # Not skipped — name does not match
        _write_requirements_yml(os.path.join(tests_dir, "integration", "docs", "reqstool"), "proj-c")

        roots = discover_root_projects(tmp)
        urns = {p.urn for p in roots}
        assert "my-project" in urns
        assert "proj-a" not in urns
        assert "proj-b" not in urns
        assert "proj-c" in urns


# ---------------------------------------------------------------------------
# Empty file / comments only — no effect
# ---------------------------------------------------------------------------


def test_reqstoolignore_empty_has_no_effect():
    """An empty .reqstoolignore file does not restrict discovery."""
    with tempfile.TemporaryDirectory() as tmp:
        _write_requirements_yml(os.path.join(tmp, "docs", "reqstool"), "my-project")

        fixture_root = os.path.join(tmp, "tests", "resources")
        _write_reqstoolignore(fixture_root)  # empty
        _write_requirements_yml(os.path.join(fixture_root, "fixture-a"), "fixture-a")

        roots = discover_root_projects(tmp)
        urns = {p.urn for p in roots}
        assert "my-project" in urns
        assert "fixture-a" in urns  # discovered normally


def test_reqstoolignore_comments_only_has_no_effect():
    """A .reqstoolignore with only comments does not restrict discovery."""
    with tempfile.TemporaryDirectory() as tmp:
        _write_requirements_yml(os.path.join(tmp, "docs", "reqstool"), "my-project")

        tests_dir = os.path.join(tmp, "tests")
        _write_reqstoolignore(tests_dir, "# this is a comment\n")
        _write_requirements_yml(os.path.join(tests_dir, "fixtures", "docs", "reqstool"), "fixture-proj")

        roots = discover_root_projects(tmp)
        urns = {p.urn for p in roots}
        assert "my-project" in urns
        assert "fixture-proj" in urns


# ---------------------------------------------------------------------------
# No .reqstoolignore — normal discovery
# ---------------------------------------------------------------------------


def test_no_reqstoolignore_discovers_all_roots():
    """Without .reqstoolignore, all non-referenced projects are roots."""
    with tempfile.TemporaryDirectory() as tmp:
        _write_requirements_yml(os.path.join(tmp, "docs", "reqstool"), "project-a")
        _write_requirements_yml(os.path.join(tmp, "services", "svc-b", "docs", "reqstool"), "project-b")

        roots = discover_root_projects(tmp)
        urns = {p.urn for p in roots}
        assert "project-a" in urns
        assert "project-b" in urns
