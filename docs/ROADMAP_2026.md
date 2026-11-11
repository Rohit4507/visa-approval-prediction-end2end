# Roadmap 2026 — turning this project into a current-generation system

> Author: Rohit Singh Rajput · Last updated: November 2026
>
> This document is the plan for v2 of `visa-approval-prediction-end2end`. It is written against
> the state of the repo as of `main@c9a2b32` (the imported + rebranded v1), and it is deliberately
> opinionated: every item says *why*, *what exactly to change*, and *how much effort* it is.

---

## 1. Honest gap audit

This is what v1 looks like next to what a 2026 reviewer (or interviewer) expects:

| Area | v1 today | 2026 expectation | Severity |
|---|---|---|---|
| Runtime | `python:3.8.5-slim-buster` (3.8 EOL Oct 2024, buster EOL) | Python 3.12/3.13 slim, optional 3.14 free-threaded | 🔴 high |
| Dependencies | 20 unpinned lines, `-e .`, `imblearn` (legacy name), `neuro_mf`, `from_root` | `pyproject.toml` (PEP 621) + `uv.lock`, hashes, Renovate bot | 🔴 high |
| Quality gates | none — no tests, no linter, no types | `pytest` w/ coverage gate, `ruff`, `mypy`, `pre-commit` | 🔴 high |
| Orchestration | `TrainPipeline.run_pipeline()` called from a GET route | Dagster/Prefect assets, retries, schedules, lineage | 🟠 medium |
| Data | MongoDB collection → CSV artifacts | Parquet + DuckDB, data contracts (Pandera), versioned datasets (DVC/lakeFS) | 🟠 medium |
| Drift | `evidently==0.2.8` (pre-0.3 API, removed in current releases) | Evidently 0.7.x `Snapshot` API, drift as a service + alerting | 🔴 high |
| Model registry | `model.pkl` on S3 under a key, "beat the old score by 2%" | MLflow 3.x registry, aliases (`champion`/`challenger`), signatures, lineage, pickle-free | 🟠 medium |
| Modelling | GridSearchCV over KNN/RandomForest on a random split | sklearn `Pipeline` + `HistGradientBoosting`/CatBoost, Optuna, calibration, cost-based threshold, SHAP | 🟠 medium |
| Serving | HTML form only, model re-loaded per request, `except: return {"error": str(e)}` | Pydantic v2 contracts, warm model in `lifespan`, `/predict` + `/batch` + `/explain`, `/healthz` | 🔴 high |
| Deploy | `docker run` on EC2 + self-hosted runner, long-lived AWS keys in secrets | IaC (OpenTofu/Terraform), ECS Fargate or EKS+KServe, GitHub OIDC → no static keys | 🔴 high |
| Observability | log files on the box | OpenTelemetry traces, Prometheus + Grafana, SLOs, alert rules, prediction logging | 🔴 high |
| Governance | none | model card, decision audit log, human-in-the-loop, bias slices, EU AI Act §7 mapping | 🟠 medium |
| Security | secrets in repo history (fixed in v1), no scan in CI | Trivy image scan, SBOM + cosign signing, branch protection, secret scanning | 🟠 medium |
| Front end | Jinja2 form + CSS | React/Next or HTMX + explanation panel + confidence | 🟢 low (cosmetic) |

**Verdict:** the *architecture* (component → entity → pipeline, config-driven, artifacts) is
still sound and worth keeping. What is dated is the **tooling, the delivery path, and the
absence of testing/observability/governance**. This is a refactor, not a rewrite.

---

## 2. Target architecture (v2)

```
              ┌──────────────────────────── Data plane ────────────────────────────┐
  Kaggle ──► S3 (Parquet, versioned by DVC/lakeFS)
              │
              ├─► Pandera data contract ──► Dagster/Prefect orchestration (schedule + retries)
              │                                   │
              └───────────────────────────────────┴──► feature/training job
                                                          │
                        ┌─────────────────────────────────┴─────────────────────┐
                        ▼                                                       ▼
             MLflow tracking + model registry                     Evidently monitoring job
             (aliases: champion / challenger)                     (drift + performance, cron)
                        │                                                       │
                        ▼                                                       ▼
  ┌──────────────── Model plane ───────────────┐            ┌──── Observability ─────┐
  │ FastAPI (or BentoML/KServe)                │            │ OpenTelemetry traces   │
  │ /predict  /batch  /explain  /healthz       │───────────►│ Prometheus + Grafana   │
  │ Pydantic v2 contracts, warm model          │            │ alerts → Slack/email   │
  └──────────────────┬─────────────────────────┘            └────────────────────────┘
                     │
                     ▼
  ┌──────────────── Trust plane (2026 differentiator) ─────────────────┐
  │ decision audit log · human-review queue · model card · bias report │
  │ RAG "why was this denied?" explainer (cited) · MCP tool for agents │
  └────────────────────────────────────────────────────────────────────┘

  Deployed by: OpenTofu/Terraform → ECS Fargate (or EKS + KServe)
  Released by: GitHub Actions (OIDC → AWS), canary + auto-rollback
```

---

## 3. The upgrades, ordered by return on effort

### 3.1 Week-zero hygiene — the highest ROI by far (2–3 evenings)

Nothing else you build will look credible without this, and it is pure mechanical work.

```bash
uv init --python 3.13        # or: uv venv && uv add ...
uv add fastapi uvicorn pydantic-settings pymongo boto3 pandas numpy scikit-learn \
       xgboost catboost evidently mlflow optuna shap pandera pyarrow duckdb structlog
uv add --dev pytest pytest-cov ruff mypy pre-commit
uv lock
```

- Replace `setup.py` + `requirements.txt` with `pyproject.toml` (`[project]`, `[dependency-groups]`)
  and commit `uv.lock`. Drop `imblearn` → `imbalanced-learn`, `from_root` → `pathlib`,
  `neuro_mf` (unused) → delete, `dill` → `cloudpickle`/`joblib`.
- `ruff` (lint + format), `mypy` on `us_visa/`, `pre-commit` hooks, `pytest --cov --cov-fail-under=80`.
- Python **3.13** as target (3.14's free-threaded build is officially supported now, but not worth
  it for this workload — the bottleneck is I/O, not the GIL).
- Fix the `us_visa/pipline` → `us_visa/pipeline` typo once, with a redirect-free import sweep.

**Acceptance:** `uv run pytest`, `uv run ruff check`, `uv run mypy us_visa` all green; CI fails on
any of them.

### 3.2 Container + supply chain (1 evening)

- Multi-stage Dockerfile: `python:3.13-slim` builder → distroless/non-root runtime, `HEALTHCHECK`,
  pinned digests.
- `trivy image` scan + `syft` SBOM + `cosign sign` in CI; fail on HIGH/CRITICAL.
- Branch protection on `main`, required checks, Dependabot/Renovate for the 20+ deps you now have.

### 3.3 Data layer: contracts and versioning (1 week)

- Land raw data as **Parquet in S3**, query with **DuckDB** locally — kills the "CSV in artifact dir"
  pattern and makes the pipeline runnable without MongoDB.
- **Pandera** schema (replaces the hand-written `schema.yaml` checks): dtypes, ranges, allowed
  categories, no-null policy, plus a `case_id` uniqueness invariant.
- **DVC** or **lakeFS** for dataset versioning so every model run points at an immutable dataset
  hash. Store the hash as an MLflow tag.
- Add a *temporal* split (`case_id`/submission order) next to the random split — a random split on
  this data leaks future cases and inflates metrics. Report both.

### 3.4 Orchestration: replace the hand-rolled pipeline (3–5 days)

- **Dagster** (asset-first, best lineage story) or **Prefect** (simplest migration). Keep
  `us_visa/components/*` as the pure functions; the orchestrator becomes the only thing that
  schedules, retries and records.
- Every stage gets an **asset key**, an output Parquet artifact, retries with backoff, and an
  **OpenLineage** event. `/train` then triggers a *run*, not a function call — and returns a run id.
- Schedule drift check daily, retraining weekly (or on drift/performance trigger).

### 3.5 Experiment tracking + registry: MLflow 3.x (3–4 days)

- Current MLflow (3.18 line as of Nov 2026) has **deprecated model stages** — use **aliases**
  (`champion`, `challenger`) and tags. The 3.11+ line also brought pickle-free serialization and
  native `uv` dependency capture, which is exactly what you want for reproducible models.
- `mlflow.autolog()` for parameters/metrics/artifacts, `log_model(..., signature=..., input_example=...)`,
  register with `--alias challenger`, and promote to `champion` only after the evaluation gate.
- **Optuna** for HPO (replaces `config/model.yaml` grid search), with the study persisted in the
  MLflow run. Keep a YAML profile for the search space so it stays config-driven.
- Delete `us_visa/cloud_storage/*` + `entity/s3_estimator.py` in favour of the MLflow client.

### 3.6 Model quality that a 2026 reviewer will actually probe (1 week)

- `sklearn.pipeline.Pipeline` + `ColumnTransformer` as a **single artifact** (no separate
  `preprocessing.pkl`).
- `HistGradientBoostingClassifier` / `CatBoostClassifier` with native categorical handling; keep
  KNN/RF only as baselines.
- **Calibration** (`CalibratedClassifierCV`) + report Brier score / reliability curve. A visa
  decision needs probabilities that mean something, not just a class label.
- **Cost-based threshold**: an FP (wrongly approving) and an FN (wrongly denying) are not equally
  bad — encode that, pick the operating point, and document it.
- **Slice metrics + fairness**: approval rate and TPR/FPR per `continent`, `education_of_employee`,
  `unit_of_wage`. Report disparate impact; this is the finding a serious reviewer looks for.
- **SHAP** reasons per prediction → `/explain`, human-readable top-3 factors per case.

### 3.7 Serving: a real API (3–4 days)

```python
# app/main.py (sketch)
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model = load_champion()      # warm, once
    yield

@app.post("/predict", response_model=PredictionResponse)
async def predict(case: VisaCase, request: Request) -> PredictionResponse: ...

@app.post("/predict/batch", response_model=list[PredictionResponse])
@app.post("/explain")            # SHAP top factors
@app.get("/healthz")             # liveness
@app.get("/readyz")              # model loaded + registry reachable
@app.get("/metrics")             # Prometheus
```

- Pydantic v2 models shared by request *and* validation pipeline (one contract, two uses).
- Request-id middleware, structured JSON logs (`structlog`), timeouts, per-key rate limiting.
- Keep the HTML form as a thin demo page that calls `/predict` — the API becomes the product.
- If you want the "scale" box ticked: **BentoML** (Python-first, adapts batching, OTel-native) or
  **KServe** on K8s (scale-to-zero, canary, Prometheus out of the box). Don't do K8s *and* a
  rewrite in the same month.

### 3.8 Deployment with IaC and no static keys (1 week)

- **OpenTofu/Terraform** for S3, ECR, ECS Fargate service + ALB, CloudWatch, IAM. `terraform plan`
  in PR, `apply` on merge, separate `dev`/`prod` workspaces.
- **GitHub Actions OIDC → IAM role** (`permissions: id-token: write`). Delete the long-lived
  `AWS_ACCESS_KEY_ID`/`SECRET` secrets entirely; this alone is a strong 2026 signal.
- Canary or blue/green (CodeDeploy on ECS, or Argo Rollouts on K8s) with automatic rollback on
  error-rate/latency regression.
- Kill the EC2 + self-hosted runner pattern. Rough monthly cost: ECS Fargate + ALB ≈ $25–40;
  EKS control plane alone ≈ $73 before nodes; SageMaker endpoint ≈ $60+. Fargate is the right
  default for this service.

### 3.9 Observability and monitoring (1 week)

- **OpenTelemetry** traces (HTTP span → model span), Prometheus metrics: `predict_latency_p95`,
  `predictions_total{decision}`, `model_version`, `drift_score`, `input_null_ratio`.
- Grafana dashes for the four golden signals + ML signals (prediction distribution vs training
  baseline, mean confidence).
- **Evidently 0.7.x**: `report.run(reference_data, current_data)` → `Snapshot`, export drift metrics
  to Prometheus/dashboard; schedule daily, alert on dataset drift share > calibrated threshold.
  (Note: current Evidently rejects the 0.2.x `Report(metrics=[DataDriftPreset()])` style this repo
  still uses, so this is a mandatory change, not a nice-to-have.)
- Retraining trigger: drift breach or rolling F1 drop → open a Dagster run / PR to `main`.
- Runbook: what to do when p95 latency triples, when drift fires, how to roll back.

### 3.10 Governance and trust — the 2026 differentiator (1 week)

Visa/immigration decision support is **Annex III §7 high-risk** under the EU AI Act. Annex III
obligations were deferred by the Digital Omnibus to **2 December 2027** (Art. 50 transparency is
already live since 2 August 2026), and GDPR Art. 22 on automated decisions applies today. So the
right framing is *"built for a Dec-2027 compliance deadline, useful now"*:

- **Model card** (`docs/model-card.md`): intended use, non-use, training data provenance, metrics
  per slice, known limitations, human-oversight requirement, contact.
- **Data card** for the dataset; **decision audit log** (input hash, model version + alias, score,
  reasons, timestamp) — legally this is the "automatic logging" requirement.
- **Human-in-the-loop**: the API returns a recommendation + reasons; a review UI records
  accept/override with a reason code, and override rate becomes a monitored metric.
- **Never** auto-deny: make "no decision without a human" an explicit, tested invariant.
- Adverse-action explanation ("your application scored X, main factors were Y") from SHAP.
- Map each Chapter III obligation (risk mgmt, data governance, tech docs, logging, transparency,
  human oversight, accuracy/robustness/security) to a repo artifact — a one-page traceability
  table in `docs/compliance.md` is enough, and it is a genuinely rare thing to see in a portfolio.

### 3.11 The GenAI layer (optional, 1–2 weeks, high demo value)

Only after 3.1–3.7 — otherwise it is lipstick.

- **RAG explainer**: index the policy text (8 CFR / USCIS policy manual excerpts) with embeddings;
  `/explain` returns reasons **with citations** to the actual rule. Guardrails: refusal on
  out-of-scope asks, no new facts, citations required.
- **Evals** for that layer: `promptfoo` or DeepEval golden set (20–30 cases) in CI, hallucination
  and citation-precision metrics. LLM tracing via Langfuse/MLflow tracing; token + cost budget.
- **MCP server** exposing `predict_visa_case` and `get_case_reasons` as tools, so agents/IDEs can
  call your model as a first-class tool (MLflow 3.15+ even ships an MCP registry for this).
- Never let the LLM touch the decision — it only *explains* the model's output.

---

## 4. Current → 2026 stack

| Concern | v1 | v2 target |
|---|---|---|
| Packaging | `setup.py` + `requirements.txt` | `pyproject.toml` + `uv.lock` |
| Runtime | Python 3.8.5, buster | Python 3.13 slim / distroless, non-root |
| Lint/type/test | — | ruff, mypy, pytest + coverage gate |
| Orchestration | hand-rolled `TrainPipeline` | Dagster or Prefect + OpenLineage |
| Storage | MongoDB + CSV | S3 Parquet + DuckDB (+ MongoDB only as source) |
| Contracts | `schema.yaml` + asserts | Pandera + Pydantic v2 (shared) |
| Versioning | none | DVC/lakeFS + MLflow tags |
| Tracking/registry | S3 keys + score threshold | MLflow 3.x, aliases, signatures, lineage |
| HPO | GridSearchCV in YAML | Optuna (MLflow-logged studies) |
| Explainability | — | SHAP per prediction + global report |
| Drift | Evidently 0.2.8 (obsolete API) | Evidently 0.7.x + scheduled monitoring + alerts |
| Serving | Jinja2 form, per-request load | FastAPI + Pydantic, warm model, `/predict` `/batch` `/explain` |
| Deploy | EC2 + `docker run` + self-hosted runner | OpenTofu → ECS Fargate, canary, auto-rollback |
| Auth to AWS | static keys in GitHub secrets | GitHub OIDC → IAM role |
| Observability | log files | OTel traces, Prometheus, Grafana, SLOs |
| Governance | — | model card, audit log, HITL, AI Act §7 mapping |
| GenAI | — | cited RAG explainer + evals + MCP tool |

---

## 5. Sequenced plan (8 weeks, part-time)

| Week | Focus | Done when |
|---|---|---|
| 1 | Hygiene: `pyproject` + uv, ruff/mypy/pytest, pre-commit, `pipline` → `pipeline`, Python 3.13 | CI green on all gates; v1 behaviour unchanged |
| 2 | Container + supply chain: multi-stage, non-root, Trivy/SBOM/cosign, Renovate, branch protection | Image scans clean, `main` protected |
| 3 | Data: Parquet + DuckDB, Pandera contract, DVC, temporal split | Pipeline runs offline from Parquet; contract test fails on bad data |
| 4 | Orchestration: Dagster assets for the 6 stages + schedule | `/train` returns a run id; lineage visible |
| 5 | MLflow registry + Optuna; delete S3 estimator/cloud_storage | Champion/challenger promotion works end to end |
| 6 | Modelling quality: sklearn Pipeline, CatBoost/HGB, calibration, cost threshold, SHAP, fairness slices | Model card auto-generated with per-slice metrics |
| 7 | Serving v2: Pydantic API, warm model, `/batch`, `/explain`, health, rate limit; OTel + Prometheus | p95 < 100 ms local; Locust/k6 report committed |
| 8 | Deploy: OpenTofu + ECS Fargate + OIDC + canary; Grafana dashboard; drift cron + alert | One-command deploy, rollback tested, alert fires in a drill |
| 9–10 (optional) | Governance pack + cited RAG explainer + MCP tool + evals | `docs/compliance.md` + eval suite in CI |

**Metrics to put in the README when done:** test coverage %, p95 latency, model Brier score,
approval-rate parity across `continent`, mean time from merge → deployed, drift alert MTTD.

---

## 6. If you only have a weekend

Do these five, in this order — they move the project the most per hour spent:

1. `pyproject.toml` + `uv.lock` + ruff/mypy/pytest + CI gate (kills the "tutorial repo" smell).
2. Multi-stage `python:3.13-slim` image, non-root, with a Trivy scan step.
3. `/predict` + Pydantic v2 + warm model in `lifespan` + `/healthz` (keeps the form as a demo page).
4. MLflow tracking + registry alias `champion` instead of `model.pkl` on S3.
5. Evidently 0.7.x drift job on a schedule + a badge/dashboard screenshot in the README.

---

## 7. Anti-goals (don't do these)

- **No Kubernetes** unless learning K8s *is* the goal — one 0.5-vCPU service does not need it.
- **No Kafka/Spark/Feast** for 25k rows; DuckDB + Parquet is the correct scale answer.
- **No microservices split** — one deployable app + one training job + one monitoring job.
- **No LLM in the decision path**, ever. Explanation only, with citations and evals.
- **No fabricated metrics** in the README; publish the real numbers, including the weak slices.

---

## 8. Decisions I need from you

1. **Goal** — portfolio/interviews, or a real service? (Portfolio → prioritise 3.1, 3.6, 3.7, 3.9,
   3.10. Real service → add 3.8, 3.9, 3.10 and a paging policy.)
2. **Cloud & budget** — stay on AWS (Fargate ≈ $25–40/mo), or a free tier (Render/Fly/HF Spaces +
   S3 + local MLflow)? Or fully local (Docker Compose + MinIO + MLflow) for zero cost?
3. **K8s** — skip it, or make KServe part of the learning goal?
4. **GenAI layer** — yes (it is the flashiest 2026 differentiator) or keep it pure classical ML?
5. **Scope now** — start with the weekend list (section 6) or jump straight into week 1 of
   section 5?

Answer those and I can start landing PR-sized chunks immediately.
