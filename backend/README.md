# RNA/Protein Binding Classifier - Backend

A FastAPI-based backend service and command-line interface for classifying molecules as RNA-binding or Protein-binding using a pre-trained XGBoost ensemble model.

## Features

- **Single Molecule Classification**: Classify individual molecules from SMILES strings
- **Batch Processing**: Process multiple molecules in a single request
- **PubChem Integration**: Fetch molecules from PubChem database by CID or name
- **File Processing**: Process CSV, TSV, and SDF files
- **Probability Scores**: Get confidence scores for predictions
- **RESTful API**: Easy-to-use REST endpoints with automatic documentation
- **Command-Line Interface**: Powerful CLI for batch processing and automation
- **Visualization Reports**: Generate comprehensive classification reports with charts
- **CORS Enabled**: Ready for frontend integration

## Model Information

- **Model Type**: XGBoost Ensemble Classifier
- **Dataset**: Set 1 (RNA-binding vs Protein-binding ligands)
- **Input Features**: ECFP6 (Extended Connectivity Fingerprints, radius=3, 2048 bits)
- **Classes**: 
  - Class 0: RNA_binding
  - Class 1: Protein_binding

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

Note: RDKit installation may require conda on some systems:
```bash
conda install -c conda-forge rdkit
pip install -r requirements.txt --ignore-installed rdkit
```

## Recommended Development Environment

Using conda for RDKit and pip for other dependencies ensures smoother installs:

```bash
conda create -n dt-backend python=3.11 -y
conda activate dt-backend
conda install -c conda-forge rdkit=2023.9.4 -y
python -m pip install -r backend/requirements.txt
```

Notes:

- We pin `numpy<2.0` to satisfy `scikit-learn==1.4.x` requirements.
- In CI, RDKit is installed via conda and the rest via `backend/requirements-ci.txt`.
- For reproducibility you can export the environment:

  ```bash
  conda env export --from-history > environment.yml
  ```


## Running the Server

### Development Mode

Start the server with auto-reload:
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Or run directly:
```bash
python app.py
```

### Production Mode

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at: `http://localhost:8000`

## API Documentation

Interactive API documentation is automatically generated and available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### 1. Root Endpoint
```
GET /
```
Returns API information and available endpoints.

**Response:**
```json
{
  "message": "RNA/Protein Binding Classifier API",
  "version": "1.0.0",
  "model": "XGBoost Ensemble (Set 1)",
  "endpoints": {
    "classify": "/api/classify",
    "classify_batch": "/api/classify/batch",
    "classify_pubchem": "/api/classify/pubchem",
    "classify_file": "/api/classify/file",
    "get_job": "/api/jobs/{job_id}",
    "health": "/health",
    "docs": "/docs"
  }
}
```

### 2. Health Check
```
GET /health
```
Check if the server and model are loaded properly.

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true
}
```

### 3. Classify Single Molecule
```
POST /api/classify
```

Classify a single molecule from its SMILES string.

**Request Body:**
```json
{
  "smiles": "CC(C)Cc1ccc(cc1)C(C)C(O)=O"
}
```

**Response:**
```json
{
  "smiles": "CC(C)Cc1ccc(cc1)C(C)C(O)=O",
  "prediction": "RNA_binding",
  "probability_rna": 0.8523,
  "probability_protein": 0.1477,
  "confidence": 0.8523,
  "valid": true,
  "error": null
}
```

### 4. Classify Batch of Molecules
```
POST /api/classify/batch
```

Classify multiple molecules at once.

**Request Body:**
```json
{
  "smiles_list": [
    "CC(C)Cc1ccc(cc1)C(C)C(O)=O",
    "c1ccccc1",
    "CCO"
  ]
}
```

**Response:**
```json
{
  "results": [
    {
      "smiles": "CC(C)Cc1ccc(cc1)C(C)C(O)=O",
      "prediction": "RNA_binding",
      "probability_rna": 0.8523,
      "probability_protein": 0.1477,
      "confidence": 0.8523,
      "valid": true,
      "error": null
    },
    ...
  ],
  "summary": {
    "total": 3,
    "valid": 3,
    "invalid": 0,
    "rna_binding": 2,
    "protein_binding": 1,
    "average_confidence": 0.7845
  }
}
```

### 5. Classify from PubChem
```
POST /api/classify/pubchem
```

Fetch molecules from PubChem and classify them.

**Request Body:**
```json
{
  "compound_ids": ["2244", "aspirin", "caffeine"]
}
```

**Response:**
Similar to batch classification, with molecules fetched from PubChem.

### 6. Classify from File Upload
```
POST /api/classify/file
```

Upload and classify molecules from CSV/TSV/SDF files with streaming support for large datasets.

**Form Parameters:**
- `file` (required): The uploaded file
- `format` (optional, default: "csv"): File format - one of: `csv`, `tsv`, `sdf`
- `smiles_col` (optional, default: "smiles"): Column name containing SMILES strings (for CSV/TSV only)
- `delimiter` (optional, default: ","): Delimiter for CSV files (automatically set to tab for TSV)
- `chunksize` (optional, default: 5000): Number of rows to process per chunk
- `report` (optional, default: false): Whether to generate visualization report
- `output_format` (optional, default: "json"): Response format - one of: `json`, `csv`

**Example Request (using form data):**
```bash
curl -X POST "http://localhost:8000/api/classify/file" \
  -F "file=@molecules.csv" \
  -F "format=csv" \
  -F "smiles_col=smiles" \
  -F "report=true" \
  -F "output_format=json"
```

**Response (JSON format):**
```json
{
  "results": [
    {
      "smiles": "c1ccccc1",
      "prediction": "Protein_binding",
      "probability_rna": 0.0019,
      "probability_protein": 0.9981,
      "confidence": 0.9981,
      "valid": true,
      "error": null
    },
    ...
  ],
  "summary": {
    "total": 100,
    "valid": 98,
    "invalid": 2,
    "rna_binding": 45,
    "protein_binding": 53,
    "average_confidence": 0.8234
  },
  "report_path": "/tmp/classification_report_molecules_csv"
}
```

**Response (CSV format):**
When `output_format=csv`, returns a CSV file with all results and summary in comments.

**Supported File Formats:**
- **CSV**: Comma-separated values with customizable delimiter
- **TSV**: Tab-separated values (delimiter automatically set to tab)
- **SDF**: Structure-Data File format (SMILES extracted from molecular structures)

**Features:**
- Streaming processing for large files (processes in chunks)
- Order preservation - results maintain input order
- Invalid entry tracking - invalid SMILES are marked and counted
- Optional visualization report generation
- Flexible output formats (JSON or CSV)

**Example with Custom Column Name:**
```bash
curl -X POST "http://localhost:8000/api/classify/file" \
  -F "file=@compounds.csv" \
  -F "format=csv" \
  -F "smiles_col=compound_smiles"
```

**Example TSV File:**
```bash
curl -X POST "http://localhost:8000/api/classify/file" \
  -F "file=@molecules.tsv" \
  -F "format=tsv"
```

**Example with Report Generation:**
```bash
curl -X POST "http://localhost:8000/api/classify/file" \
  -F "file=@molecules.csv" \
  -F "report=true"
```

When `report=true`, a visualization report is generated containing:
- Probability distribution plots
- Confidence score visualizations
- Classification summary pie charts
- Statistical summary text file

### 7. Retrieve Stored Job (when persistence is enabled)
```
GET /api/jobs/{job_id}
```

Fetch a previously stored classification job (including summary and all results). This endpoint is available when database persistence is enabled.

**Enabling Persistence**
- Set environment variable `ENABLE_PERSISTENCE=true` (see `docker-compose.yml`).
- The API service expects `DATABASE_URL` (PostgreSQL recommended). Example from `docker-compose.yml`:

```yaml
services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: classifier
      POSTGRES_PASSWORD: classifier_password
      POSTGRES_DB: classifier_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U classifier"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://classifier:classifier_password@db:5432/classifier_db
      - ENABLE_PERSISTENCE=true
    depends_on:
      db:
        condition: service_healthy
```

**Response Example:**
```json
{
  "job_id": "<uuid>",
  "created_at": "2025-11-07T12:34:56Z",
  "input_type": "batch",
  "params": {"smiles_count": 3},
  "status": "completed",
  "duration_ms": 123,
  "summary": {
    "total": 3,
    "valid": 3,
    "invalid": 0,
    "rna_binding": 1,
    "protein_binding": 2,
    "average_confidence": 0.84
  },
  "results": [
    {
      "smiles": "c1ccccc1",
      "prediction": "Protein_binding",
      "probability_rna": 0.002,
      "probability_protein": 0.998,
      "confidence": 0.998,
      "valid": true,
      "error": null
    }
  ]
}
```

## Usage Examples

### Using cURL

**Single molecule classification:**
```bash
curl -X POST "http://localhost:8000/api/classify" \
  -H "Content-Type: application/json" \
  -d '{"smiles": "CC(C)Cc1ccc(cc1)C(C)C(O)=O"}'
```

**Batch classification:**
```bash
curl -X POST "http://localhost:8000/api/classify/batch" \
  -H "Content-Type: application/json" \
  -d '{"smiles_list": ["c1ccccc1", "CCO", "CC(=O)O"]}'
```

**PubChem classification:**
```bash
curl -X POST "http://localhost:8000/api/classify/pubchem" \
  -H "Content-Type: application/json" \
  -d '{"compound_ids": ["2244", "aspirin"]}'
```

### Using Python

```python
import requests

# Single molecule
response = requests.post(
    "http://localhost:8000/api/classify",
    json={"smiles": "c1ccccc1"}
)
result = response.json()
print(f"Prediction: {result['prediction']}")
print(f"Confidence: {result['confidence']:.2%}")

# Batch processing
response = requests.post(
    "http://localhost:8000/api/classify/batch",
    json={"smiles_list": ["c1ccccc1", "CCO", "CC(=O)O"]}
)
results = response.json()
print(f"Total: {results['summary']['total']}")
print(f"RNA binding: {results['summary']['rna_binding']}")
print(f"Protein binding: {results['summary']['protein_binding']}")

# PubChem integration
response = requests.post(
    "http://localhost:8000/api/classify/pubchem",
    json={"compound_ids": ["2244", "aspirin"]}
)
results = response.json()
for r in results['results']:
    if r['valid']:
        print(f"{r['smiles']}: {r['prediction']} ({r['confidence']:.2%})")
```

### Using JavaScript/fetch

```javascript
// Single molecule
fetch('http://localhost:8000/api/classify', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    smiles: 'c1ccccc1'
  })
})
.then(response => response.json())
.then(data => {
  console.log('Prediction:', data.prediction);
  console.log('Confidence:', data.confidence);
});

// Batch processing
fetch('http://localhost:8000/api/classify/batch', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    smiles_list: ['c1ccccc1', 'CCO', 'CC(=O)O']
  })
})
.then(response => response.json())
.then(data => {
  console.log('Summary:', data.summary);
  console.log('Results:', data.results);
});
```

## Command-Line Interface (CLI)

The backend includes a powerful command-line interface for batch processing and automation. The CLI shares the same core logic as the API, ensuring consistent results.

### CLI Installation

The CLI is automatically available after installing the backend dependencies:

```bash
pip install -r requirements.txt
```

### CLI Usage

Run the CLI with:

```bash
python -m backend.cli [COMMAND] [OPTIONS]
```

Or from the backend directory:

```bash
python -m cli [COMMAND] [OPTIONS]
```

### Available Commands

#### 1. Classify SMILES Strings

Classify one or more SMILES strings directly from the command line.

**Basic usage:**
```bash
python -m backend.cli classify smiles "c1ccccc1"
```

**Multiple SMILES:**
```bash
python -m backend.cli classify smiles "c1ccccc1" "CCO" "CC(=O)O"
```

**JSON output (default):**
```bash
python -m backend.cli classify smiles "c1ccccc1" --output-format json
```

**CSV output:**
```bash
python -m backend.cli classify smiles "c1ccccc1" "CCO" --output-format csv
```

**Save to file:**
```bash
python -m backend.cli classify smiles "c1ccccc1" --output results.json
python -m backend.cli classify smiles "c1ccccc1" --output-format csv --output results.csv
```

**Generate visualization report:**
```bash
python -m backend.cli classify smiles "c1ccccc1" "CCO" "CC(=O)O" --report ./report_dir
```

#### 2. Classify from File

Process molecules from CSV, TSV, or SDF files.

**CSV file:**
```bash
python -m backend.cli classify file --path molecules.csv --format csv
```

**TSV file:**
```bash
python -m backend.cli classify file --path molecules.tsv --format tsv
```

**SDF file:**
```bash
python -m backend.cli classify file --path molecules.sdf --format sdf
```

**Custom SMILES column:**
```bash
python -m backend.cli classify file --path data.csv --format csv --smiles-col "smiles_column"
```

**Custom delimiter:**
```bash
python -m backend.cli classify file --path data.txt --format csv --delimiter "|"
```

**Process in chunks (for large files):**
```bash
python -m backend.cli classify file --path large_file.csv --format csv --chunksize 1000
```

**Complete example with all options:**
```bash
python -m backend.cli classify file \
  --path molecules.csv \
  --format csv \
  --smiles-col "smiles" \
  --output-format csv \
  --output results.csv \
  --report ./report
```

#### 3. Classify from PubChem

Fetch molecules from PubChem and classify them.

**By CID:**
```bash
python -m backend.cli classify pubchem --id 2244
```

**By compound name:**
```bash
python -m backend.cli classify pubchem --id aspirin
```

**Multiple compounds:**
```bash
python -m backend.cli classify pubchem --id 2244 --id aspirin --id caffeine
```

**With output options:**
```bash
python -m backend.cli classify pubchem \
  --id 2244 \
  --id aspirin \
  --output-format csv \
  --output pubchem_results.csv \
  --report ./pubchem_report
```

### CLI Output Formats

#### JSON Output

The default output format matches the API response schema:

```json
{
  "results": [
    {
      "smiles": "c1ccccc1",
      "prediction": "Protein_binding",
      "probability_rna": 0.0019,
      "probability_protein": 0.9981,
      "confidence": 0.9981,
      "valid": true,
      "error": null
    }
  ],
  "summary": {
    "total": 1,
    "valid": 1,
    "invalid": 0,
    "rna_binding": 0,
    "protein_binding": 1,
    "average_confidence": 0.9981
  }
}
```

#### CSV Output

CSV format includes all classification details:

```csv
smiles,prediction,probability_rna,probability_protein,confidence,valid,error
c1ccccc1,Protein_binding,0.0019,0.9981,0.9981,True,
CCO,Protein_binding,0.0041,0.9959,0.9959,True,
```

### Visualization Reports

When using the `--report` option, the CLI generates a comprehensive report including:

- **probability_distribution.png**: Histograms of RNA and Protein binding probabilities
- **confidence_scores.png**: Box plots of confidence scores by prediction type
- **classification_summary.png**: Pie chart showing classification breakdown
- **summary.txt**: Text file with detailed statistics

Example:
```bash
python -m backend.cli classify smiles "c1ccccc1" "CCO" "CC(=O)O" --report ./my_report
```

This creates a `my_report/` directory with all visualization files.

### CLI Examples

**Example 1: Quick classification of a few molecules**
```bash
python -m backend.cli classify smiles "c1ccccc1" "CCO" "CC(=O)O"
```

**Example 2: Process a CSV file and save results**
```bash
python -m backend.cli classify file \
  --path input.csv \
  --format csv \
  --output-format csv \
  --output results.csv
```

**Example 3: Classify PubChem compounds with visualization**
```bash
python -m backend.cli classify pubchem \
  --id aspirin \
  --id ibuprofen \
  --id acetaminophen \
  --report ./drug_analysis
```

**Example 4: Process a large file in chunks**
```bash
python -m backend.cli classify file \
  --path large_library.csv \
  --format csv \
  --chunksize 1000 \
  --output-format csv \
  --output results.csv
```

### CLI vs API

Both the CLI and API use the same core classification logic from `backend/core.py`, ensuring:

- **Consistent Results**: Same predictions for the same input
- **Shared Model**: Single model instance loaded once
- **Identical Features**: Same ECFP6 fingerprint generation
- **Compatible Output**: CLI JSON format matches API response schema

Use the **CLI** when:
- Processing batch files locally
- Automating classification pipelines
- Working in command-line environments
- Generating offline reports

Use the **API** when:
- Building web applications
- Integrating with other services
- Real-time classification needs
- Multi-user concurrent access

### CLI Help

Get help on any command:

```bash
python -m backend.cli --help
python -m backend.cli classify --help
python -m backend.cli classify smiles --help
python -m backend.cli classify file --help
python -m backend.cli classify pubchem --help
```

## Error Handling

The API returns appropriate HTTP status codes:

- `200`: Success
- `422`: Validation Error (invalid request format)
- `503`: Service Unavailable (model not loaded)
- `500`: Internal Server Error

Error responses include detailed messages:
```json
{
  "detail": "Model not loaded"
}
```

## Model Details

The classification model uses ECFP6 (Extended-Connectivity Fingerprints) molecular descriptors:

- **Fingerprint Type**: Morgan/Circular fingerprints
- **Radius**: 3 (equivalent to ECFP6)
- **Bits**: 2048
- **Algorithm**: XGBoost ensemble classifier

The model was trained on curated datasets of RNA-binding and Protein-binding ligands from multiple chemical libraries (Enamine, ChemDiv, Life Chemicals, ROBIN).

## Frontend Integration

This backend is designed to be easily integrated with a frontend application. CORS is enabled for all origins in development mode. For production, update the CORS settings in `app.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],  # Update this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Troubleshooting

### RDKit Installation Issues

If you encounter issues installing RDKit via pip, use conda:
```bash
conda create -n rna-classifier python=3.10
conda activate rna-classifier
conda install -c conda-forge rdkit
pip install -r requirements.txt --ignore-installed rdkit
```

### Model Not Found

Ensure the model file exists at:
```
../models/ensemble/set1/best_xgb.joblib
```

The path is relative to the `backend/` directory.

### Port Already in Use

If port 8000 is already in use, specify a different port:
```bash
uvicorn app:app --port 8080
```

## Example Scripts and Utilities

The `backend/` directory includes several utility scripts to help you get started:

### Test Script

Run the basic test to verify the installation:
```bash
python test_classifier.py
```

This will:
- Load the model
- Test SMILES to fingerprint conversion
- Classify several example molecules
- Verify error handling

### Example Client

A Python client library for easy API integration:
```bash
python example_client.py
```

The `example_client.py` module provides a `RNAProteinClassifierClient` class that you can import into your own projects:

```python
from example_client import RNAProteinClassifierClient

client = RNAProteinClassifierClient("http://localhost:8000")
result = client.classify_molecule("c1ccccc1")
print(f"Prediction: {result['prediction']}")
```

### Complete Demo

Run a comprehensive demonstration of all features:
```bash
python demo.py
```

This will:
- Perform health checks
- Classify molecules from different categories
- Generate batch predictions
- Attempt PubChem integration (if internet available)
- Create visualization reports

### Visualization Tools

The `visualize.py` module provides functions to create plots and reports:

```python
from visualize import generate_report

# After getting results from the API
generate_report(results_data, output_dir="/tmp/my_report")
```

This generates:
- Probability distribution plots
- Confidence score visualizations
- Classification summary pie charts
- Statistical summary text files

### Quick Start Script

Use the automated startup script:
```bash
./start.sh
```

This will:
- Create and activate a virtual environment
- Install dependencies
- Run tests
- Start the API server

## License

See the main repository LICENSE file.

## Citation

If you use this tool in your research, please cite the original thesis:

Fulop, J. (2024). Cheminformatics Analysis of RNA-Binding Ligands. Diploma Thesis, UCT Prague.

## Contact

For issues and questions, please open an issue in the GitHub repository.
