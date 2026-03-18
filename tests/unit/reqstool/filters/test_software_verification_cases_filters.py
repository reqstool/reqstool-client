# Copyright © LFV
from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.common.models.urn_id import UrnId
from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.locations.local_location import LocalLocation
from reqstool.storage.pipeline import build_database
from reqstool.storage.requirements_repository import RequirementsRepository


@SVCs("SVC_011", "SVC_012")
def test_include_exclude_for_svcs(local_testdata_resources_rootdir_w_path):
    semantic_validator = SemanticValidator(validation_error_holder=ValidationErrorHolder())
    with build_database(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        semantic_validator=semantic_validator,
    ) as (db, _):
        repo = RequirementsRepository(db)
        svcs = repo.get_all_svcs()

        assert UrnId(urn="sys-001", id="SVC_sys001_500") in svcs
        assert UrnId(urn="sys-001", id="SVC_sys001_600") in svcs
        assert UrnId(urn="sys-001", id="SVC_sys001_000") not in svcs
