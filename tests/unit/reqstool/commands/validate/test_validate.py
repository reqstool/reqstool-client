# Copyright © LFV

from reqstool_python_decorators.decorators.decorators import SVCs

from reqstool.commands.validate.validate import ValidateCommand
from reqstool.locations.local_location import LocalLocation


@SVCs("SVC_021")
def test_validate_warns_on_missing_mvr(local_testdata_resources_rootdir_w_path):
    result = ValidateCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001"))
    )
    assert "⚠" in result.result
    assert "no MVR defined" in result.result


@SVCs("SVC_021")
def test_validate_exit_code_zero_without_strict(local_testdata_resources_rootdir_w_path):
    result = ValidateCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001"))
    )
    assert result.exit_code == 0


@SVCs("SVC_021")
def test_validate_exit_code_one_with_strict(local_testdata_resources_rootdir_w_path):
    result = ValidateCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001")),
        strict=True,
    )
    assert result.exit_code == 1


@SVCs("SVC_021")
def test_validate_shows_initial_urn(local_testdata_resources_rootdir_w_path):
    result = ValidateCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_standard/baseline/ms-001"))
    )
    assert "ms-001" in result.result


@SVCs("SVC_021")
def test_validate_pass_on_complete_dataset(local_testdata_resources_rootdir_w_path):
    result = ValidateCommand(
        location=LocalLocation(path=local_testdata_resources_rootdir_w_path("test_basic/baseline/ms-101"))
    )
    assert "✓ All checks passed" in result.result
    assert result.exit_code == 0
