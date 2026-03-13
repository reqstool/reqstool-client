# Copyright © LFV

from reqstool.models.raw_datasets import RawDataset
from reqstool.storage.database import RequirementsDatabase


class DatabasePopulator:
    @staticmethod
    def populate_from_raw_dataset(db: RequirementsDatabase, urn: str, rd: RawDataset) -> None:
        if rd.requirements_data is not None:
            DatabasePopulator._populate_requirements(db, urn, rd)

        if rd.svcs_data is not None:
            DatabasePopulator._populate_svcs(db, urn, rd)

        if rd.mvrs_data is not None:
            DatabasePopulator._populate_mvrs(db, urn, rd)

        if rd.annotations_data is not None:
            DatabasePopulator._populate_annotations(db, rd)

        if rd.automated_tests is not None:
            DatabasePopulator._populate_test_results(db, rd)

    @staticmethod
    def _populate_requirements(db: RequirementsDatabase, urn: str, rd: RawDataset) -> None:
        for req_urn_id, req_data in rd.requirements_data.requirements.items():
            db.insert_requirement(urn, req_data)

    @staticmethod
    def _populate_svcs(db: RequirementsDatabase, urn: str, rd: RawDataset) -> None:
        for svc_urn_id, svc_data in rd.svcs_data.cases.items():
            db.insert_svc(urn, svc_data)

    @staticmethod
    def _populate_mvrs(db: RequirementsDatabase, urn: str, rd: RawDataset) -> None:
        for mvr_urn_id, mvr_data in rd.mvrs_data.results.items():
            db.insert_mvr(urn, mvr_data)

    @staticmethod
    def _populate_annotations(db: RequirementsDatabase, rd: RawDataset) -> None:
        for req_urn_id, annotations in rd.annotations_data.implementations.items():
            for annotation in annotations:
                db.insert_annotation_impl(req_urn_id, annotation)

        for svc_urn_id, annotations in rd.annotations_data.tests.items():
            for annotation in annotations:
                db.insert_annotation_test(svc_urn_id, annotation)

    @staticmethod
    def _populate_test_results(db: RequirementsDatabase, rd: RawDataset) -> None:
        for test_urn_id, test_data in rd.automated_tests.tests.items():
            db.insert_test_result(test_urn_id.urn, test_data.fully_qualified_name, test_data.status)
