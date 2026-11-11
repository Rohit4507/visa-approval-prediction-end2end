import os
import sys
from typing import Any, cast

import joblib
import numpy as np
import yaml
from numpy.typing import NDArray
from pandas import DataFrame

from us_visa.exception import USvisaException
from us_visa.logger import logging


def read_yaml_file(file_path: str) -> dict[str, Any]:
    """Read a YAML file and return its content as a dictionary."""
    try:
        with open(file_path, "rb") as yaml_file:
            content = yaml.safe_load(yaml_file)
        if not isinstance(content, dict):
            raise TypeError(f"Expected a mapping at the top level of {file_path}")
        return content

    except Exception as e:
        raise USvisaException(e, sys) from e


def write_yaml_file(file_path: str, content: object, replace: bool = False) -> None:
    """Write ``content`` to a YAML file, creating parent directories as needed."""
    try:
        if replace and os.path.exists(file_path):
            os.remove(file_path)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as file:
            yaml.dump(content, file)
    except Exception as e:
        raise USvisaException(e, sys) from e


def load_object(file_path: str) -> Any:
    """Load a serialized Python object (joblib format)."""
    logging.info("Entered the load_object method of utils")

    try:
        obj = joblib.load(file_path)

        logging.info("Exited the load_object method of utils")

        return obj

    except Exception as e:
        raise USvisaException(e, sys) from e


def save_numpy_array_data(file_path: str, array: NDArray[Any]) -> None:
    """Save a numpy array to ``file_path`` (.npy format)."""
    try:
        dir_path = os.path.dirname(file_path)
        os.makedirs(dir_path, exist_ok=True)
        with open(file_path, "wb") as file_obj:
            np.save(file_obj, array)
    except Exception as e:
        raise USvisaException(e, sys) from e


def load_numpy_array_data(file_path: str) -> NDArray[Any]:
    """Load a numpy array saved with :func:`save_numpy_array_data`."""
    try:
        with open(file_path, "rb") as file_obj:
            return cast(NDArray[Any], np.load(file_obj))
    except Exception as e:
        raise USvisaException(e, sys) from e


def save_object(file_path: str, obj: object) -> None:
    """Serialize ``obj`` to ``file_path`` with joblib."""
    logging.info("Entered the save_object method of utils")

    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        joblib.dump(obj, file_path)

        logging.info("Exited the save_object method of utils")

    except Exception as e:
        raise USvisaException(e, sys) from e


def drop_columns(df: DataFrame, cols: list[str]) -> DataFrame:
    """Return ``df`` without the columns listed in ``cols``."""
    logging.info("Entered drop_columns method of utils")

    try:
        df = df.drop(columns=cols)

        logging.info("Exited the drop_columns method of utils")

        return df
    except Exception as e:
        raise USvisaException(e, sys) from e
