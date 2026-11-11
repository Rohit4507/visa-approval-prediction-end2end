from __future__ import annotations

import logging as stdlib_logging

from us_visa import constants
from us_visa.logger import LOG_DIR, LOG_FILE, LOG_FILE_PATH
from us_visa.logger import logging as project_logging


def test_storage_constants_are_defined() -> None:
    assert constants.DATABASE_NAME == "US_VISA"
    assert constants.COLLECTION_NAME == "visa_data"
    assert constants.DATA_INGESTION_COLLECTION_NAME == constants.COLLECTION_NAME


def test_target_and_artifact_names() -> None:
    assert constants.TARGET_COLUMN == "case_status"
    assert constants.PIPELINE_NAME == "usvisa"
    assert constants.ARTIFACT_DIR == "artifact"
    assert constants.MODEL_FILE_NAME.endswith(".pkl")
    assert constants.SCHEMA_FILE_PATH.replace("\\", "/") == "config/schema.yaml"


def test_model_registry_defaults() -> None:
    # The bucket is environment-driven, so only assert that it is resolved.
    assert constants.MODEL_BUCKET_NAME
    assert constants.MODEL_PUSHER_S3_KEY == "model-registry"
    assert constants.MODEL_EVALUATION_CHANGED_THRESHOLD_SCORE > 0


def test_serving_configuration() -> None:
    assert constants.APP_HOST == "0.0.0.0"
    assert constants.APP_PORT == 8080


def test_logger_targets_project_logs_directory() -> None:
    assert LOG_DIR.is_dir()
    assert LOG_FILE.endswith(".log")
    assert LOG_FILE_PATH.parent == LOG_DIR


def test_logger_has_file_handler() -> None:
    project_logging.warning("logger smoke test")

    handlers = project_logging.getLogger().handlers
    assert handlers, "root logger should be configured by us_visa.logger"
    assert any(isinstance(handler, stdlib_logging.FileHandler) for handler in handlers)
