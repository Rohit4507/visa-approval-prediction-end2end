"""Config-driven estimator search.

This module replaces the unmaintained ``neuro_mf`` package that earlier releases
of the project depended on. It reads ``config/model.yaml``, instantiates every
estimator declared under ``model_selection`` by importing it dynamically, runs the
configured grid search and reports the best candidate.

Keeping this in ~100 lines of local code means the project installs on current
Python versions without pinning abandoned dependencies, and the search strategy
can be swapped for Optuna later (see ``docs/ROADMAP_2026.md``).
"""

import sys
from dataclasses import dataclass, field
from importlib import import_module
from typing import Any

from numpy.typing import NDArray

from us_visa.exception import USvisaException
from us_visa.logger import logging
from us_visa.utils.main_utils import read_yaml_file


@dataclass(frozen=True)
class BestModelDetail:
    """Outcome of a model search: the winner, its score and the full leaderboard."""

    best_model: Any
    best_score: float
    model_report: dict[str, float] = field(default_factory=dict)


def _load_attribute(module_name: str, attribute_name: str) -> Any:
    """Import ``attribute_name`` from ``module_name``.

    ``config/model.yaml`` stores import paths as strings, so this is the only
    place in the codebase that resolves them.
    """
    try:
        module = import_module(module_name)
    except ImportError as e:  # pragma: no cover - defensive
        raise USvisaException(f"Could not import module '{module_name}'", sys) from e

    try:
        return getattr(module, attribute_name)
    except AttributeError as e:
        raise USvisaException(
            f"Module '{module_name}' has no attribute '{attribute_name}'", sys
        ) from e


class ModelFactory:
    """Run the grid search defined in ``config/model.yaml`` over all candidate models."""

    def __init__(self, model_config_path: str) -> None:
        self.model_config: dict[str, Any] = read_yaml_file(file_path=model_config_path)

        try:
            self.grid_search_config: dict[str, Any] = self.model_config["grid_search"]
            self.model_selection_config: dict[str, Any] = self.model_config["model_selection"]
        except KeyError as e:
            raise USvisaException(
                f"'{model_config_path}' must define 'grid_search' and 'model_selection' blocks: {e}",
                sys,
            ) from e

    def _instantiate(self, config: dict[str, Any]) -> Any:
        estimator_class = _load_attribute(config["module"], config["class"])
        return estimator_class(**(config.get("params") or {}))

    def _grid_search(
        self,
        config: dict[str, Any],
        x_train: NDArray[Any],
        y_train: NDArray[Any],
    ) -> tuple[Any, float]:
        """Fit one candidate model with grid search and return (best estimator, CV score)."""
        estimator = self._instantiate(config)

        search_class = _load_attribute(
            self.grid_search_config["module"], self.grid_search_config["class"]
        )
        search_params = dict(self.grid_search_config.get("params") or {})
        search_params.setdefault("verbose", 0)

        search = search_class(
            estimator=estimator,
            param_grid=config.get("search_param_grid") or {},
            **search_params,
        )
        search.fit(x_train, y_train)

        return search.best_estimator_, float(search.best_score_)

    def get_best_model(
        self,
        X: NDArray[Any],
        y: NDArray[Any],
        base_accuracy: float = 0.6,
    ) -> BestModelDetail:
        """Search every configured model and return the one with the highest CV score."""
        try:
            if not self.model_selection_config:
                raise ValueError("No models declared under 'model_selection'.")

            model_report: dict[str, float] = {}
            best_model: Any = None
            best_score = float("-inf")

            for candidate_name, config in self.model_selection_config.items():
                model_name = f"{config['module']}.{config['class']}"
                logging.info("Training candidate model: %s (%s)", candidate_name, model_name)

                model, score = self._grid_search(config, X, y)
                model_report[model_name] = score

                logging.info("Candidate %s scored %.4f", model_name, score)

                if score > best_score:
                    best_model, best_score = model, score

            if best_model is None:
                raise ValueError("Grid search did not return any model.")

            if best_score < base_accuracy:
                logging.warning(
                    "Best model %s scored %.4f, below the expected accuracy of %.4f",
                    type(best_model).__name__,
                    best_score,
                    base_accuracy,
                )

            logging.info("Best model: %s with score %.4f", type(best_model).__name__, best_score)

            return BestModelDetail(
                best_model=best_model,
                best_score=best_score,
                model_report=model_report,
            )

        except Exception as e:
            raise USvisaException(e, sys) from e
