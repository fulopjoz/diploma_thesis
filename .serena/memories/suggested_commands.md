## Suggested Commands
- `cd backend && ./start.sh` – automated backend setup (venv, install deps, run tests, launch API).
- `cd backend && uvicorn app:app --reload --host 0.0.0.0 --port 8000` – run FastAPI server in dev mode.
- `cd backend && python app.py` – alternative to launch the API.
- `cd backend && python test_classifier.py` – run smoke tests that load the model and classify sample molecules.
- `docker-compose up --build` – build and start the API via Docker Compose.
- `docker build -t rna-classifier . && docker run -p 8000:8000 rna-classifier` – manual Docker workflow from repo root.
