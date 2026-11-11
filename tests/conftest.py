from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from us_visa.constants import SCHEMA_FILE_PATH
from us_visa.utils.main_utils import read_yaml_file

NUMERIC_COLUMNS = ["no_of_employees", "yr_of_estab", "prevailing_wage"]
CATEGORICAL_COLUMNS = [
    "continent",
    "education_of_employee",
    "has_job_experience",
    "requires_job_training",
    "region_of_employment",
    "unit_of_wage",
    "full_time_position",
]


@pytest.fixture(scope="session")
def schema() -> dict:
    """The data schema that the validation component enforces."""
    return read_yaml_file(SCHEMA_FILE_PATH)


def make_visa_frame(n_rows: int = 200, seed: int = 7) -> pd.DataFrame:
    """Build a synthetic dataframe that matches ``config/schema.yaml``."""
    rng = np.random.default_rng(seed)

    frame = pd.DataFrame(
        {
            "case_id": np.arange(1, n_rows + 1),
            "continent": rng.choice(["Asia", "Europe", "Africa", "North America"], n_rows),
            "education_of_employee": rng.choice(
                ["High School", "Bachelor's", "Master's", "Doctorate"], n_rows
            ),
            "has_job_experience": rng.choice(["Y", "N"], n_rows),
            "requires_job_training": rng.choice(["Y", "N"], n_rows),
            "no_of_employees": rng.integers(50, 5000, n_rows),
            "yr_of_estab": rng.integers(1990, 2016, n_rows),
            "region_of_employment": rng.choice(["West", "Northeast", "South", "Midwest"], n_rows),
            "prevailing_wage": rng.normal(70_000, 20_000, n_rows),
            "unit_of_wage": rng.choice(["Year", "Hour", "Month", "Week"], n_rows),
            "full_time_position": rng.choice(["Y", "N"], n_rows),
            "case_status": rng.choice(["Certified", "Denied"], n_rows, p=[0.68, 0.32]),
        }
    )
    return frame


@pytest.fixture
def visa_frame() -> pd.DataFrame:
    return make_visa_frame()


@pytest.fixture
def drifted_visa_frame(visa_frame: pd.DataFrame) -> pd.DataFrame:
    """Heavily drifted sample: every numeric column shifts and every categorical
    column collapses to a value the reference data never contains."""
    drifted = visa_frame.copy()
    rng = np.random.default_rng(99)
    rows = len(drifted)

    drifted["no_of_employees"] = rng.integers(500_000, 900_000, rows)
    drifted["prevailing_wage"] = rng.normal(900_000, 5_000, rows)
    drifted["yr_of_estab"] = rng.integers(1900, 1910, rows)
    drifted["continent"] = rng.choice(["Antarctica", "Atlantis"], rows, p=[0.9, 0.1])
    drifted["education_of_employee"] = rng.choice(["Primary School", "None"], rows, p=[0.8, 0.2])
    drifted["region_of_employment"] = rng.choice(["Remote", "Offshore"], rows, p=[0.7, 0.3])
    drifted["unit_of_wage"] = rng.choice(["Decade", "Century"], rows, p=[0.6, 0.4])

    return drifted
