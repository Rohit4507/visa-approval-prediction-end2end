from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import yaml

from us_visa.exception import USvisaException
from us_visa.utils.model_factory import BestModelDetail, ModelFactory


@pytest.fixture
def dataset() -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(3)
    x = rng.normal(size=(120, 4))
    y = (x[:, 0] + x[:, 1] > 0).astype(int)
    return x, y


@pytest.fixture
def fast_config(tmp_path: Path) -> str:
    """A minimal version of config/model.yaml with tiny, fast search spaces."""
    config = {
        "grid_search": {
            "class": "GridSearchCV",
            "module": "sklearn.model_selection",
            "params": {"cv": 2, "verbose": 0},
        },
        "model_selection": {
            "module_0": {
                "class": "DecisionTreeClassifier",
                "module": "sklearn.tree",
                "params": {"random_state": 0},
                "search_param_grid": {"max_depth": [2, 4]},
            },
            "module_1": {
                "class": "LogisticRegression",
                "module": "sklearn.linear_model",
                "params": {"max_iter": 200},
                "search_param_grid": {"C": [0.1, 1.0]},
            },
        },
    }
    file_path = tmp_path / "model.yaml"
    file_path.write_text(yaml.safe_dump(config))
    return str(file_path)


def test_get_best_model_returns_leaderboard(
    fast_config: str, dataset: tuple[np.ndarray, np.ndarray]
) -> None:
    x_train, y_train = dataset

    detail = ModelFactory(model_config_path=fast_config).get_best_model(
        X=x_train, y=y_train, base_accuracy=0.6
    )

    assert isinstance(detail, BestModelDetail)
    assert set(detail.model_report) == {
        "sklearn.tree.DecisionTreeClassifier",
        "sklearn.linear_model.LogisticRegression",
    }
    assert detail.best_score == max(detail.model_report.values())
    assert hasattr(detail.best_model, "predict")
    assert 0.0 <= detail.best_score <= 1.0


def test_best_model_is_fitted_and_predicts(
    fast_config: str, dataset: tuple[np.ndarray, np.ndarray]
) -> None:
    x_train, y_train = dataset
    detail = ModelFactory(model_config_path=fast_config).get_best_model(X=x_train, y=y_train)

    predictions = detail.best_model.predict(x_train)

    assert predictions.shape == y_train.shape
    assert set(np.unique(predictions)).issubset({0, 1})


def test_low_score_is_only_a_warning(
    fast_config: str, dataset: tuple[np.ndarray, np.ndarray]
) -> None:
    x_train, y_train = dataset

    detail = ModelFactory(model_config_path=fast_config).get_best_model(
        X=x_train, y=y_train, base_accuracy=0.999
    )

    assert detail.best_score < 0.999, "unreachable threshold must not raise, the caller decides"


def test_config_missing_required_blocks_raises(
    tmp_path: Path, dataset: tuple[np.ndarray, np.ndarray]
) -> None:
    file_path = tmp_path / "broken.yaml"
    file_path.write_text(yaml.safe_dump({"grid_search": {}}))

    with pytest.raises(USvisaException):
        ModelFactory(model_config_path=str(file_path))


def test_empty_model_selection_raises(
    tmp_path: Path, dataset: tuple[np.ndarray, np.ndarray]
) -> None:
    file_path = tmp_path / "empty.yaml"
    file_path.write_text(
        yaml.safe_dump(
            {
                "grid_search": {
                    "class": "GridSearchCV",
                    "module": "sklearn.model_selection",
                    "params": {"cv": 2},
                },
                "model_selection": {},
            }
        )
    )
    x_train, y_train = dataset

    with pytest.raises(USvisaException):
        ModelFactory(model_config_path=str(file_path)).get_best_model(X=x_train, y=y_train)
