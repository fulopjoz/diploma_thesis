# PostgreSQL Persistence for Classification Jobs

This directory contains the database layer for persisting classification jobs and results.

## Overview

The classifier can optionally persist all classification jobs to a PostgreSQL database, allowing you to:
- Track all classification requests
- Retrieve historical results
- Audit model usage
- Analyze classification patterns over time

## Database Schema

### Tables

**jobs**
- `id` (String/UUID): Unique job identifier
- `created_at` (DateTime): Timestamp when job was created
- `updated_at` (DateTime): Timestamp when job was last updated
- `input_type` (String): Type of input (batch, pubchem, file, smiles)
- `params` (JSON): Input parameters (e.g., SMILES count, compound IDs)
- `status` (String): Job status (completed, failed, processing)
- `duration_ms` (Integer): Processing duration in milliseconds
- `summary` (JSON): Summary statistics (total, valid, invalid counts, etc.)
- `report_path` (String): Optional path to generated report

**molecules**
- `id` (Integer): Unique molecule identifier
- `job_id` (String/UUID): Foreign key to jobs table
- `input_smiles` (Text): Original SMILES string
- `normalized_smiles` (Text): Normalized/canonical SMILES
- `is_valid` (Boolean): Whether the SMILES is valid
- `error` (Text): Error message if invalid

**predictions**
- `id` (Integer): Unique prediction identifier
- `molecule_id` (Integer): Foreign key to molecules table
- `label` (String): Classification label (RNA_binding, Protein_binding, Invalid)
- `probability_rna` (Float): Probability of RNA binding
- `probability_protein` (Float): Probability of Protein binding
- `confidence` (Float): Confidence score (max probability)

## Configuration

### Environment Variables

- `DATABASE_URL`: PostgreSQL connection string (default: SQLite for testing)
  - Format: `postgresql://user:password@host:port/database`
  - Example: `postgresql://classifier:password@localhost:5432/classifier_db`

- `ENABLE_PERSISTENCE`: Enable/disable database persistence (default: false)
  - Set to `true`, `1`, or `yes` to enable

### Docker Compose

The docker-compose.yml includes a PostgreSQL service:

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
```

## Usage

### Starting with Docker Compose

```bash
# Start services with persistence enabled
docker compose up -d

# Check that persistence is enabled
curl http://localhost:8000/
# Should show "persistence_enabled": true
```

### Making Requests

When persistence is enabled, batch classification endpoints return a `job_id`:

```bash
# Classify a batch of molecules
curl -X POST "http://localhost:8000/api/classify/batch" \
  -H "Content-Type: application/json" \
  -d '{"smiles_list": ["c1ccccc1", "CCO"]}'

# Response includes job_id:
# {
#   "results": [...],
#   "summary": {...},
#   "job_id": "d48034c1-c3ea-473e-86a9-bcecddb58edf"
# }
```

### Retrieving Job Results

```bash
# Get job by ID
curl "http://localhost:8000/api/jobs/d48034c1-c3ea-473e-86a9-bcecddb58edf"

# Response includes full job metadata and results:
# {
#   "job_id": "...",
#   "created_at": "2025-11-06T14:10:47.219620",
#   "input_type": "batch",
#   "params": {...},
#   "summary": {...},
#   "results": [...]
# }
```

## Files

- `session.py`: Database engine and session management
- `models.py`: SQLAlchemy ORM models (Job, Molecule, Prediction)
- `operations.py`: Database operations (create, retrieve jobs)
- `__init__.py`: Package initialization

## Testing

### Unit Tests

```bash
# Run database unit tests
cd backend
python -m pytest test_db.py -v
```

### Integration Tests

```bash
# Start services
docker compose up -d

# Wait for services to be healthy
sleep 10

# Run integration test
./backend/test_integration.sh
```

## Development

### Local Development Without Docker

```bash
# The application falls back to SQLite when DATABASE_URL is not set
cd backend
python app.py

# Persistence will use SQLite: test_classifier.db
# To enable persistence with SQLite:
export ENABLE_PERSISTENCE=true
python app.py
```

### Connecting to PostgreSQL

```bash
# Connect to the PostgreSQL database
docker compose exec db psql -U classifier classifier_db

# List tables
\dt

# Query jobs
SELECT id, input_type, created_at, summary FROM jobs ORDER BY created_at DESC LIMIT 10;

# Query molecules for a job
SELECT m.input_smiles, m.is_valid, p.label, p.confidence 
FROM molecules m 
LEFT JOIN predictions p ON m.id = p.molecule_id 
WHERE m.job_id = 'your-job-id-here';
```

## Migration Notes

- Database tables are automatically created on application startup
- For production, consider using Alembic for schema migrations
- The current implementation does not include automatic migration support

## Performance Considerations

- Database writes add ~5-10ms overhead per batch classification
- For high-throughput scenarios, consider:
  - Batch inserts
  - Async database operations
  - Connection pooling (already configured)
  - Read replicas for analytics queries

## Security

- Change default PostgreSQL credentials in production
- Use environment variables or secrets management for credentials
- Enable SSL for PostgreSQL connections in production
- Implement access controls and authentication for the API
- Consider data retention policies for old jobs
