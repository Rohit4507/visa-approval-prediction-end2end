# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[semantic versioning](https://semver.org/).

## [Unreleased]

Weekend roadmap items 3–5 from [`docs/ROADMAP_2026.md`](docs/ROADMAP_2026.md): Pydantic API,
local MLflow + MinIO registry, scheduled drift monitoring.

## [0.2.0] — 2026-11-11

### Changed

- **Packaging:** replaced `setup.py` + `requirements.txt` with a PEP 621 `pyproject.toml` and a
  committed `uv.lock`; the project now installs as `us-visa` on Python 3.11+ (CI verifies 3.12 and 3.13).
- **Dependencies:** dropped three abandoned/indirect packages — `from_root` (replaced by `pathlib`),
  `dill` (replaced by `joblib`), `neuro_mf` (replaced by a local, tested `ModelFactory`) — and
  renamed `imblearn` to `imbalanced-learn`. Notebook-only libraries moved to the `notebooks` extra.
- **Evidently:** ported the data-validation drift report from the removed 0.2.x `Profile` API to the
  current `Report` + `DataDriftPreset` snapshot API (0.7.x), and made the report structure explicit
  (`summary` block with feature counts, drift share and threshold).
- **Quality gates:** added `ruff` (lint + format), `mypy` (the `us_visa` package type-checks cleanly),
  a 40-test `pytest` suite with a coverage gate, and `pre-commit` hooks.
- **CI:** the workflow now runs lint, formatting, types and tests on Python 3.12 and 3.13 using the
  lockfile; config/notebook validation and the credential scan moved to their own job.
- **Typing fixes:** `USvisaException` is properly typed, `USvisaModel.predict` is duck-typed,
  the MongoDB client is annotated, and error paths raise with `from e` to keep tracebacks.
- **Renamed:** `us_visa/pipline` → `us_visa/pipeline` (imports, docs and scaffolding updated).

### Added

- `tests/` — unit tests for utils, exceptions and estimators, component tests for data validation
  and the model factory, and API smoke tests, all running on synthetic fixtures (no MongoDB/AWS).
- `CHANGELOG.md` and an expanded README development section.

## [0.1.0] — 2026-11-11

### Added

- Imported and rebranded the end-to-end MLOps pipeline: data ingestion, validation, transformation,
  training, evaluation and model pushing, the FastAPI app, notebooks, flowcharts and CI/CD workflow.
