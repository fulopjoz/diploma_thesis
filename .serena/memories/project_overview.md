## Project Overview
- Diploma thesis repository exploring cheminformatics models for RNA- vs protein-binding ligands.
- Two main modelling tracks: ensemble/XGBoost classifiers (Set 1 & Set 2) and GNN experiments (notebooks plus `models/gnn`).
- Includes FastAPI backend (`backend/`) exposing the Set 1 ensemble model as REST API for molecule classification.
- Notebooks under `notebooks/analysis/` document data prep, feature engineering, and evaluation workflows for both datasets.
- `models/` holds serialized models, feature sets, and experiment outputs; `output/` collects generated figures/reports.
- Deployment assets: Dockerfile & docker-compose for containerizing backend.
