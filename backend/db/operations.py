"""
Database operations for classification job persistence.

This module provides helper functions to persist classification jobs
and retrieve them from the database.
"""

import os
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from .models import Job, Molecule, Prediction


def is_persistence_enabled() -> bool:
    """Check if database persistence is enabled via environment variable."""
    return os.getenv("ENABLE_PERSISTENCE", "false").lower() in ("true", "1", "yes")


def create_job(
    db: Session,
    input_type: str,
    params: Optional[Dict] = None,
    summary: Optional[Dict] = None,
    duration_ms: Optional[int] = None,
) -> Job:
    """
    Create a new classification job in the database.
    
    Args:
        db: Database session
        input_type: Type of input (smiles, batch, file, pubchem)
        params: Optional parameters dictionary
        summary: Optional summary statistics
        duration_ms: Processing duration in milliseconds
    
    Returns:
        Job: Created Job object
    """
    job = Job(
        input_type=input_type,
        params=params,
        summary=summary,
        duration_ms=duration_ms,
        status="completed",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def add_molecules_and_predictions(
    db: Session,
    job: Job,
    results: List[Dict],
) -> None:
    """
    Add molecules and their predictions to a job.
    
    Args:
        db: Database session
        job: Job object to add molecules to
        results: List of classification results
    """
    for result in results:
        # Create molecule
        molecule = Molecule(
            job_id=job.id,
            input_smiles=result["smiles"],
            normalized_smiles=result.get("smiles"),  # Could add canonicalization later
            is_valid=result["valid"],
            error=result.get("error"),
        )
        db.add(molecule)
        db.flush()  # Get molecule ID
        
        # Create prediction if molecule is valid
        if result["valid"]:
            prediction = Prediction(
                molecule_id=molecule.id,
                label=result["prediction"],
                probability_rna=result["probability_rna"],
                probability_protein=result["probability_protein"],
                confidence=result["confidence"],
            )
            db.add(prediction)
    
    db.commit()


def get_job(db: Session, job_id: str) -> Optional[Job]:
    """
    Retrieve a job by ID with all related data.
    
    Args:
        db: Database session
        job_id: Job UUID
    
    Returns:
        Job object or None if not found
    """
    return db.query(Job).filter(Job.id == job_id).first()


def get_job_results(db: Session, job_id: str) -> Optional[Dict]:
    """
    Get full results for a job including all molecules and predictions.
    
    Args:
        db: Database session
        job_id: Job UUID
    
    Returns:
        Dictionary with job metadata and results, or None if not found
    """
    job = get_job(db, job_id)
    if not job:
        return None
    
    results = []
    for molecule in job.molecules:
        result = {
            "smiles": molecule.input_smiles,
            "valid": molecule.is_valid,
            "error": molecule.error,
        }
        
        if molecule.is_valid and molecule.prediction:
            result.update({
                "prediction": molecule.prediction.label,
                "probability_rna": molecule.prediction.probability_rna,
                "probability_protein": molecule.prediction.probability_protein,
                "confidence": molecule.prediction.confidence,
            })
        else:
            result.update({
                "prediction": "Invalid",
                "probability_rna": 0.0,
                "probability_protein": 0.0,
                "confidence": 0.0,
            })
        
        results.append(result)
    
    return {
        "job_id": job.id,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "input_type": job.input_type,
        "params": job.params,
        "status": job.status,
        "duration_ms": job.duration_ms,
        "summary": job.summary,
        "results": results,
    }
