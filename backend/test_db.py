"""
Tests for database persistence functionality.

This test suite verifies that classification jobs can be persisted
to the database and retrieved correctly.
"""

import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.models import Base, Job, Molecule, Prediction
from db import operations as db_ops


# Test database URL (SQLite in-memory)
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture
def test_db():
    """Create a test database session."""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_create_job(test_db):
    """Test creating a classification job."""
    job = db_ops.create_job(
        db=test_db,
        input_type="batch",
        params={"smiles_count": 3},
        summary={"total": 3, "valid": 3, "invalid": 0},
        duration_ms=150
    )
    
    assert job.id is not None
    assert job.input_type == "batch"
    assert job.params["smiles_count"] == 3
    assert job.summary["total"] == 3
    assert job.duration_ms == 150
    assert job.status == "completed"


def test_add_molecules_and_predictions(test_db):
    """Test adding molecules and predictions to a job."""
    # Create a job
    job = db_ops.create_job(
        db=test_db,
        input_type="batch",
        params={"smiles_count": 2},
        summary={"total": 2, "valid": 2, "invalid": 0},
        duration_ms=100
    )
    
    # Sample results
    results = [
        {
            "smiles": "c1ccccc1",
            "prediction": "Protein_binding",
            "probability_rna": 0.001,
            "probability_protein": 0.999,
            "confidence": 0.999,
            "valid": True,
            "error": None
        },
        {
            "smiles": "CCO",
            "prediction": "RNA_binding",
            "probability_rna": 0.95,
            "probability_protein": 0.05,
            "confidence": 0.95,
            "valid": True,
            "error": None
        }
    ]
    
    # Add molecules and predictions
    db_ops.add_molecules_and_predictions(test_db, job, results)
    
    # Verify molecules were added
    molecules = test_db.query(Molecule).filter(Molecule.job_id == job.id).all()
    assert len(molecules) == 2
    assert molecules[0].input_smiles == "c1ccccc1"
    assert molecules[0].is_valid is True
    assert molecules[1].input_smiles == "CCO"
    
    # Verify predictions were added
    predictions = test_db.query(Prediction).all()
    assert len(predictions) == 2
    assert predictions[0].label == "Protein_binding"
    assert predictions[0].confidence == 0.999
    assert predictions[1].label == "RNA_binding"
    assert predictions[1].confidence == 0.95


def test_add_invalid_molecules(test_db):
    """Test adding invalid molecules without predictions."""
    job = db_ops.create_job(
        db=test_db,
        input_type="batch",
        params={"smiles_count": 1},
        summary={"total": 1, "valid": 0, "invalid": 1},
        duration_ms=50
    )
    
    results = [
        {
            "smiles": "INVALID_SMILES",
            "prediction": "Invalid",
            "probability_rna": 0.0,
            "probability_protein": 0.0,
            "confidence": 0.0,
            "valid": False,
            "error": "Invalid SMILES string"
        }
    ]
    
    db_ops.add_molecules_and_predictions(test_db, job, results)
    
    molecules = test_db.query(Molecule).filter(Molecule.job_id == job.id).all()
    assert len(molecules) == 1
    assert molecules[0].is_valid is False
    assert molecules[0].error == "Invalid SMILES string"
    
    # Should not have predictions for invalid molecules
    predictions = test_db.query(Prediction).all()
    assert len(predictions) == 0


def test_get_job(test_db):
    """Test retrieving a job by ID."""
    # Create a job
    job = db_ops.create_job(
        db=test_db,
        input_type="pubchem",
        params={"compound_ids": ["2244"]},
        summary={"total": 1, "valid": 1, "invalid": 0},
        duration_ms=200
    )
    
    # Retrieve the job
    retrieved_job = db_ops.get_job(test_db, job.id)
    
    assert retrieved_job is not None
    assert retrieved_job.id == job.id
    assert retrieved_job.input_type == "pubchem"
    assert retrieved_job.params["compound_ids"] == ["2244"]


def test_get_nonexistent_job(test_db):
    """Test retrieving a job that doesn't exist."""
    result = db_ops.get_job(test_db, "nonexistent-id")
    assert result is None


def test_get_job_results(test_db):
    """Test retrieving full job results."""
    # Create a job
    job = db_ops.create_job(
        db=test_db,
        input_type="batch",
        params={"smiles_count": 2},
        summary={"total": 2, "valid": 2, "invalid": 0},
        duration_ms=150
    )
    
    # Add molecules and predictions
    results = [
        {
            "smiles": "c1ccccc1",
            "prediction": "Protein_binding",
            "probability_rna": 0.002,
            "probability_protein": 0.998,
            "confidence": 0.998,
            "valid": True,
            "error": None
        },
        {
            "smiles": "CCO",
            "prediction": "RNA_binding",
            "probability_rna": 0.85,
            "probability_protein": 0.15,
            "confidence": 0.85,
            "valid": True,
            "error": None
        }
    ]
    db_ops.add_molecules_and_predictions(test_db, job, results)
    
    # Retrieve full job results
    job_data = db_ops.get_job_results(test_db, job.id)
    
    assert job_data is not None
    assert job_data["job_id"] == job.id
    assert job_data["input_type"] == "batch"
    assert job_data["status"] == "completed"
    assert len(job_data["results"]) == 2
    
    # Check first result
    result_0 = job_data["results"][0]
    assert result_0["smiles"] == "c1ccccc1"
    assert result_0["prediction"] == "Protein_binding"
    assert result_0["confidence"] == 0.998
    assert result_0["valid"] is True
    
    # Check second result
    result_1 = job_data["results"][1]
    assert result_1["smiles"] == "CCO"
    assert result_1["prediction"] == "RNA_binding"
    assert result_1["confidence"] == 0.85
    assert result_1["valid"] is True


def test_is_persistence_enabled():
    """Test persistence enabled flag."""
    # Without env var, should be disabled
    os.environ.pop("ENABLE_PERSISTENCE", None)
    assert db_ops.is_persistence_enabled() is False
    
    # With env var set to true
    os.environ["ENABLE_PERSISTENCE"] = "true"
    assert db_ops.is_persistence_enabled() is True
    
    # With env var set to 1
    os.environ["ENABLE_PERSISTENCE"] = "1"
    assert db_ops.is_persistence_enabled() is True
    
    # With env var set to yes
    os.environ["ENABLE_PERSISTENCE"] = "yes"
    assert db_ops.is_persistence_enabled() is True
    
    # With env var set to false
    os.environ["ENABLE_PERSISTENCE"] = "false"
    assert db_ops.is_persistence_enabled() is False
    
    # Cleanup
    os.environ.pop("ENABLE_PERSISTENCE", None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
