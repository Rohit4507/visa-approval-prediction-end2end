from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from us_visa.entity.estimator import TargetValueMapping, USvisaModel
from us_visa.exception import USvisaException

FEATURES = ["continent", "no_of_employees"]


@pytest.fixture
def trained_model(visa_frame: pd.DataFrame) -> USvisaModel:
    x = visa_frame[FEATURES]
    y = (visa_frame["case_status"] == "Certified").astype(int)

    preprocessing = ColumnTransformer(
        [
            ("numeric", StandardScaler(), ["no_of_employees"]),
            ("categorical", OneHotEncoder(handle_unknown="ignore"), ["continent"]),
        ]
    )
    preprocessing.fit(x)

    model = LogisticRegression(max_iter=200).fit(preprocessing.transform(x), y)

    return USvisaModel(preprocessing_object=preprocessing, trained_model_object=model)


def test_target_value_mapping_reverses() -> None:
    mapping = TargetValueMapping()

    assert mapping._asdict() == {"Certified": 0, "Denied": 1}
    assert mapping.reverse_mapping() == {0: "Certified", 1: "Denied"}


def test_usvisa_model_predicts_on_raw_input(
    trained_model: USvisaModel, visa_frame: pd.DataFrame
) -> None:
    predictions = trained_model.predict(visa_frame[FEATURES].head(10))

    assert predictions.shape == (10,)
    assert set(np.unique(predictions)).issubset({0, 1})


def test_usvisa_model_handles_unseen_category(trained_model: USvisaModel) -> None:
    unseen = pd.DataFrame({"continent": ["Antarctica"], "no_of_employees": [1234]})

    assert trained_model.predict(unseen).shape == (1,)


def test_usvisa_model_repr_uses_estimator_name(trained_model: USvisaModel) -> None:
    assert repr(trained_model) == "LogisticRegression()"
    assert str(trained_model) == "LogisticRegression()"


def test_usvisa_model_wraps_errors(visa_frame: pd.DataFrame) -> None:
    broken = USvisaModel(preprocessing_object=None, trained_model_object="not-a-model")

    with pytest.raises(USvisaException):
        broken.predict(visa_frame[FEATURES])
