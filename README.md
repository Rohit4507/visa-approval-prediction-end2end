# End-to-End US Visa Approval Prediction (MLOps)

<p align="left">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-Web%20App-009688?logo=fastapi&logoColor=white">
  <img alt="MongoDB" src="https://img.shields.io/badge/MongoDB-Atlas-47A248?logo=mongodb&logoColor=white">
  <img alt="AWS" src="https://img.shields.io/badge/AWS-S3%20%7C%20ECR%20%7C%20EC2-FF9900?logo=amazonaws&logoColor=white">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-Container-2496ED?logo=docker&logoColor=white">
  <img alt="CI/CD" src="https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-green.svg">
</p>

An **end-to-end MLOps project** that predicts whether a US visa application will be
**approved** or **rejected**, and takes that model all the way from raw data to a
containerised web app running on AWS.

The project is deliberately built the way production ML systems are built: every stage is a
reusable *component* wired into a *training pipeline*, artifacts are versioned, data drift is
monitored, the trained model is pushed to an S3 model registry, the prediction service is
served with FastAPI, and deployment is automated with GitHub Actions → Amazon ECR → EC2.

> 👤 **Author:** Rohit Singh Rajput — [rohitrajput33220@gmail.com](mailto:rohitrajput33220@gmail.com)
> 🔗 **Repository:** [Rohit4507/visa-approval-prediction-end2end](https://github.com/Rohit4507/visa-approval-prediction-end2end)

---

## Table of Contents

- [Why this project](#why-this-project)
- [Architecture](#architecture)
- [Pipeline stages](#pipeline-stages)
- [Project structure](#project-structure)
- [Tech stack](#tech-stack)
- [Dataset](#dataset)
- [Quickstart](#quickstart)
- [Environment variables](#environment-variables)
- [Running the web app](#running-the-web-app)
- [Training the model](#training-the-model)
- [Docker](#docker)
- [CI/CD and AWS deployment](#cicd-and-aws-deployment)
- [Notebooks](#notebooks)
- [Learning log](#learning-log)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Credits](#credits)
- [License](#license)

---

## Why this project

Approving or rejecting a visa application is a high-volume, high-impact decision. This repo
shows a complete, reproducible machine learning system around that decision:

- **Reproducibility** — config-driven training (`config/model.yaml`) and schema-driven
  validation (`config/schema.yaml`); no hardcoded paths, no notebook-only code.
- **Data quality gates** — schema validation, train/test split checks and **Evidently** data
  drift reports run before any model is trained.
- **Model governance** — every accepted model is versioned in an S3 model registry, and a new
  model only replaces the production one if it beats it by a configured threshold.
- **Operability** — structured logging, custom exception handling, a FastAPI prediction
  service, a Docker image, and an automated CI/CD release to EC2.

## Architecture

![Folder structure](flowcharts/1_Folder%20Structure.png)

```
                    ┌──────────────────────┐
                    │   MongoDB Atlas      │  feature store (visa_data)
                    └──────────┬───────────┘
                               │  Data Ingestion
                               ▼
                    ┌──────────────────────┐
                    │  feature_store/*.csv │
                    └──────────┬───────────┘
                     Data Validation (schema + drift)
                               ▼
                    ┌──────────────────────┐
                    │ train.csv / test.csv │
                    └──────────┬───────────┘
                Data Transformation (preprocessing.pkl)
                               ▼
              Model Trainer (GridSearchCV: KNN, RandomForest)
                               ▼
        Model Evaluation ──► S3 model registry (model.pkl)
                  │                    ▲
                  │        Model Pusher│
                  ▼                    │
        FastAPI app  ◄─────────────────┘
         (Docker → ECR → EC2)
```

The per-stage flowcharts live in [`flowcharts/`](flowcharts) — one image per component
(ingestion, validation, transformation, trainer, evaluation, pusher).

## Pipeline stages

| # | Component | Module | What it does |
|---|-----------|--------|--------------|
| 1 | Data Ingestion | `us_visa/components/data_ingestion.py` | Pulls the collection from MongoDB Atlas into `artifact/.../feature_store/usvisa.csv`, then splits train/test |
| 2 | Data Validation | `us_visa/components/data_validation.py` | Validates columns and dtypes against `config/schema.yaml`, checks dataset size, writes an **Evidently** drift report |
| 3 | Data Transformation | `us_visa/components/data_transformation.py` | Imputes missing values and one-hot encodes categoricals; persists `preprocessing.pkl` |
| 4 | Model Trainer | `us_visa/components/model_trainer.py` | Runs `GridSearchCV` over the estimators declared in `config/model.yaml`, scores on the test set, keeps models above the expected score |
| 5 | Model Evaluation | `us_visa/components/model_evaluation.py` | Compares the new model to the one in S3; only accepts it if the improvement clears `MODEL_EVALUATION_CHANGED_THRESHOLD_SCORE` |
| 6 | Model Pusher | `us_visa/components/model_pusher.py` | Uploads the accepted model + preprocessing object to the S3 model registry |
| 7 | Prediction Pipeline | `us_visa/pipline/prediction_pipeline.py` | Loads the production model from S3 and serves single-record predictions |

## Project structure

```
visa-approval-prediction-end2end/
├── app.py                        # FastAPI entrypoint (/, POST /, /train)
├── config/
│   ├── model.yaml                # model + grid-search definitions
│   └── schema.yaml               # expected columns, dtypes, column groups
├── us_visa/                      # core library (installed as the `us_visa` package)
│   ├── cloud_storage/            # S3 client + upload/download helpers
│   ├── components/               # the 6 pipeline components
│   ├── configuration/            # MongoDB and AWS connection factories
│   ├── constants/                # every tunable name/threshold in one place
│   ├── data_access/              # MongoDB → DataFrame access layer
│   ├── entity/                   # config + artifact dataclasses, estimators
│   ├── exception/                # custom USvisaException with traceback detail
│   ├── logger/                   # timestamped file + console logging
│   ├── pipline/                  # training and prediction pipelines
│   └── utils/                    # YAML readers, model save/load, evaluation helpers
├── notebook/                     # EDA, feature engineering, drift, MongoDB demos
├── flowcharts/                   # component-level design diagrams
├── templates/, static/           # Jinja2 template and CSS for the web UI
├── template.py                   # scaffolding script for the folder structure
├── demo.py                       # scratch file used while building components
├── ProjectFlow.txt               # step-by-step build log of the whole project
├── Dockerfile, .dockerignore
├── .github/workflows/            # CI/CD (ECR push + EC2 deploy) and syntax CI
├── requirements.txt, setup.py
└── LICENSE
```

## Tech stack

| Layer | Tools |
|---|---|
| Data & storage | MongoDB Atlas, pandas, numpy, Kaggle dataset |
| Modelling | scikit-learn, XGBoost, CatBoost, imbalanced-learn |
| Monitoring | Evidently (data drift reports) |
| Serving | FastAPI, Uvicorn, Jinja2 |
| Cloud | AWS S3 (model registry), ECR (images), EC2 (runtime), IAM |
| DevOps | Docker, GitHub Actions, self-hosted runner |
| Config & logging | PyYAML, `from_root`, custom logger/exception modules |

## Dataset

[EasyVisa dataset](https://www.kaggle.com/datasets/moro23/easyvisa-dataset) — 25,480 visa
applications with 11 features describing the employee, the employer and the job offer.

| Feature | Type | Notes |
|---|---|---|
| `continent` | categorical | employee's continent of origin |
| `education_of_employee` | categorical | highest degree |
| `has_job_experience` | categorical | Y/N |
| `requires_job_training` | categorical | Y/N |
| `no_of_employees` | numeric | company size |
| `yr_of_estab` | numeric | year the company was established |
| `region_of_employment` | categorical | US region |
| `prevailing_wage` | numeric | offered wage |
| `unit_of_wage` | categorical | Hour/Year/Month/Week |
| `full_time_position` | categorical | Y/N |
| **`case_status`** | **target** | Certified / Denied |

A copy for offline work sits at [`notebook/Visadataset.csv`](notebook/Visadataset.csv); the
pipeline itself reads from MongoDB Atlas.

## Quickstart

```bash
# 1. clone
git clone https://github.com/Rohit4507/visa-approval-prediction-end2end.git
cd visa-approval-prediction-end2end

# 2. environment (Python 3.8+)
conda create -n visa python=3.8 -y && conda activate visa
pip install -r requirements.txt          # installs the local `us_visa` package too

# 3. configure secrets (see next section)
cp .env.example .env                     # then edit .env

# 4. run the web app
python app.py                            # http://localhost:8080
```

## Environment variables

The project never hardcodes credentials — everything is read from the environment:

| Variable | Required for | Purpose |
|---|---|---|
| `MONGODB_URL` | ingestion | MongoDB Atlas connection string |
| `AWS_ACCESS_KEY_ID` | evaluation, pusher, prediction | IAM access key |
| `AWS_SECRET_ACCESS_KEY` | evaluation, pusher, prediction | IAM secret key |
| `MODEL_BUCKET_NAME` | S3 registry | bucket that stores `model.pkl` (default: `rohit-usvisa-model-registry`) |

```bash
export MONGODB_URL="mongodb+srv://<user>:<password>@cluster0.xxxxxxx.mongodb.net/?retryWrites=true&w=majority"
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
export MODEL_BUCKET_NAME="rohit-usvisa-model-registry"
```

On Windows PowerShell:

```powershell
$env:MONGODB_URL="mongodb+srv://..."
$env:AWS_ACCESS_KEY_ID="..."
$env:AWS_SECRET_ACCESS_KEY="..."
$env:MODEL_BUCKET_NAME="rohit-usvisa-model-registry"
```

## Running the web app

```bash
python app.py
```

| Route | Method | Description |
|---|---|---|
| `/` | GET | Renders the visa application form |
| `/` | POST | Takes the 10 application fields and returns **Visa-approved** / **Visa Not-Approved** |
| `/train` | GET | Triggers the full training pipeline and returns the outcome |
| `/docs` | GET | Auto-generated OpenAPI docs (FastAPI) |

## Training the model

```bash
# through the API
curl http://localhost:8080/train

# or straight from Python
python -c "from us_visa.pipline.training_pipeline import TrainPipeline; TrainPipeline().run_pipeline()"
```

Every run writes its artifacts to `artifact/<timestamp>/` — ingestion, validation, transformation,
trainer, evaluation and pusher outputs are kept separately so you can inspect or roll back.

## Docker

```bash
docker build -t usvisa .
docker run -d --name usvisa -p 8080:8080 \
  -e MONGODB_URL="$MONGODB_URL" \
  -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
  -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
  -e MODEL_BUCKET_NAME="$MODEL_BUCKET_NAME" \
  usvisa
```

## CI/CD and AWS deployment

`.github/workflows/aws.yaml` runs on every push to `main`:

1. **Continuous Integration** (GitHub-hosted): configure AWS credentials → log in to Amazon ECR →
   build the Docker image → push it to ECR.
2. **Continuous Deployment** (self-hosted runner on EC2): check out the repo → log in to ECR →
   `docker run` the freshly pushed image on port `8080`.

Repository secrets required:

```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_DEFAULT_REGION
ECR_REPO
MONGODB_URL
```

AWS resources to provision: an S3 bucket for the model registry, an ECR repository for images, an
EC2 Ubuntu instance (with Docker and a self-hosted GitHub runner), and IAM users for
S3/ECR access. The full console walkthrough — including security groups, port `8080`, and runner
registration — is in [`ProjectFlow.txt`](ProjectFlow.txt), and can be repeated for your own AWS
account using the placeholders listed there.

> **The deploy workflow is opt-in.** Both jobs are gated on a repository variable named
> `DEPLOY_ENABLED`, so pushes to `main` stay green until your AWS account is wired up. When the
> five secrets above exist and the self-hosted runner is online, create
> **Settings → Secrets and variables → Actions → Variables → `DEPLOY_ENABLED = true`** and the
> pipeline goes live. The lightweight `ci.yml` (syntax, config and secret checks) runs on every
> push and needs no secrets at all.

## Notebooks

| Notebook | Contents |
|---|---|
| [`1_EDA_US_visa.ipynb`](notebook/1_EDA_US_visa.ipynb) | Univariate/bivariate analysis, class balance, wage and education insights |
| [`2_Feature_Engineering_and_Model_Training.ipynb`](notebook/2_Feature_Engineering_and_Model_Training.ipynb) | Cleaning, encoding, model comparison and hyper-parameter search |
| [`data_drift_demo_evidently.ipynb`](notebook/data_drift_demo_evidently.ipynb) | Evidently drift report used by the validation component |
| [`mongoDB_demo.ipynb`](notebook/mongoDB_demo.ipynb) | Pushing the Kaggle CSV into MongoDB Atlas (connection strings are placeholders) |

## Learning log

[`ProjectFlow.txt`](ProjectFlow.txt) documents the project from empty folder to deployed
endpoint — MongoDB Atlas setup, component-by-component build order, AWS IAM/S3/ECR/EC2
configuration, self-hosted runner registration and GitHub secrets. It is the fastest way to
understand *why* each file exists.

## Roadmap

Planned improvements:

- [ ] Pin dependency versions and add a `requirements-dev.txt`
- [ ] Improve the Jinja2 form UI: input validation, loading states and a results panel
- [ ] Add `pytest` unit tests for every component and wire them into CI
- [ ] Track experiments with MLflow instead of only S3 artifacts
- [ ] Serve the model with a proper `/predict` JSON API alongside the HTML form
- [ ] Rebuild the image on `python:3.11-slim` and switch to `boto3` with IAM roles (no static keys)
- [ ] Add scheduled drift monitoring instead of drift checks only at training time
- [ ] Rename `us_visa/pipline` → `us_visa/pipeline` (typo carried over from the original layout)

## Contributing

Issues and pull requests are welcome. Please branch from `main`, keep the component structure
(config → component → pipeline), and make sure `python -m compileall us_visa app.py` passes
before opening a PR.

engineering improvements are tracked in the [roadmap](#roadmap).

## License

Released under the [MIT License](LICENSE).
