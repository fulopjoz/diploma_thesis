# Quick Start Guide - RNA/Protein Binding Classifier Backend

This guide will help you get the backend API up and running in just a few minutes.

## Prerequisites

- Python 3.8 or higher
- pip package manager
- Git (to clone the repository)

## Installation

### Option 1: Automated Setup (Recommended)

1. Navigate to the backend directory:
```bash
cd backend
```

2. Run the startup script:
```bash
./start.sh
```

This will automatically:
- Create a virtual environment
- Install all dependencies
- Run tests
- Start the API server

### Option 2: Manual Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run tests to verify installation:
```bash
python test_classifier.py
```

5. Start the server:
```bash
python app.py
# or
uvicorn app:app --reload
```

### Option 3: Docker

1. Build and run with Docker Compose:
```bash
docker-compose up --build
```

The API will be available at `http://localhost:8000`

## First Steps

### 1. Check API Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "model_loaded": true
}
```

### 2. View API Documentation

Open your browser and go to:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 3. Classify Your First Molecule

```bash
curl -X POST "http://localhost:8000/api/classify" \
  -H "Content-Type: application/json" \
  -d '{"smiles": "c1ccccc1"}'
```

Expected response:
```json
{
  "smiles": "c1ccccc1",
  "prediction": "Protein_binding",
  "probability_rna": 0.0019,
  "probability_protein": 0.9981,
  "confidence": 0.9981,
  "valid": true,
  "error": null
}
```

### 4. Run the Demo

```bash
python demo.py
```

This will:
- Test all API endpoints
- Classify multiple molecules
- Generate visualization reports
- Show example usage patterns

## Common Use Cases

### Classify Multiple Molecules

```python
from example_client import RNAProteinClassifierClient

client = RNAProteinClassifierClient()
results = client.classify_batch([
    "c1ccccc1",  # benzene
    "CCO",       # ethanol
    "CC(=O)O"    # acetic acid
])

print(f"Results: {results['summary']}")
```

### Generate Visualization Reports

```python
from visualize import generate_report

# After getting results from the API
generate_report(results, output_dir="/tmp/my_report")
```

### Fetch from PubChem

```bash
curl -X POST "http://localhost:8000/api/classify/pubchem" \
  -H "Content-Type: application/json" \
  -d '{"compound_ids": ["2244", "aspirin"]}'
```

## Troubleshooting

### Model not found

Ensure the model file exists at:
```
../models/ensemble/set1/best_xgb.joblib
```

### RDKit installation issues

If pip fails to install RDKit, try using conda:
```bash
conda install -c conda-forge rdkit
pip install -r requirements.txt --ignore-installed rdkit
```

### Port already in use

Use a different port:
```bash
uvicorn app:app --port 8001
```

## Next Steps

1. **Integrate into your application**: Use the `example_client.py` library
2. **Customize**: Modify endpoints or add new features in `app.py`
3. **Deploy**: Use Docker Compose for production deployment
4. **Frontend**: Connect a web frontend using the API

## Support

- Full documentation: `backend/README.md`
- API docs: http://localhost:8000/docs
- Example scripts: `demo.py`, `example_client.py`
- Visualization: `visualize.py`

## Performance

Expected performance on standard hardware:
- Single molecule: < 10ms
- Batch of 100 molecules: < 1s
- Model loading: < 2s

## API Endpoints Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/api/classify` | POST | Classify single molecule |
| `/api/classify/batch` | POST | Classify multiple molecules |
| `/api/classify/pubchem` | POST | Fetch from PubChem and classify |
| `/docs` | GET | Interactive API documentation |

## Security Notes

- CORS is enabled for all origins in development mode
- For production, update CORS settings in `app.py`
- No authentication required (add if needed for production)
- All inputs are validated using Pydantic models

Happy classifying! 🧬
