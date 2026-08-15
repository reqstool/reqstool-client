# Copyright © LFV

import os

from reqstool.common.snapshot_fingerprint import FileStamp, GlobSpec, SnapshotFingerprint

URN = "ms-101"


def _write(path, content: str = "x"):
    with open(path, "w") as f:
        f.write(content)
    return str(path)


def _fingerprint_of(paths, kind: str = "requirements") -> SnapshotFingerprint:
    return SnapshotFingerprint(stamps=tuple(FileStamp.capture(str(p), kind, URN) for p in paths))


# ---------------------------------------------------------------------------
# FileStamp
# ---------------------------------------------------------------------------


def test_unchanged_file_is_not_stale(tmp_path):
    fingerprint = _fingerprint_of([_write(tmp_path / "requirements.yml")])

    assert not fingerprint.is_stale()
    assert fingerprint.stale_reasons() == []


def test_modified_file_is_stale(tmp_path):
    path = _write(tmp_path / "requirements.yml", "before")
    fingerprint = _fingerprint_of([path])

    _write(path, "after (a different size, so mtime granularity cannot hide the change)")

    assert fingerprint.is_stale()
    assert fingerprint.stale_reasons() == [f"modified: {path}"]


def test_removed_file_is_stale(tmp_path):
    path = _write(tmp_path / "requirements.yml")
    fingerprint = _fingerprint_of([path])

    os.remove(path)

    assert fingerprint.stale_reasons() == [f"removed: {path}"]


def test_file_absent_at_capture_that_appears_is_stale(tmp_path):
    """The reported failure mode: a build generates annotations.yml after the server started."""
    path = str(tmp_path / "annotations.yml")
    fingerprint = _fingerprint_of([path], kind="annotations")

    assert not fingerprint.is_stale()

    _write(path, "annotations: {}")

    assert fingerprint.stale_reasons() == [f"added: {path}"]


def test_stale_reasons_honours_limit(tmp_path):
    paths = [_write(tmp_path / f"f{i}.yml") for i in range(4)]
    fingerprint = _fingerprint_of(paths)
    for path in paths:
        os.remove(path)

    assert len(fingerprint.stale_reasons(limit=2)) == 2
    assert len(fingerprint.stale_reasons()) == 4


# ---------------------------------------------------------------------------
# GlobSpec — test results are resolved from patterns, not fixed paths
# ---------------------------------------------------------------------------


def _test_results_fingerprint(root, pattern: str = "**/*.xml") -> SnapshotFingerprint:
    matched = [str(p) for p in root.rglob(pattern)]
    return SnapshotFingerprint(globs=(GlobSpec.capture(str(root), pattern, URN, matched),))


def test_new_test_result_file_is_stale(tmp_path):
    reports = tmp_path / "target" / "surefire-reports"
    reports.mkdir(parents=True)
    _write(reports / "TEST-a.xml", "<testsuite/>")

    fingerprint = _test_results_fingerprint(tmp_path)
    assert not fingerprint.is_stale()

    _write(reports / "TEST-b.xml", "<testsuite/>")

    assert fingerprint.stale_reasons() == [
        f"test results changed for pattern '**/*.xml' under {tmp_path} (+1/-0 files)"
    ]


def test_rewritten_test_result_file_is_stale(tmp_path):
    reports = tmp_path / "target" / "surefire-reports"
    reports.mkdir(parents=True)
    xml = reports / "TEST-a.xml"
    _write(xml, "<testsuite tests='1'/>")

    fingerprint = _test_results_fingerprint(tmp_path)

    _write(xml, "<testsuite tests='2' failures='0'/>")

    assert fingerprint.stale_reasons() == [f"test result modified: {xml}"]


def test_pattern_matching_no_files_is_reported_as_a_warning(tmp_path):
    fingerprint = _test_results_fingerprint(tmp_path, pattern="target/surefire-reports/*.xml")

    assert not fingerprint.is_stale()
    assert fingerprint.warnings() == [
        f"[{URN}] test_results pattern 'target/surefire-reports/*.xml' matched no files under {tmp_path}"
    ]


# ---------------------------------------------------------------------------
# SnapshotFingerprint
# ---------------------------------------------------------------------------


def test_missing_annotations_warns_only_for_the_primary_urn(tmp_path):
    primary = FileStamp.capture(str(tmp_path / "annotations.yml"), "annotations", "ms-101")
    imported = FileStamp.capture(str(tmp_path / "sys" / "annotations.yml"), "annotations", "sys-101")
    fingerprint = SnapshotFingerprint(stamps=(primary, imported))

    warnings = fingerprint.warnings(primary_urn="ms-101")

    assert len(warnings) == 1
    assert "[ms-101]" in warnings[0]


def test_missing_annotations_of_imported_sources_is_not_a_warning(tmp_path):
    imported = FileStamp.capture(str(tmp_path / "sys" / "annotations.yml"), "annotations", "sys-101")

    assert SnapshotFingerprint(stamps=(imported,)).warnings(primary_urn="ms-101") == []


def test_restamped_fingerprint_tracks_the_same_inputs_as_they_are_now(tmp_path):
    path = _write(tmp_path / "requirements.yml", "before")
    fingerprint = _fingerprint_of([path])
    _write(path, "after — a broken edit that fails to parse")

    assert fingerprint.is_stale()

    restamped = fingerprint.restamped()

    assert not restamped.is_stale()
    assert [s.path for s in restamped.stamps] == [path]

    _write(path, "the next edit, which must be noticed again")
    assert restamped.is_stale()


def test_merge_combines_every_source(tmp_path):
    a = _fingerprint_of([_write(tmp_path / "a.yml")])
    b = _test_results_fingerprint(tmp_path)

    merged = SnapshotFingerprint.merge([a, b])

    assert len(merged.stamps) == 1
    assert len(merged.globs) == 1
    assert merged.tracked_file_count == 1 + len(b.globs[0].matched)


def test_empty_fingerprint_is_never_stale():
    """Remote sources are version-pinned downloads: nothing local to watch."""
    assert not SnapshotFingerprint().is_stale()
    assert SnapshotFingerprint().tracked_file_count == 0
