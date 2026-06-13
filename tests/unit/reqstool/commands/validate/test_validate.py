# Copyright © LFV

from unittest.mock import MagicMock

from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.commands.validate.validate import ValidateCommand
from reqstool.common.models.urn_id import UrnId
from reqstool.locations.local_location import LocalLocation


@SVCs("SVC_VALIDATE_0001")
def test_validate_reports_requirement_without_svc():
    """VALIDATE_0001: a requirement with no SVC is reported as a coverage gap."""
    repo = MagicMock()
    uid = UrnId(urn="proj", id="REQ_NO_SVC")
    repo.get_all_requirements.return_value = {uid: object()}
    repo.get_svcs_for_req.return_value = []
    repo.get_all_svcs.return_value = {}
    warnings = ValidateCommand._check_coverage(MagicMock(), repo)
    assert any("no SVC defined" in w for w in warnings)
    assert any("REQ_NO_SVC" in w for w in warnings)


@SVCs("SVC_VALIDATE_0002")
def test_validate_warns_on_missing_mvr(local_testdata_resources_rootdir_w_path):
    result = ValidateCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001"))
    )
    assert "⚠" in result.result
    assert "no MVR defined" in result.result


@SVCs("SVC_VALIDATE_0004")
def test_validate_exit_code_zero_without_strict(local_testdata_resources_rootdir_w_path):
    result = ValidateCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001"))
    )
    assert result.exit_code == 0


@SVCs("SVC_VALIDATE_0004")
def test_validate_exit_code_one_with_strict(local_testdata_resources_rootdir_w_path):
    result = ValidateCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        strict=True,
    )
    assert result.exit_code == 1


@SVCs("SVC_VALIDATE_0005")
def test_validate_shows_initial_urn(local_testdata_resources_rootdir_w_path):
    result = ValidateCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001"))
    )
    assert "ms-001" in result.result


@SVCs("SVC_VALIDATE_0005")
def test_validate_pass_on_complete_dataset(local_testdata_resources_rootdir_w_path):
    result = ValidateCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_basic/baseline/ms-101"))
    )
    assert "✓ All checks passed" in result.result
    assert result.exit_code == 0


@SVCs("SVC_VALIDATE_0004")
def test_validate_strict_with_no_warnings_exits_zero(local_testdata_resources_rootdir_w_path):
    """--strict on a fully-covered dataset must still exit 0 (no warnings to promote)."""
    result = ValidateCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_basic/baseline/ms-101")),
        strict=True,
    )
    assert result.exit_code == 0


@SVCs("SVC_VALIDATE_0003")
def test_validate_referential_errors_cause_exit_one(local_testdata_resources_rootdir_w_path):
    """Referential-integrity errors (broken references detected by SemanticValidator) must
    always produce exit code 1 and be prefixed with ✗ in the output."""
    result = ValidateCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/empty_ms/ms-001"))
    )
    assert result.exit_code == 1
    assert "✗" in result.result
