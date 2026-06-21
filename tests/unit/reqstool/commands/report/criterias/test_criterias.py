# Copyright © LFV

from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.commands.report.criterias.group_by import GroupbyOptions, GroupByOrganizor
from reqstool.commands.report.criterias.sort_by import SortByOptions
from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.local_location import LocalLocation
from reqstool.model_generators.combined_raw_datasets_generator import CombinedRawDatasetsGenerator
from reqstool.storage.database import RequirementsDatabase
from reqstool.storage.requirements_repository import RequirementsRepository


@SVCs("SVC_REPORT_0003", "SVC_REPORT_0004")
def test_basic_baseline(local_testdata_resources_rootdir_w_path):
    db = RequirementsDatabase()
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    CombinedRawDatasetsGenerator(
        initial_location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_basic/baseline/ms-101")),
        semantic_validator=semantic_validator,
        database=db,
    )
    repo = RequirementsRepository(db)

    # REPORT_0003: all requirements come from the initial dataset, so INITIAL_IMPORTS grouping
    # puts them all into a single "Initial URN (...)" group.
    gbc_initial = GroupByOrganizor(
        repo=repo,
        group_by=GroupbyOptions.INITIAL_IMPORTS,
        sort_by=[SortByOptions.ID, SortByOptions.REVISION, SortByOptions.SIGNIFICANCE],
    )
    initial_groups = dict(gbc_initial)
    assert set(initial_groups.keys()) == {f"Initial URN ({repo.get_initial_urn()})"}

    # REPORT_0004: within the group, requirements are sorted by id.
    ordered_ids = [urn_id.id for urn_id in next(iter(initial_groups.values()))]
    assert ordered_ids == ["REQ_101", "REQ_102", "REQ_201", "REQ_202"]

    # REPORT_0003: CATEGORY grouping buckets requirements by their first stored category
    # (categories are read back from the database in alphabetical order).
    gbc_category = GroupByOrganizor(
        repo=repo,
        group_by=GroupbyOptions.CATEGORY,
        sort_by=[SortByOptions.ID],
    )
    category_groups = {key: [urn_id.id for urn_id in value] for key, value in gbc_category}
    assert category_groups == {
        "functional-suitability": ["REQ_101", "REQ_201"],
        "maintainability": ["REQ_102"],
        "reliability": ["REQ_202"],
    }

    db.close()
