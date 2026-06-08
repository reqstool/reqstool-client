# Copyright © LFV

from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.commands.validate.validate import ValidateCommand
from reqstool.locations.local_location import LocalLocation


@SVCs("SVC_VALIDATE_0001")
def test_validate_warns_on_missing_mvr(local_testdata_resources_rootdir_w_path):
    result = ValidateCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001"))
    )
    assert "⚠" in result.result
    assert "no MVR defined" in result.result


@SVCs("SVC_VALIDATE_0001")
def test_validate_exit_code_zero_without_strict(local_testdata_resources_rootdir_w_path):
    result = ValidateCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001"))
    )
    assert result.exit_code == 0


@SVCs("SVC_VALIDATE_0001")
def test_validate_exit_code_one_with_strict(local_testdata_resources_rootdir_w_path):
    result = ValidateCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        strict=True,
    )
    assert result.exit_code == 1


@SVCs("SVC_VALIDATE_0001")
def test_validate_shows_initial_urn(local_testdata_resources_rootdir_w_path):
    result = ValidateCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001"))
    )
    assert "ms-001" in result.result


@SVCs("SVC_VALIDATE_0001")
def test_validate_pass_on_complete_dataset(local_testdata_resources_rootdir_w_path):
    result = ValidateCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_basic/baseline/ms-101"))
    )
    assert "✓ All checks passed" in result.result
    assert result.exit_code == 0


@SVCs("SVC_VALIDATE_0001")
def test_validate_strict_with_no_warnings_exits_zero(local_testdata_resources_rootdir_w_path):
    """--strict on a fully-covered dataset must still exit 0 (no warnings to promote)."""
    result = ValidateCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_basic/baseline/ms-101")),
        strict=True,
    )
    assert result.exit_code == 0


@SVCs("SVC_VALIDATE_0001")
def test_validate_referential_errors_cause_exit_one(local_testdata_resources_rootdir_w_path):
    """Referential-integrity errors (broken references detected by SemanticValidator) must
    always produce exit code 1 and be prefixed with ✗ in the output."""
    result = ValidateCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/empty_ms/ms-001"))
    )
    assert result.exit_code == 1
    assert "✗" in result.result
