## Task Completion Checklist
- After code changes touching backend logic, run `cd backend && python test_classifier.py` to verify model loading and sample classifications.
- When altering API endpoints, start the server with `uvicorn app:app --reload` and manually hit `/health` or `/docs` to confirm responses.
- If deployment configuration changed, rebuild containers with `docker-compose up --build` to ensure images still start.
- Confirm the model artifact `models/ensemble/set1/best_xgb.joblib` remains accessible from `backend/` before finishing work.
