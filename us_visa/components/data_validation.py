import json
import sys

import pandas as pd
from evidently import Report
from evidently.presets import DataDriftPreset
from pandas import DataFrame

from us_visa.constants import SCHEMA_FILE_PATH
from us_visa.entity.artifact_entity import DataIngestionArtifact, DataValidationArtifact
from us_visa.entity.config_entity import DataValidationConfig
from us_visa.exception import USvisaException
from us_visa.logger import logging
from us_visa.utils.main_utils import read_yaml_file, write_yaml_file


class DataValidation:
    def __init__(
        self,
        data_ingestion_artifact: DataIngestionArtifact,
        data_validation_config: DataValidationConfig,
    ):
        """
        :param data_ingestion_artifact: Output reference of data ingestion artifact stage
        :param data_validation_config: configuration for data validation
        """
        try:
            self.data_ingestion_artifact = data_ingestion_artifact
            self.data_validation_config = data_validation_config
            self._schema_config = read_yaml_file(file_path=SCHEMA_FILE_PATH)
        except Exception as e:
            raise USvisaException(e, sys) from e

    def validate_number_of_columns(self, dataframe: DataFrame) -> bool:
        """
        Method Name :   validate_number_of_columns
        Description :   This method validates the number of columns

        Output      :   Returns bool value based on validation results
        On Failure  :   Write an exception log and then raise an exception
        """
        try:
            status = len(dataframe.columns) == len(self._schema_config["columns"])
            logging.info(f"Is required column present: [{status}]")
            return status
        except Exception as e:
            raise USvisaException(e, sys) from e

    def is_column_exist(self, df: DataFrame) -> bool:
        """
        Method Name :   is_column_exist
        Description :   This method validates the existence of a numerical and categorical columns

        Output      :   Returns bool value based on validation results
        On Failure  :   Write an exception log and then raise an exception
        """
        try:
            dataframe_columns = df.columns
            missing_numerical_columns = []
            missing_categorical_columns = []
            for column in self._schema_config["numerical_columns"]:
                if column not in dataframe_columns:
                    missing_numerical_columns.append(column)

            if len(missing_numerical_columns) > 0:
                logging.info(f"Missing numerical column: {missing_numerical_columns}")

            for column in self._schema_config["categorical_columns"]:
                if column not in dataframe_columns:
                    missing_categorical_columns.append(column)

            if len(missing_categorical_columns) > 0:
                logging.info(f"Missing categorical column: {missing_categorical_columns}")

            return not (len(missing_categorical_columns) > 0 or len(missing_numerical_columns) > 0)
        except Exception as e:
            raise USvisaException(e, sys) from e

    @staticmethod
    def read_data(file_path) -> DataFrame:
        try:
            return pd.read_csv(file_path)
        except Exception as e:
            raise USvisaException(e, sys) from e

    def detect_dataset_drift(self, reference_df: DataFrame, current_df: DataFrame) -> bool:
        """
        Method Name :   detect_dataset_drift
        Description :   Runs an Evidently data-drift report between the reference
                        (training) and current (test) data and persists it as YAML

        Output      :   True when the share of drifted columns exceeds the preset
                        threshold, False otherwise
        On Failure  :   Write an exception log and then raise an exception
        """
        try:
            report = Report(metrics=[DataDriftPreset()])
            snapshot = report.run(current_data=current_df, reference_data=reference_df)

            # Evidently returns numpy scalars; round-trip through JSON so the
            # report can be dumped to YAML without custom representers.
            metrics = json.loads(json.dumps(snapshot.dict()["metrics"], default=float))

            drifted_columns = next(
                (
                    metric["value"]
                    for metric in metrics
                    if metric["config"]["type"] == "evidently:metric_v2:DriftedColumnsCount"
                ),
                None,
            )

            if drifted_columns is None:  # pragma: no cover - preset always emits this metric
                raise ValueError("DriftedColumnsCount metric missing from the Evidently report.")

            n_features = len(metrics) - 1  # every remaining metric is a per-column drift score
            n_drifted_features = int(drifted_columns["count"])
            drift_share = float(drifted_columns["share"])
            drift_threshold = float(
                next(
                    metric["config"]["drift_share"]
                    for metric in metrics
                    if metric["config"]["type"] == "evidently:metric_v2:DriftedColumnsCount"
                )
            )
            dataset_drift = drift_share > drift_threshold

            write_yaml_file(
                file_path=self.data_validation_config.drift_report_file_path,
                content={
                    "summary": {
                        "n_features": n_features,
                        "n_drifted_features": n_drifted_features,
                        "drift_share": drift_share,
                        "drift_threshold": drift_threshold,
                        "dataset_drift": dataset_drift,
                    },
                    "metrics": metrics,
                },
                replace=True,
            )

            logging.info(
                f"{n_drifted_features}/{n_features} features drifted "
                f"(share={drift_share:.2f}, threshold={drift_threshold:.2f})."
            )
            return dataset_drift
        except Exception as e:
            raise USvisaException(e, sys) from e

    def initiate_data_validation(self) -> DataValidationArtifact:
        """
        Method Name :   initiate_data_validation
        Description :   This method initiates the data validation component for the pipeline

        Output      :   Returns bool value based on validation results
        On Failure  :   Write an exception log and then raise an exception
        """

        try:
            validation_error_msg = ""
            logging.info("Starting data validation")
            train_df, test_df = (
                DataValidation.read_data(file_path=self.data_ingestion_artifact.trained_file_path),
                DataValidation.read_data(file_path=self.data_ingestion_artifact.test_file_path),
            )

            status = self.validate_number_of_columns(dataframe=train_df)
            logging.info(f"All required columns present in training dataframe: {status}")
            if not status:
                validation_error_msg += "Columns are missing in training dataframe."
            status = self.validate_number_of_columns(dataframe=test_df)

            logging.info(f"All required columns present in testing dataframe: {status}")
            if not status:
                validation_error_msg += "Columns are missing in test dataframe."

            status = self.is_column_exist(df=train_df)

            if not status:
                validation_error_msg += "Columns are missing in training dataframe."
            status = self.is_column_exist(df=test_df)

            if not status:
                validation_error_msg += "columns are missing in test dataframe."

            validation_status = len(validation_error_msg) == 0

            if validation_status:
                drift_status = self.detect_dataset_drift(train_df, test_df)
                if drift_status:
                    logging.info("Drift detected.")
                    validation_error_msg = "Drift detected"
                else:
                    validation_error_msg = "Drift not detected"
            else:
                logging.info(f"Validation_error: {validation_error_msg}")

            data_validation_artifact = DataValidationArtifact(
                validation_status=validation_status,
                message=validation_error_msg,
                drift_report_file_path=self.data_validation_config.drift_report_file_path,
            )

            logging.info(f"Data validation artifact: {data_validation_artifact}")
            return data_validation_artifact
        except Exception as e:
            raise USvisaException(e, sys) from e
