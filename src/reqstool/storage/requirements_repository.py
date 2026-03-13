# Copyright © LFV

from __future__ import annotations

from packaging.version import Version

from reqstool.common.models.lifecycle import LIFECYCLESTATE, LifecycleData
from reqstool.common.models.urn_id import UrnId
from reqstool.models.annotations import AnnotationData
from reqstool.models.mvrs import MVRData
from reqstool.models.requirements import (
    CATEGORIES,
    IMPLEMENTATION,
    SIGNIFICANCETYPES,
    ReferenceData,
    RequirementData,
)
from reqstool.models.svcs import VERIFICATIONTYPES, SVCData
from reqstool.models.test_data import TEST_RUN_STATUS, TestData
from reqstool.storage.database import RequirementsDatabase


class RequirementsRepository:
    def __init__(self, db: RequirementsDatabase):
        self._db = db

    # -- Metadata queries --

    def get_initial_urn(self) -> str:
        return self._db.get_metadata("initial_urn")

    def get_urn_parsing_order(self) -> list[str]:
        rows = self._db.connection.execute("SELECT urn FROM urn_metadata ORDER BY parse_position").fetchall()
        return [row["urn"] for row in rows]

    def get_import_graph(self) -> dict[str, list[str]]:
        graph: dict[str, list[str]] = {}
        all_urns = {row["urn"] for row in self._db.connection.execute("SELECT urn FROM urn_metadata").fetchall()}
        for urn in all_urns:
            graph[urn] = []
        rows = self._db.connection.execute("SELECT parent_urn, child_urn FROM parsing_graph").fetchall()
        for row in rows:
            graph.setdefault(row["parent_urn"], []).append(row["child_urn"])
        return graph

    def is_filtered(self) -> bool:
        return self._db.get_metadata("filtered") == "true"

    # -- Entity queries --

    def get_all_requirements(self) -> dict[UrnId, RequirementData]:
        rows = self._db.connection.execute("SELECT * FROM requirements").fetchall()
        result = {}
        for row in rows:
            urn_id = UrnId(urn=row["urn"], id=row["id"])
            result[urn_id] = self._row_to_requirement_data(row)
        return result

    def get_all_svcs(self) -> dict[UrnId, SVCData]:
        rows = self._db.connection.execute("SELECT * FROM svcs").fetchall()
        result = {}
        for row in rows:
            urn_id = UrnId(urn=row["urn"], id=row["id"])
            result[urn_id] = self._row_to_svc_data(row)
        return result

    def get_all_mvrs(self) -> dict[UrnId, MVRData]:
        rows = self._db.connection.execute("SELECT * FROM mvrs").fetchall()
        result = {}
        for row in rows:
            urn_id = UrnId(urn=row["urn"], id=row["id"])
            result[urn_id] = self._row_to_mvr_data(row)
        return result

    # -- Index/lookup queries --

    def get_svcs_for_req(self, req_urn_id: UrnId) -> list[UrnId]:
        rows = self._db.connection.execute(
            "SELECT svc_urn, svc_id FROM svc_requirement_links WHERE req_urn = ? AND req_id = ?",
            (req_urn_id.urn, req_urn_id.id),
        ).fetchall()
        return [UrnId(urn=row["svc_urn"], id=row["svc_id"]) for row in rows]

    def get_mvrs_for_svc(self, svc_urn_id: UrnId) -> list[UrnId]:
        rows = self._db.connection.execute(
            "SELECT mvr_urn, mvr_id FROM mvr_svc_links WHERE svc_urn = ? AND svc_id = ?",
            (svc_urn_id.urn, svc_urn_id.id),
        ).fetchall()
        return [UrnId(urn=row["mvr_urn"], id=row["mvr_id"]) for row in rows]

    def get_annotations_impls(self) -> dict[UrnId, list[AnnotationData]]:
        rows = self._db.connection.execute(
            "SELECT req_urn, req_id, element_kind, fqn FROM annotations_impls"
        ).fetchall()
        result: dict[UrnId, list[AnnotationData]] = {}
        for row in rows:
            key = UrnId(urn=row["req_urn"], id=row["req_id"])
            annotation = AnnotationData(element_kind=row["element_kind"], fully_qualified_name=row["fqn"])
            result.setdefault(key, []).append(annotation)
        return result

    def get_annotations_tests(self) -> dict[UrnId, list[AnnotationData]]:
        rows = self._db.connection.execute(
            "SELECT svc_urn, svc_id, element_kind, fqn FROM annotations_tests"
        ).fetchall()
        result: dict[UrnId, list[AnnotationData]] = {}
        for row in rows:
            key = UrnId(urn=row["svc_urn"], id=row["svc_id"])
            annotation = AnnotationData(element_kind=row["element_kind"], fully_qualified_name=row["fqn"])
            result.setdefault(key, []).append(annotation)
        return result

    def get_annotations_impls_for_req(self, req_urn_id: UrnId) -> list[AnnotationData]:
        rows = self._db.connection.execute(
            "SELECT element_kind, fqn FROM annotations_impls WHERE req_urn = ? AND req_id = ?",
            (req_urn_id.urn, req_urn_id.id),
        ).fetchall()
        return [AnnotationData(element_kind=row["element_kind"], fully_qualified_name=row["fqn"]) for row in rows]

    def get_annotations_tests_for_svc(self, svc_urn_id: UrnId) -> list[AnnotationData]:
        rows = self._db.connection.execute(
            "SELECT element_kind, fqn FROM annotations_tests WHERE svc_urn = ? AND svc_id = ?",
            (svc_urn_id.urn, svc_urn_id.id),
        ).fetchall()
        return [AnnotationData(element_kind=row["element_kind"], fully_qualified_name=row["fqn"]) for row in rows]

    # -- Test result resolution --

    def get_automated_test_results(self) -> dict[UrnId, list[TestData]]:
        """Replaces CombinedIndexedDatasetGenerator.__process_automated_test_result.

        For each test annotation:
          - CLASS annotations: find all test_results with fqn starting with annotation.fqn + '.'
            Aggregate: all passed → PASSED, any not passed → FAILED, none found → MISSING
          - METHOD annotations: find exact test_result match, else MISSING
        """
        annotations = self._db.connection.execute(
            "SELECT svc_urn, svc_id, element_kind, fqn FROM annotations_tests"
        ).fetchall()

        result: dict[UrnId, list[TestData]] = {}

        for ann in annotations:
            test_urn_id = UrnId(urn=ann["svc_urn"], id=ann["fqn"])

            if ann["element_kind"] == "CLASS":
                test_data = self._process_class_annotated_test_results(ann["svc_urn"], ann["fqn"])
            else:
                # METHOD or other — look for exact match in any URN
                test_result_row = self._db.connection.execute(
                    "SELECT fqn, status FROM test_results WHERE fqn = ?",
                    (ann["fqn"],),
                ).fetchone()

                if test_result_row is not None:
                    test_data = TestData(
                        fully_qualified_name=test_result_row["fqn"],
                        status=TEST_RUN_STATUS(test_result_row["status"]),
                    )
                else:
                    test_data = TestData(
                        fully_qualified_name=ann["fqn"],
                        status=TEST_RUN_STATUS.MISSING,
                    )

            result.setdefault(test_urn_id, []).append(test_data)

        return result

    def _process_class_annotated_test_results(self, urn: str, fqn: str) -> TestData:
        """Replaces CombinedIndexedDatasetGenerator.__process_class_annotated_test_results."""
        rows = self._db.connection.execute(
            "SELECT status FROM test_results WHERE fqn LIKE ? || '.%'",
            (fqn,),
        ).fetchall()

        # Also check for exact match (fqn == test_result.fqn, matching the original `if fqn in urn_id.id` logic)
        exact_rows = self._db.connection.execute(
            "SELECT status FROM test_results WHERE fqn = ?",
            (fqn,),
        ).fetchall()

        all_statuses = [TEST_RUN_STATUS(row["status"]) for row in rows] + [
            TEST_RUN_STATUS(row["status"]) for row in exact_rows
        ]

        if not all_statuses:
            return TestData(fully_qualified_name=fqn, status=TEST_RUN_STATUS.MISSING)
        elif all(s == TEST_RUN_STATUS.PASSED for s in all_statuses):
            return TestData(fully_qualified_name=fqn, status=TEST_RUN_STATUS.PASSED)
        else:
            return TestData(fully_qualified_name=fqn, status=TEST_RUN_STATUS.FAILED)

    # -- Private helpers --

    def _row_to_requirement_data(self, row) -> RequirementData:
        urn = row["urn"]
        req_id = row["id"]

        categories = [
            CATEGORIES(r["category"])
            for r in self._db.connection.execute(
                "SELECT category FROM requirement_categories WHERE req_urn = ? AND req_id = ?",
                (urn, req_id),
            ).fetchall()
        ]

        ref_rows = self._db.connection.execute(
            "SELECT ref_req_urn, ref_req_id FROM requirement_references WHERE req_urn = ? AND req_id = ?",
            (urn, req_id),
        ).fetchall()

        references = []
        if ref_rows:
            ref_ids = {UrnId(urn=r["ref_req_urn"], id=r["ref_req_id"]) for r in ref_rows}
            references.append(ReferenceData(requirement_ids=ref_ids))

        lifecycle = LifecycleData(
            state=LIFECYCLESTATE(row["lifecycle_state"]),
            reason=row["lifecycle_reason"],
        )

        return RequirementData(
            id=UrnId(urn=urn, id=req_id),
            title=row["title"],
            significance=SIGNIFICANCETYPES(row["significance"]),
            description=row["description"],
            rationale=row["rationale"],
            revision=Version(row["revision"]),
            lifecycle=lifecycle,
            implementation=IMPLEMENTATION(row["implementation"]),
            categories=categories,
            references=references if references else [],
        )

    def _row_to_svc_data(self, row) -> SVCData:
        urn = row["urn"]
        svc_id = row["id"]

        req_link_rows = self._db.connection.execute(
            "SELECT req_urn, req_id FROM svc_requirement_links WHERE svc_urn = ? AND svc_id = ?",
            (urn, svc_id),
        ).fetchall()
        requirement_ids = [UrnId(urn=r["req_urn"], id=r["req_id"]) for r in req_link_rows]

        lifecycle = LifecycleData(
            state=LIFECYCLESTATE(row["lifecycle_state"]),
            reason=row["lifecycle_reason"],
        )

        return SVCData(
            id=UrnId(urn=urn, id=svc_id),
            title=row["title"],
            description=row["description"],
            verification=VERIFICATIONTYPES(row["verification_type"]),
            instructions=row["instructions"],
            revision=Version(row["revision"]),
            lifecycle=lifecycle,
            requirement_ids=requirement_ids,
        )

    def _row_to_mvr_data(self, row) -> MVRData:
        urn = row["urn"]
        mvr_id = row["id"]

        svc_link_rows = self._db.connection.execute(
            "SELECT svc_urn, svc_id FROM mvr_svc_links WHERE mvr_urn = ? AND mvr_id = ?",
            (urn, mvr_id),
        ).fetchall()
        svc_ids = [UrnId(urn=r["svc_urn"], id=r["svc_id"]) for r in svc_link_rows]

        return MVRData(
            id=UrnId(urn=urn, id=mvr_id),
            comment=row["comment"],
            passed=bool(row["passed"]),
            svc_ids=svc_ids,
        )
