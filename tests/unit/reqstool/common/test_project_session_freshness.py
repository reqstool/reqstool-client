# Copyright © LFV

import os
import shutil

import pytest
from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.common.exceptions import SnapshotReloadError
from reqstool.common.project_session import ProjectSession
from reqstool.locations.local_location import LocalLocation
from reqstool.services.statistics_service import StatisticsService

ANNOTATIONS_WITH_EXTRA_IMPL = """\
---
requirement_annotations:
  implementations:
    REQ_101:
      - elementKind: "CLASS"
        fullyQualifiedName: "com.example.RequirementsExample"
      - elementKind: "METHOD"
        fullyQualifiedName: "com.example.RequirementsExample.addedAfterStartup"
    REQ_201:
      - elementKind: "METHOD"
        fullyQualifiedName: "com.example.RequirementsExample.someMethod"
"""


@pytest.fixture
def project_copy(tmp_path, local_testdata_resources_rootdir_w_path):
    """A writable copy of the ms-101 fixture, so a test can simulate a build changing it."""
    dst = tmp_path / "ms-101"
    shutil.copytree(local_testdata_resources_rootdir_w_path("test_basic/baseline/ms-101"), dst)
    return dst


def _implementation_count(session: ProjectSession) -> int:
    return sum(len(impls) for impls in session.repo.get_annotations_impls().values())


def _automated_tests(session: ProjectSession) -> dict:
    """Automated test totals as the status command computes them."""
    return StatisticsService(session.repo).to_status_dict()["totals"]["automated_tests"]


@pytest.fixture
def session(project_copy):
    session = ProjectSession(LocalLocation(path=str(project_copy)))
    session.build()
    assert session.ready
    yield session
    session.close()


@SVCs("SVC_MCP_0006")
def test_unchanged_project_is_not_rebuilt(session):
    built_at = session.built_at

    assert session.ensure_fresh() is False
    assert session.built_at == built_at


@SVCs("SVC_MCP_0006")
def test_edited_annotations_are_picked_up_without_a_restart(session, project_copy):
    """The reported failure: a build regenerates annotations while the server keeps serving."""
    before = _implementation_count(session)

    (project_copy / "annotations.yml").write_text(ANNOTATIONS_WITH_EXTRA_IMPL)

    assert session.ensure_fresh() is True
    assert _implementation_count(session) == before + 1


@SVCs("SVC_MCP_0006")
def test_test_results_written_after_startup_are_picked_up(
    session, project_copy, local_testdata_resources_rootdir_w_path
):
    """The reported scenario: the server was started before the build produced any JUnit XML.

    Test results are resolved from a glob, so files appearing under a matched pattern have
    to count as a change — not stay reported as zero passing tests.
    """
    results = project_copy / "test_results"
    shutil.rmtree(results)
    session.build()
    assert _automated_tests(session)["passed"] == 0

    shutil.copytree(local_testdata_resources_rootdir_w_path("test_basic/baseline/ms-101/test_results"), results)

    assert session.ensure_fresh() is True
    assert _automated_tests(session)["passed"] > 0


@SVCs("SVC_MCP_0006")
def test_an_annotations_file_created_after_startup_is_picked_up(session, project_copy):
    """Files absent at build time are tracked too — that is the unbuilt-project case."""
    os.remove(project_copy / "annotations.yml")
    session.build()
    assert session.repo.get_annotations_impls() == {}

    (project_copy / "annotations.yml").write_text(ANNOTATIONS_WITH_EXTRA_IMPL)

    assert session.ensure_fresh() is True
    assert len(session.repo.get_annotations_impls()) > 0


@SVCs("SVC_MCP_0007")
def test_a_broken_reload_reports_an_error_rather_than_the_superseded_snapshot(session, project_copy):
    (project_copy / "requirements.yml").write_text(": this is not: [ valid yaml")

    with pytest.raises(SnapshotReloadError, match="sources changed but reloading them failed"):
        session.ensure_fresh()

    assert not session.ready
    assert session.repo is None


@SVCs("SVC_MCP_0007")
def test_an_unfixed_project_keeps_reporting_the_error_without_reparsing(session, project_copy):
    requirements = project_copy / "requirements.yml"
    original = requirements.read_text()
    requirements.write_text(": this is not: [ valid yaml")

    with pytest.raises(SnapshotReloadError, match="sources changed but reloading them failed"):
        session.ensure_fresh()
    # Re-stamped on failure: the broken tree is not re-parsed until it changes again.
    with pytest.raises(SnapshotReloadError, match="project is not loaded"):
        session.ensure_fresh()

    requirements.write_text(original)

    assert session.ensure_fresh() is True
    assert session.ready


@SVCs("SVC_MCP_0008")
def test_snapshot_records_when_it_was_built_and_what_it_tracks(session, project_copy):
    assert session.built_at is not None
    assert session.initial_urn == "ms-101"

    fingerprint = session.fingerprint
    tracked = {stamp.path for stamp in fingerprint.stamps}
    assert str(project_copy / "requirements.yml") in tracked
    assert str(project_copy / "annotations.yml") in tracked
    # The two JUnit XML files of the fixture, matched by the configured pattern.
    assert fingerprint.tracked_file_count == len(fingerprint.stamps) + 2

    built_at = session.built_at
    (project_copy / "annotations.yml").write_text(ANNOTATIONS_WITH_EXTRA_IMPL)
    session.ensure_fresh()

    assert session.built_at != built_at


@SVCs("SVC_MCP_0008")
def test_absent_test_results_are_warned_about_rather_than_counted_as_zero(session, project_copy):
    shutil.rmtree(project_copy / "test_results")
    session.build()

    assert _automated_tests(session)["passed"] == 0
    warnings = session.fingerprint.warnings(primary_urn=session.initial_urn)
    assert warnings == [f"[ms-101] test_results pattern 'test_results/**/*.xml' matched no files under {project_copy}"]
