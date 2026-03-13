from unittest.mock import MagicMock, patch

import pytest

from reqstool.common.validator_error_holder import ValidationErrorHolder
from reqstool.common.validators.semantic_validator import SemanticValidator
from reqstool.models.raw_datasets import CombinedRawDataset
from reqstool.storage.pipeline import build_database


@pytest.fixture
def mock_location():
    return MagicMock()


@pytest.fixture
def mock_semantic_validator():
    return SemanticValidator(validation_error_holder=ValidationErrorHolder())


@patch("reqstool.storage.pipeline.CombinedRawDatasetsGenerator")
@patch("reqstool.storage.pipeline.DatabaseFilterProcessor")
@patch("reqstool.storage.pipeline.LifecycleValidator")
def test_build_database_returns_db_and_crd(
    mock_lifecycle, mock_filter, mock_crdg, mock_location, mock_semantic_validator
):
    mock_crd = MagicMock(spec=CombinedRawDataset)
    mock_crd.raw_datasets = {}
    mock_crdg.return_value.combined_raw_datasets = mock_crd

    with build_database(location=mock_location, semantic_validator=mock_semantic_validator) as (db, crd):
        assert db is not None
        assert crd is mock_crd


@patch("reqstool.storage.pipeline.CombinedRawDatasetsGenerator")
@patch("reqstool.storage.pipeline.DatabaseFilterProcessor")
@patch("reqstool.storage.pipeline.LifecycleValidator")
def test_build_database_calls_filter_processor(
    mock_lifecycle, mock_filter, mock_crdg, mock_location, mock_semantic_validator
):
    mock_crd = MagicMock(spec=CombinedRawDataset)
    mock_crd.raw_datasets = {}
    mock_crdg.return_value.combined_raw_datasets = mock_crd

    with build_database(location=mock_location, semantic_validator=mock_semantic_validator, filter_data=True) as (
        db,
        _,
    ):
        mock_filter.return_value.apply_filters.assert_called_once()


@patch("reqstool.storage.pipeline.CombinedRawDatasetsGenerator")
@patch("reqstool.storage.pipeline.DatabaseFilterProcessor")
@patch("reqstool.storage.pipeline.LifecycleValidator")
def test_build_database_skips_filter_when_disabled(
    mock_lifecycle, mock_filter, mock_crdg, mock_location, mock_semantic_validator
):
    mock_crd = MagicMock(spec=CombinedRawDataset)
    mock_crd.raw_datasets = {}
    mock_crdg.return_value.combined_raw_datasets = mock_crd

    with build_database(location=mock_location, semantic_validator=mock_semantic_validator, filter_data=False) as (
        db,
        _,
    ):
        mock_filter.assert_not_called()


@patch("reqstool.storage.pipeline.CombinedRawDatasetsGenerator")
@patch("reqstool.storage.pipeline.DatabaseFilterProcessor")
@patch("reqstool.storage.pipeline.LifecycleValidator")
def test_build_database_runs_lifecycle_validator(
    mock_lifecycle, mock_filter, mock_crdg, mock_location, mock_semantic_validator
):
    mock_crd = MagicMock(spec=CombinedRawDataset)
    mock_crd.raw_datasets = {}
    mock_crdg.return_value.combined_raw_datasets = mock_crd

    with build_database(location=mock_location, semantic_validator=mock_semantic_validator) as (db, _):
        mock_lifecycle.assert_called_once()
