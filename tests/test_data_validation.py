from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from us_visa.components.data_validation import DataValidation
from us_visa.entity.artifact_entity import DataIngestionArtifact
from us_visa.entity.config_entity import DataValidationConfig
from us_visa.exception import USvisaException
from us_visa.utils.main_utils import read_yaml_file


@pytest.fixture
def validator(tmp_path: Path) -> DataValidation:
    artifact = DataIngestionArtifact(
        trained_file_path=str(tmp_path / "train.csv"),
        test_file_path=str(tmp_path / "test.csv"),
    )
    config = DataValidationConfig()
    config.drift_report_file_path = str(tmp_path / "drift_report" / "report.yaml")

    return DataValidation(data_ingestion_artifact=artifact, data_validation_config=config)


def test_validate_number_of_columns_matches_schema(
    validator: DataValidation, visa_frame: pd.DataFrame
) -> None:
    assert validator.validate_number_of_columns(visa_frame) is True


def test_validate_number_of_columns_detects_extra_column(
    validator: DataValidation, visa_frame: pd.DataFrame
) -> None:
    assert validator.validate_number_of_columns(visa_frame.assign(extra=1)) is False


def test_is_column_exist_with_complete_frame(
    validator: DataValidation, visa_frame: pd.DataFrame
) -> None:
    assert validator.is_column_exist(visa_frame) is True


def test_is_column_exist_detects_missing_numeric_and_categorical(
    validator: DataValidation, visa_frame: pd.DataFrame
) -> None:
    broken = visa_frame.drop(columns=["prevailing_wage", "continent"])

    assert validator.is_column_exist(broken) is False


def test_read_data_roundtrip(
    validator: DataValidation, visa_frame: pd.DataFrame, tmp_path: Path
) -> None:
    file_path = tmp_path / "train.csv"
    visa_frame.to_csv(file_path, index=False)

    loaded = DataValidation.read_data(str(file_path))

    assert loaded.shape == visa_frame.shape


def test_read_data_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(USvisaException):
        DataValidation.read_data(str(tmp_path / "nope.csv"))


def test_detect_dataset_drift_writes_report_and_flags_shift(
    validator: DataValidation,
    visa_frame: pd.DataFrame,
    drifted_visa_frame: pd.DataFrame,
) -> None:
    drifted = validator.detect_dataset_drift(visa_frame, drifted_visa_frame)

    report = read_yaml_file(validator.data_validation_config.drift_report_file_path)
    summary = report["summary"]

    assert drifted is summary["dataset_drift"], "return value must match the persisted report"
    assert drifted is True
    assert summary["n_drifted_features"] >= 6
    assert summary["drift_share"] > summary["drift_threshold"]
    assert report["metrics"], "per-column drift metrics should be persisted"


def test_detect_dataset_drift_on_same_distribution(
    validator: DataValidation, visa_frame: pd.DataFrame
) -> None:
    assert validator.detect_dataset_drift(visa_frame, visa_frame.copy()) is False
