# Copyright © LFV

"""Fingerprint of the local input files a parsed snapshot was built from.

A long-lived server (MCP) parses once and then serves that snapshot. The fingerprint
records what was read — and what was looked for but absent — so the server can tell,
cheaply and per request, whether the snapshot still matches the working tree.

Only local sources are fingerprinted. Remote sources (git/maven/npm/pypi) are
version-pinned downloads materialized into a temp directory that is removed once
parsing finishes, so there is nothing stable to stat.
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FileStamp:
    """Identity of a single input file at capture time.

    Absent files are stamped too (``exists=False``): an ``annotations.yml`` that the build
    has not generated yet is the common staleness trigger, and it can only be detected by
    having recorded that we looked for it.
    """

    path: str
    kind: str
    urn: str
    exists: bool = True
    mtime_ns: int = 0
    size: int = 0

    @staticmethod
    def capture(path: str, kind: str, urn: str) -> "FileStamp":
        try:
            st = os.stat(path)
        except OSError:
            return FileStamp(path=path, kind=kind, urn=urn, exists=False)
        return FileStamp(path=path, kind=kind, urn=urn, exists=True, mtime_ns=st.st_mtime_ns, size=st.st_size)

    def changed_on_disk(self) -> Optional[str]:
        """Return a human-readable reason if disk no longer matches this stamp, else None."""
        current = FileStamp.capture(self.path, self.kind, self.urn)

        if current.exists is not self.exists:
            return f"{'removed' if self.exists else 'added'}: {self.path}"

        if current.exists and (current.mtime_ns != self.mtime_ns or current.size != self.size):
            return f"modified: {self.path}"

        return None


@dataclass(frozen=True)
class GlobSpec:
    """A test-results glob pattern and the files it matched at capture time.

    Test results are resolved from patterns, not fixed paths, so freshness means
    "the pattern still matches the same files, unchanged" — a new JUnit XML dropped
    into a report directory has to count as a change.
    """

    root: str
    pattern: str
    urn: str
    matched: Tuple[FileStamp, ...] = ()

    @staticmethod
    def capture(root: str, pattern: str, urn: str, matched_paths: List[str]) -> "GlobSpec":
        stamps = tuple(sorted((FileStamp.capture(p, "test_results", urn) for p in matched_paths), key=lambda s: s.path))
        return GlobSpec(root=root, pattern=pattern, urn=urn, matched=stamps)

    @property
    def matched_paths(self) -> Tuple[str, ...]:
        return tuple(stamp.path for stamp in self.matched)

    def changed_on_disk(self) -> Optional[str]:
        """Return a human-readable reason if the pattern no longer resolves as captured, else None."""
        try:
            current = tuple(sorted(str(p) for p in Path(self.root).rglob(self.pattern)))
        except OSError as e:
            return f"test results unreadable for pattern {self.pattern!r} under {self.root}: {e}"

        if current != self.matched_paths:
            added = len(set(current) - set(self.matched_paths))
            removed = len(set(self.matched_paths) - set(current))
            return f"test results changed for pattern {self.pattern!r} under {self.root} (+{added}/-{removed} files)"

        for stamp in self.matched:
            reason = stamp.changed_on_disk()
            if reason is not None:
                return f"test result {reason}"

        return None


@dataclass(frozen=True)
class SnapshotFingerprint:
    """The full set of local inputs a snapshot was built from."""

    stamps: Tuple[FileStamp, ...] = ()
    globs: Tuple[GlobSpec, ...] = ()

    @staticmethod
    def merge(parts: List["SnapshotFingerprint"]) -> "SnapshotFingerprint":
        stamps: List[FileStamp] = []
        globs: List[GlobSpec] = []
        for part in parts:
            stamps.extend(part.stamps)
            globs.extend(part.globs)
        return SnapshotFingerprint(stamps=tuple(stamps), globs=tuple(globs))

    @property
    def tracked_file_count(self) -> int:
        return len(self.stamps) + sum(len(g.matched) for g in self.globs)

    def stale_reasons(self, limit: Optional[int] = None) -> List[str]:
        """Reasons this snapshot no longer matches disk, at most ``limit`` of them."""
        reasons: List[str] = []

        for checkable in (*self.stamps, *self.globs):
            reason = checkable.changed_on_disk()
            if reason is not None:
                reasons.append(reason)
                if limit is not None and len(reasons) >= limit:
                    break

        return reasons

    def is_stale(self) -> bool:
        return bool(self.stale_reasons(limit=1))

    def restamped(self) -> "SnapshotFingerprint":
        """Same tracked inputs, re-read from disk.

        Used after a failed reload: the paths we know about are still the right ones to
        watch, but re-stamping them stops a broken working tree from being re-parsed on
        every single request — the next edit flips it stale again.
        """
        stamps = tuple(FileStamp.capture(s.path, s.kind, s.urn) for s in self.stamps)
        globs = []
        for g in self.globs:
            try:
                matched_paths = [str(p) for p in Path(g.root).rglob(g.pattern)]
            except OSError:
                matched_paths = list(g.matched_paths)
            globs.append(GlobSpec.capture(g.root, g.pattern, g.urn, matched_paths))
        return SnapshotFingerprint(stamps=stamps, globs=tuple(globs))

    def warnings(self, primary_urn: Optional[str] = None) -> List[str]:
        """Input conditions that make a well-formed answer misleading.

        A test-results pattern matching nothing is reported as such rather than silently
        counted as zero tests — that is the incremental-build trap this exists for.

        A missing annotations file is only worth reporting for ``primary_urn``, the source
        the session was opened on: imported sources supply requirements, and are not
        expected to carry implementation annotations of their own.
        """
        warnings: List[str] = []

        for g in self.globs:
            if not g.matched:
                warnings.append(f"[{g.urn}] test_results pattern {g.pattern!r} matched no files under {g.root}")

        for s in self.stamps:
            if s.kind == "annotations" and not s.exists and s.urn == primary_urn:
                warnings.append(
                    f"[{s.urn}] no annotations file at {s.path} — "
                    "implementation and test annotations are reported as absent"
                )

        return warnings
