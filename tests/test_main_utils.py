from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from us_visa.exception import USvisaException
from us_visa.utils.main_utils import (
    drop_columns,
    load_numpy_array_data,
    load_object,
    read_yaml_file,
    save_numpy_array_data,
    save_object,
    write_yaml_file,
)


def test_yaml_roundtrip(tmp_path: Path) -> None:
    file_path = tmp_path / "nested" / "config.yaml"
    content = {"model": {"name": "RandomForest", "params": {"n_estimators": 5}}, "list": [1, 2, 3]}

    write_yaml_file(str(file_path), content)

    assert file_path.is_file()
    assert read_yaml_file(str(file_path)) == content


def test_write_yaml_file_replace(tmp_path: Path) -> None:
    file_path = tmp_path / "report.yaml"

    write_yaml_file(str(file_path), {"a": 1})
    write_yaml_file(str(file_path), {"b": 2}, replace=True)

    assert read_yaml_file(str(file_path)) == {"b": 2}


def test_read_yaml_file_rejects_non_mapping(tmp_path: Path) -> None:
    file_path = tmp_path / "list.yaml"
    file_path.write_text("- one\n- two\n")

    with pytest.raises(USvisaException):
        read_yaml_file(str(file_path))


def test_read_yaml_file_missing_path_raises(tmp_path: Path) -> None:
    with pytest.raises(USvisaException):
        read_yaml_file(str(tmp_path / "does-not-exist.yaml"))


def test_object_roundtrip(tmp_path: Path) -> None:
    model = {"weights": np.arange(5), "classes": ["Certified", "Denied"]}
    file_path = tmp_path / "artifacts" / "model.pkl"

    save_object(str(file_path), model)
    loaded = load_object(str(file_path))

    assert loaded["classes"] == ["Certified", "Denied"]
    np.testing.assert_array_equal(loaded["weights"], np.arange(5))


def test_load_object_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(USvisaException):
        load_object(str(tmp_path / "nope.pkl"))


def test_numpy_array_roundtrip(tmp_path: Path) -> None:
    array = np.arange(12, dtype=float).reshape(3, 4)
    file_path = tmp_path / "transformed" / "train.npy"

    save_numpy_array_data(str(file_path), array)
    loaded = load_numpy_array_data(str(file_path))

    np.testing.assert_array_equal(loaded, array)


def test_drop_columns_returns_new_frame(visa_frame: pd.DataFrame) -> None:
    result = drop_columns(visa_frame, ["case_id", "continent"])

    assert "case_id" not in result.columns
    assert "continent" not in result.columns
    assert "case_id" in visa_frame.columns, "input frame must not be mutated"


def test_drop_columns_rejects_unknown_column(visa_frame: pd.DataFrame) -> None:
    with pytest.raises(USvisaException):
        drop_columns(visa_frame, ["not_a_column"])
