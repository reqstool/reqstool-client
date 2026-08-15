# Copyright © LFV


import logging
import threading
from datetime import datetime, timezone

from reqstool.common.exceptions import SnapshotReloadError
from reqstool.common.snapshot_fingerprint import SnapshotFingerprint
from reqstool.common.validators.lifecycle_validator import LifecycleValidator
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.locations.location import LocationInterface
from reqstool.model_generators.combined_raw_datasets_generator import CombinedRawDatasetsGenerator
from reqstool.model_generators.parsing_config import ParsingConfig
from reqstool.storage.database import RequirementsDatabase
from reqstool.storage.database_filter_processor import DatabaseFilterProcessor
from reqstool.storage.requirements_repository import RequirementsRepository

logger = logging.getLogger(__name__)


class ProjectSession:
    """Long-lived database session for a reqstool project loaded from any LocationInterface.

    Keeps the SQLite database open for the lifetime of the session (unlike the
    build_database() context manager which closes on exit). Suitable for servers
    (MCP, LSP) that need persistent read access after a one-time build.

    A session records a fingerprint of the local files it parsed. Servers without an
    external change signal call `ensure_fresh()` before serving a request; servers driven
    by client file-change notifications (LSP) call `rebuild()` directly.
    """

    def __init__(self, location: LocationInterface, parsing_config: ParsingConfig = ParsingConfig()):
        self._location = location
        self._parsing_config = parsing_config
        self._db: RequirementsDatabase | None = None
        self._repo: RequirementsRepository | None = None
        self._urn_source_paths: dict[str, dict[str, str]] = {}
        self._ready: bool = False
        self._error: str | None = None
        self._fingerprint: SnapshotFingerprint | None = None
        self._built_at: str | None = None
        self._initial_urn: str | None = None
        # ensure_fresh() may rebuild the database underneath concurrent request handlers.
        self._lock = threading.RLock()

    @property
    def ready(self) -> bool:
        return self._ready

    @property
    def error(self) -> str | None:
        return self._error

    @property
    def repo(self) -> RequirementsRepository | None:
        return self._repo

    @property
    def urn_source_paths(self) -> dict[str, dict[str, str]]:
        return self._urn_source_paths

    @property
    def fingerprint(self) -> SnapshotFingerprint | None:
        return self._fingerprint

    @property
    def built_at(self) -> str | None:
        """When the current snapshot was parsed (ISO 8601, UTC), or None if never built."""
        return self._built_at

    @property
    def initial_urn(self) -> str | None:
        """URN of the source this session was opened on (imports and implementations excluded)."""
        return self._initial_urn

    def build(self) -> None:
        with self._lock:
            previous_fingerprint = self._fingerprint
            self.close()
            self._error = None
            db = RequirementsDatabase()
            try:
                holder = ValidationErrorHolder()
                semantic_validator = SemanticValidator(validation_error_holder=holder)

                crdg = CombinedRawDatasetsGenerator(
                    initial_location=self._location,
                    semantic_validator=semantic_validator,
                    database=db,
                    parsing_config=self._parsing_config,
                )
                crd = crdg.combined_raw_datasets

                DatabaseFilterProcessor(db, crd.raw_datasets).apply_filters()
                LifecycleValidator(RequirementsRepository(db))

                self._db = db
                self._repo = RequirementsRepository(db)
                self._urn_source_paths = dict(crd.urn_source_paths)
                self._fingerprint = crd.fingerprint
                self._initial_urn = crd.initial_model_urn
                self._built_at = datetime.now(timezone.utc).isoformat()
                self._ready = True
                logger.info("Built project session for %s", self._location)
            except SystemExit as e:
                logger.warning("build() called sys.exit(%s) for %s", e.code, self._location)
                self._error = f"Pipeline error (exit code {e.code})"
                db.close()
                self._fingerprint = self.__fingerprint_after_failure(previous_fingerprint)
            except Exception as e:
                logger.error("Failed to build project session for %s: %s", self._location, e)
                self._error = str(e)
                db.close()
                self._fingerprint = self.__fingerprint_after_failure(previous_fingerprint)

    @staticmethod
    def __fingerprint_after_failure(previous: SnapshotFingerprint | None) -> SnapshotFingerprint | None:
        """Keep watching the inputs we knew about, stamped as they are now.

        Without this a working tree that fails to parse — a half-written YAML file, say —
        would be re-parsed on every single request until it is fixed.
        """
        return previous.restamped() if previous is not None else None

    def rebuild(self) -> None:
        self.build()

    def ensure_fresh(self) -> bool:
        """Rebuild if the local input files no longer match the loaded snapshot.

        Returns True if a rebuild happened. Raises SnapshotReloadError if the session
        cannot serve a snapshot that matches disk — answering from a snapshot known to be
        superseded is what this whole mechanism exists to prevent.
        """
        with self._lock:
            if self._fingerprint is not None:
                stale_reasons = self._fingerprint.stale_reasons(limit=5)
                if not stale_reasons:
                    if self._ready:
                        return False
                    raise SnapshotReloadError(f"reqstool project is not loaded: {self._error}")
                logger.info("Reloading snapshot for %s: %s", self._location, "; ".join(stale_reasons))

            self.build()

            if not self._ready:
                raise SnapshotReloadError(f"reqstool project sources changed but reloading them failed: {self._error}")

            return True

    def close(self) -> None:
        with self._lock:
            if self._db is not None:
                self._db.close()
                self._db = None
            self._repo = None
            self._urn_source_paths = {}
            self._fingerprint = None
            self._built_at = None
            self._initial_urn = None
            self._ready = False
