# System Implementation Plan: RNA/Protein Binding Classification

This document is the master plan to productionize the trained XGBoost model for classifying molecules as RNA-binding vs Protein-binding. It covers end-to-end data handling, feature generation parity with training, service contracts, CLI and web app design, database integration, deployment, testing, and workstream prompts so multiple agents can work in parallel.


## 1) Goals and scope

- Provide reliable classification for single molecules and batches from multiple inputs (SMILES string, CSV, SDF, PubChem by CID/name).
- Guarantee feature parity with training pipeline (ECFP6 fingerprints; radius=3, 2048 bits) so model outputs match training expectations.
- Deliver three user interfaces:
  - Programmatic REST API (FastAPI) — already present, to be extended
  - Command-line interface (CLI) for local and batch runs
  - Minimal web app for interactive use
- Persist prediction jobs, inputs, and outputs to a database for reproducibility and later analysis.
- Package and deploy with Docker/Compose; enable easy local dev and reproducible runs.


## 2) Canonical model and feature pipeline

- Model artifact: `models/ensemble/set1/best_xgb.joblib`
- Model type: XGBoost ensemble classifier
- Features: ECFP6 fingerprints (Morgan radius=3, nBits=2048)
- Training conventions and supporting analysis are recorded in notebooks under `notebooks/analysis/`:
  - Set 1:
    - `01_standardization_final.ipynb` (molecule cleanup/standardization)
    - `02_v2_compute_ECFP_n_final.ipynb` (fingerprint generation)
    - Additional analysis notebooks: scaffolds, distributions, features importance
  - Set 2 equivalents exist under `notebooks/analysis/set2/`

Implementation source of truth for production prediction:

- Backend code: `backend/app.py` provides:
  - `smiles_to_ecfp6(smiles, radius=3, n_bits=2048)`
  - `classify_molecule(smiles)`
- Test utility: `backend/test_classifier.py` exercises model load and calls `classify_molecule`
- Visualization helper: `backend/visualize.py` creates plots/report from batch outputs

Success criteria:

- Any new interface (CLI/web) must call the same internal conversion and classification routines (or shared library) to ensure exact parity.

## 2a) Datasets and artifacts to reuse

- Primary datasets are hosted externally (as noted in `README.md`):
  - OwnCloud link: [Dataset Link](https://owncloud.cesnet.cz/index.php/s/juPLpmojqktq0IU)
- Local model and analysis artifacts already in repo:
  - `models/ensemble/set1/best_xgb.joblib` — trained XGBoost model
  - `models/ensemble/set1/features/` — feature importance CSV/PNGs
  - `models/ensemble/set1/results/` — metrics CSV and visuals
  - `output/set1/` — chemical space, histograms, scaffolds, Venn PDFs
  - `output/set2/scaffold_analysis_output_set2/*.csv` — scaffold count CSVs (useful as fixtures)
- Notebooks under `notebooks/analysis/` reproduce standardization, ECFP generation, and evaluation; we will reference these rather than re-implement from scratch.

Usage in this plan:

- Use `best_xgb.joblib` directly for inference (already wired in backend).
- Use the CSVs in `output/set2/scaffold_analysis_output_set2` as sample fixtures for testing file upload endpoints and CLI batch processing (format diversity, error handling), not for model training.
- If raw datasets are needed locally, download them to a documented path (e.g., `data/`) via the OwnCloud link; do not commit large data.

## 2b) Reuse and no-duplication policy

- Single source of truth for feature generation and inference:
  - Extract shared logic into `backend/core.py`; both API and CLI import from there.
- Do not duplicate visualization code; reuse `backend/visualize.py` from API and CLI for reports.
- Reuse `backend/test_classifier.py` as a smoke test baseline; add unit tests beside it rather than new ad-hoc scripts.
- Keep environment bootstrap in `backend/start.sh` as the primary dev entry; update it if flags or checks change.
- Pydantic v2 warning clean-up (rename `schema_extra`→`json_schema_extra`) is a small refactor and should be applied once in `app.py` to avoid duplicating config patterns.


## 3) Data ingestion and preprocessing

Supported inputs:

- Direct SMILES strings
- CSV/TSV files with a column for SMILES (configurable column name; default: `smiles`)
- SDF files containing molecules
- PubChem lookup by CID/name (via `pubchempy`)

Preprocessing steps (RDKit-based; aligned with notebooks):

- SMILES parsing with `Chem.MolFromSmiles`
- Molecule sanitization; if desired, optional standardization akin to Set 1 notebooks:
  - Neutralization of charges (if included in training)
  - Tautomer canonicalization (optional, only if used during training)
  - Stereochemistry handling (document assumptions)
- Reject invalid molecules early; propagate descriptive errors in outputs

Feature generation:

- Morgan/ECFP6 fingerprint with radius=3 and nBits=2048
- Ensure type and shape: `np.int8` array of shape `(2048,)`

Batch handling:

- Chunk large batches for memory efficiency (e.g., chunks of 5k–20k depending on environment)
- Record invalid inputs separately; keep stable ordering of results


## 4) Classification contracts (API/CLI/library)

Core function contract (shared module):

- Input: list of SMILES strings
- Output: list of result dicts with fields:
  - `smiles: str`
  - `prediction: "RNA_binding" | "Protein_binding" | "Invalid"`
  - `probability_rna: float`
  - `probability_protein: float`
  - `confidence: float` (max of probabilities)
  - `valid: bool`
  - `error: Optional[str]`

Batch summary contract:

- `summary: { total, valid, invalid, rna_binding, protein_binding, average_confidence }`

Error modes and behavior:

- Invalid SMILES: return `valid=false` with error message, do not raise; batch continues
- Model not loaded: raise `503` in API, exit non-zero in CLI
- PubChem errors/network failures: return per-item errors and continue

Edge cases:

- Empty input list
- Extremely large batch (memory/perf); enforce chunking
- Highly unusual molecules causing RDKit failures (catch, mark invalid)
- Non-UTF8 inputs in CSV — detect and fail fast with actionable message


## 5) Output data provision

- JSON (API default) with result list and summary
- CSV/TSV export (CLI flag) with columns: `smiles, prediction, probability_rna, probability_protein, confidence, valid, error`
- Optional visualization report using `backend/visualize.py` (PNG + text report) written to an output directory
- Optional database persistence (see Section 8)


## 6) Backend (FastAPI) — enhancements

Current state:

- `backend/app.py` exposes endpoints:
  - `GET /`, `GET /health`
  - `POST /api/classify` (single)
  - `POST /api/classify/batch` (list)
  - `POST /api/classify/pubchem` (CID/name)
- Dockerized via `Dockerfile`, orchestrated by `docker-compose.yml`

Planned enhancements:

- Add file upload endpoints:
  - `POST /api/classify/file` with multipart upload for CSV/SDF
  - Parameters: input format, column name (default `smiles`), delimiter, chunk size, optional output format
- Add export options: `?format=csv|json`, `?report=true` to trigger `visualize.py`
- Add async batching pipeline for large inputs (streaming responses or job-based pattern as an optional phase)
- Add optional DB logging (toggle via env var): persist job metadata + results
- Harden validation and error messages; align response models with Pydantic v2

Non-functional:

- Rate limit basic endpoints (optional)
- Add request IDs to logs for traceability


## 7) CLI tool

Create a CLI (e.g., `backend/cli.py` or package `backend_cli/`) with commands:

- `classify smiles <SMILES...>` — single or multiple SMILES strings
- `classify file --path <FILE> --format csv|tsv|sdf [--smiles-col smiles] [--delimiter ,] [--chunksize 5000]`
- `classify pubchem --id 2244 --id aspirin`
- Common flags: `--output <path>`, `--output-format json|csv`, `--report <dir>`, `--quiet`, `--verbose`
- Exit code non-zero if any fatal failure (e.g., model missing), zero if all processed (even with invalid items recorded)

The CLI must import the exact same core functions used by the API for feature generation and prediction.


## 8) Database integration

Objectives:

- Persist prediction jobs for traceability and re-use
- Store inputs, per-molecule results, and summary stats

Recommended stack:

- PostgreSQL service in docker-compose
- SQLAlchemy 2.0 or SQLModel + Alembic

Schema sketch:

- `jobs` table: id (UUID), created_at, input_type (smiles|file|pubchem), params (JSON), status, summary JSON, durations, report paths
- `molecules` table: id, job_id (FK), input_smiles, normalized_smiles, is_valid, error
- `predictions` table: id, molecule_id (FK), label, p_rna, p_protein, confidence
- Indexes on job_id, timestamps

API additions:

- `GET /api/jobs/{id}` — retrieve job metadata and (optionally) stored results
- `GET /api/jobs/{id}/download?format=csv|json` — export historical job results

Compose changes:

- Add `db` service (postgres) + volume; set `DATABASE_URL` in `api` env


## 9) Frontend web app

Scope: lightweight UI to interact with the API.

Stack options:

- React (Vite) or a minimal FastAPI-Templates page if time-constrained

Key views:

- Single-molecule form (SMILES input, submit, show prediction and probabilities)
- Batch upload page (CSV/SDF upload, options for column name)
- Results table with sortable columns and download as CSV
- Visualization: render summary and confidence distributions (re-use server-generated images or compute client-side)
- Job history page if DB is enabled

Integration details:

- CORS already enabled in backend (`backend/app.py`); lock down origins in production
- Env-configurable API base URL


## 10) Deployment & operations

Docker/Compose:

- Current compose has only `api` service. Extend to include `db`:
  - `postgres:15-alpine`, volume for data, healthcheck
  - Ensure `api` depends_on `db` for DB-backed runs

Environment variables:

- `MODEL_PATH` (optional override — falls back to existing path)
- `DATABASE_URL` (optional; toggles persistence)
- `API_MAX_BATCH` (optional safety cap)

Monitoring/health:

- Keep `/health` endpoint, add DB status when enabled
- Basic request/response structured logging


## 11) Testing, quality, CI

Automated tests:

- Unit tests for fingerprint conversion and classifier routing
- API endpoint tests (fast, use TestClient)
- CLI integration tests on small fixtures (CSV/SDF)
- DB integration tests guarded by marker (dockerized)

Quality gates:

- Black, isort, flake8/ruff; mypy on shared library code
- Pre-commit hooks
- GitHub Actions: run tests, lint, build Docker image


## 12) Workstreams and parallelization (agent-ready prompts)

Below are concurrent tracks with tight contracts and acceptance criteria. Each includes an agent prompt that can be executed independently. Coordinate via shared core library functions.

### A) Core library extraction (shared code)

- Goal: Extract `smiles_to_ecfp6` and classification batching into `backend/core.py` used by API and CLI.
- Deliverables: `backend/core.py`, refactor `app.py` and new CLI to import it; tests.
- Acceptance: API and CLI produce identical outputs for the same inputs.
- Agent prompt:
  """
  Extract common functions from backend/app.py into backend/core.py:
  - smiles_to_ecfp6(smiles: str, radius=3, n_bits=2048) -> np.ndarray|None
  - classify_smiles_list(smiles_list: List[str]) -> Tuple[List[Dict], Dict]
  Refactor app.py and a new cli.py to import from core.py. Add unit tests.
  """

### B) API file upload endpoints

- Goal: Add `POST /api/classify/file` supporting CSV/TSV/SDF.
- Deliverables: Endpoint, streaming/chunked processing, response schema unchanged.
- Acceptance: Upload a CSV with 1000 rows, receive results+summary in < 5s locally (non-binding, hardware dependent).
- Agent prompt:
  """
  Implement multipart file upload endpoint /api/classify/file accepting CSV/TSV/SDF.
  Parameters: format, smiles_col (default 'smiles'), delimiter (default ','), chunksize (default 5000).
  Reuse core.classify_smiles_list; return BatchClassificationResult.
  Add tests with small fixtures.
  """

### C) CLI implementation

- Goal: Provide CLI with commands for smiles, file, pubchem; JSON/CSV outputs; report generation.
- Deliverables: `backend/cli.py` (click/typer), packaging entry point, docs.
- Acceptance: `python -m backend.cli classify smiles "c1ccccc1"` prints JSON; CSV file processed with correct counts.
- Agent prompt:
  """
  Create a Typer-based CLI in backend/cli.py with subcommands: smiles, file, pubchem.
  Support output JSON to stdout, CSV file via --output, and --report for visualize.generate_report.
  Import shared logic from backend/core.py.
  Add basic CLI tests.
  """

### D) Database layer & persistence

- Goal: Add PostgreSQL to compose, SQLAlchemy models, migrations, and optional persistence on classification endpoints/CLI.
- Deliverables: `db` service in compose, `backend/db/models.py`, `backend/db/session.py`, alembic setup, toggled by env.
- Acceptance: When DATABASE_URL set, a job and its predictions are persisted; `GET /api/jobs/{id}` returns stored data.
- Agent prompt:
  """
  Add Postgres to docker-compose. Implement SQLAlchemy models for Job, Molecule, Prediction, with Alembic.
  Wire app.py endpoints to optionally persist runs behind FEATURE_PERSIST=true and DATABASE_URL.
  Add read endpoint GET /api/jobs/{id}. Include tests.
  """

### E) Frontend (React) minimal UI

- Goal: Small app with forms for single SMILES and file upload, results table and charts.
- Deliverables: `frontend/` with Vite React app, build instructions, env-configurable API URL.
- Acceptance: Can classify single SMILES and upload CSV; shows summary; downloads CSV.
- Agent prompt:
  """
  Scaffold a Vite React app in frontend/. Implement pages:
  - Single SMILES classification
  - Batch upload (CSV), show table + summary
  Add env var for API base, CORS handled by backend. Provide instructions.
  """

### F) Deployment & CI

- Goal: Extend Compose, add healthchecks, GitHub Actions pipeline for lint/test/build.
- Deliverables: Updated `docker-compose.yml` with db, `.github/workflows/ci.yml`.
- Acceptance: CI passes on PR; `docker-compose up --build` starts api+db.
- Agent prompt:
  """
  Update docker-compose.yml to include postgres with volume and healthcheck. Add GH Actions workflow to run tests, lint, and build Docker image on PRs.
  """


## 13) File inventory (existing and to-be-added)

Existing to use/extend:

- `backend/app.py` — API service
- `backend/test_classifier.py` — smoke/functional test
- `backend/example_client.py` — reference client
- `backend/visualize.py` — report generation
- `backend/requirements.txt` — deps (FastAPI, RDKit, XGBoost, etc.)
- `Dockerfile`, `docker-compose.yml` — containerization (compose will be extended)
- Model artifact: `models/ensemble/set1/best_xgb.joblib`
- Notebooks for reference: see Section 2

Planned additions:

- `backend/core.py` — shared classification logic
- `backend/cli.py` — Typer-based CLI
- `backend/db/models.py`, `backend/db/session.py`, `alembic/` — DB layer
- `frontend/` — React web app
- `.github/workflows/ci.yml` — CI pipeline
- `docs/` additions — usage and ops guides


## 14) Milestones and DoD

Milestone 1: Unified core + CLI

- Core library extracted; CLI operational; parity verified against API
- DoD: CLI and API return identical results on fixtures; tests pass

Milestone 2: File uploads + reports

- API supports CSV/SDF; report generation toggle
- DoD: Upload fixture, receive results and report files

Milestone 3: Database persistence

- Compose with Postgres; persistence toggled and tested; job read endpoint
- DoD: Job visible via API; records stored in DB

Milestone 4: Frontend MVP

- React app with single/batch pages, table, downloads, basic charts
- DoD: Manual e2e demo against local API

Milestone 5: CI and hardening

- Linting, tests, images build in CI; docs updated; production CORS tightened
- DoD: Green CI on PR with all checks


## 15) Try it (current state)

Local dev (already possible):

```bash
# From repo root
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python test_classifier.py
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Docker:

```bash
docker-compose up --build
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)


## 16) Notes and assumptions

- ECFP6 settings are fixed by model training; changing them requires retraining.
- Notebook standardization steps should be codified only if used in training; otherwise, keep preproc minimal to avoid feature drift.
- RDKit installation may require conda on some systems; the Docker image uses `python:3.10-slim` with system libs compatible with `rdkit==2023.9.4` from pip.
- PubChem endpoints depend on internet connectivity; handle gracefully when offline.
