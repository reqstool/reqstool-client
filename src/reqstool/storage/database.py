# Copyright © LFV


import logging
import sqlite3

from reqstool.common.models.urn_id import UrnId
from reqstool.models.annotations import AnnotationData
from reqstool.models.mvrs import MVRData
from reqstool.models.requirements import MetaData, RequirementData
from reqstool.models.svcs import SVCData
from reqstool.models.test_data import TEST_RUN_STATUS
from reqstool.storage.authorizer import authorizer
from reqstool.storage.el_to_sql_compiler import regexp_function
from reqstool.storage.schema import SCHEMA_DDL

logger = logging.getLogger(__name__)


class RequirementsDatabase:
    def __init__(self):
        self._conn = sqlite3.connect(":memory:")
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA_DDL)
        self._conn.set_authorizer(authorizer)
        self._conn.create_function("regexp", 2, regexp_function)
        self._next_parse_position = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    @property
    def connection(self) -> sqlite3.Connection:
        return self._conn

    def close(self):
        self._conn.close()

    def commit(self):
        self._conn.commit()

    # -- Insert API --

    def insert_requirement(self, urn: str, req: RequirementData) -> None:
        self._conn.execute(
            "INSERT INTO requirements (urn, id, title, significance, lifecycle_state, lifecycle_reason,"
            " implementation, description, rationale, revision)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                urn,
                req.id.id,
                req.title,
                req.significance.value,
                req.lifecycle.state.value,
                req.lifecycle.reason,
                req.implementation.value,
                req.description,
                req.rationale,
                str(req.revision),
            ),
        )

        for cat in req.categories:
            self._conn.execute(
                "INSERT INTO requirement_categories (req_urn, req_id, category) VALUES (?, ?, ?)",
                (urn, req.id.id, cat.value),
            )

        if req.references:
            for ref in req.references:
                for ref_urn_id in ref.requirement_ids:
                    self._conn.execute(
                        "INSERT OR IGNORE INTO requirement_references"
                        " (req_urn, req_id, ref_req_urn, ref_req_id) VALUES (?, ?, ?, ?)",
                        (urn, req.id.id, ref_urn_id.urn, ref_urn_id.id),
                    )

    def insert_svc(self, urn: str, svc: SVCData) -> None:
        self._conn.execute(
            "INSERT INTO svcs (urn, id, title, verification_type, lifecycle_state, lifecycle_reason,"
            " description, instructions, revision)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                urn,
                svc.id.id,
                svc.title,
                svc.verification.value,
                svc.lifecycle.state.value,
                svc.lifecycle.reason,
                svc.description,
                svc.instructions,
                str(svc.revision),
            ),
        )

        for req_urn_id in svc.requirement_ids:
            try:
                self._conn.execute(
                    "INSERT INTO svc_requirement_links (svc_urn, svc_id, req_urn, req_id) VALUES (?, ?, ?, ?)",
                    (urn, svc.id.id, req_urn_id.urn, req_urn_id.id),
                )
            except sqlite3.IntegrityError:
                logger.warning("SVC %s:%s references non-existent requirement %s", urn, svc.id.id, req_urn_id)

    def insert_mvr(self, urn: str, mvr: MVRData) -> None:
        self._conn.execute(
            "INSERT INTO mvrs (urn, id, passed, comment) VALUES (?, ?, ?, ?)",
            (urn, mvr.id.id, int(mvr.passed), mvr.comment),
        )

        for svc_urn_id in mvr.svc_ids:
            try:
                self._conn.execute(
                    "INSERT INTO mvr_svc_links (mvr_urn, mvr_id, svc_urn, svc_id) VALUES (?, ?, ?, ?)",
                    (urn, mvr.id.id, svc_urn_id.urn, svc_urn_id.id),
                )
            except sqlite3.IntegrityError:
                logger.warning("MVR %s:%s references non-existent SVC %s", urn, mvr.id.id, svc_urn_id)

    def insert_annotation_impl(self, req_urn_id: UrnId, annotation: AnnotationData) -> None:
        try:
            self._conn.execute(
                "INSERT OR IGNORE INTO annotations_impls (req_urn, req_id, element_kind, fqn) VALUES (?, ?, ?, ?)",
                (req_urn_id.urn, req_urn_id.id, annotation.element_kind, annotation.fully_qualified_name),
            )
        except sqlite3.IntegrityError:
            logger.warning("Annotation impl references non-existent requirement %s", req_urn_id)

    def insert_annotation_test(self, svc_urn_id: UrnId, annotation: AnnotationData) -> None:
        try:
            self._conn.execute(
                "INSERT OR IGNORE INTO annotations_tests (svc_urn, svc_id, element_kind, fqn) VALUES (?, ?, ?, ?)",
                (svc_urn_id.urn, svc_urn_id.id, annotation.element_kind, annotation.fully_qualified_name),
            )
        except sqlite3.IntegrityError:
            logger.warning("Annotation test references non-existent SVC %s", svc_urn_id)

    def insert_test_result(self, urn: str, fqn: str, status: TEST_RUN_STATUS) -> None:
        self._conn.execute(
            "INSERT INTO test_results (urn, fqn, status) VALUES (?, ?, ?)",
            (urn, fqn, status.value),
        )

    def insert_parsing_graph_edge(self, parent_urn: str, child_urn: str, edge_type: str) -> None:
        self._conn.execute(
            "INSERT OR IGNORE INTO parsing_graph (parent_urn, child_urn, edge_type) VALUES (?, ?, ?)",
            (parent_urn, child_urn, edge_type),
        )

    def insert_urn_metadata(
        self,
        metadata: MetaData,
        location_type: str | None = None,
        location_uri: str | None = None,
    ) -> None:
        self._conn.execute(
            "INSERT INTO urn_metadata (urn, variant, title, url, parse_position, location_type, location_uri)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                metadata.urn,
                metadata.variant.value if metadata.variant else None,
                metadata.title,
                metadata.url,
                self._next_parse_position,
                location_type,
                location_uri,
            ),
        )
        self._next_parse_position += 1

    # -- Metadata --

    def set_metadata(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            (key, value),
        )

    def get_metadata(self, key: str) -> str | None:
        row = self._conn.execute("SELECT value FROM metadata WHERE key = ?", (key,)).fetchone()
        return row["value"] if row is not None else None
