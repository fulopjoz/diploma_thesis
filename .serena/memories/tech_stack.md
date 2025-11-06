## Tech Stack
- Primary language: Python 3.8+.
- Backend service: FastAPI with Pydantic models, served by Uvicorn; depends on RDKit, scikit-learn, XGBoost, NumPy, pandas, joblib.
- Supporting tooling: PubChemPy for compound lookup, Matplotlib for reporting, requests/httpx for HTTP clients.
- Containerization: Dockerfile and docker-compose.yml target the FastAPI backend.
