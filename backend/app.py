"""
FastAPI backend for RNA/Protein binding molecule classification.

This application provides endpoints to classify molecules as RNA-binding or 
Protein-binding using a pre-trained XGBoost ensemble model.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from contextlib import asynccontextmanager
import os
import time

# Database imports
from sqlalchemy.orm import Session
from db.session import get_db, engine
from db.models import Base
from db import operations as db_ops

# Import shared core functionality
from core import (
    smiles_to_ecfp6,
    classify_smiles_list,
    ClassificationResult as CoreClassificationResult,
    MODEL_PATH,
    get_model
)

# Module-level model reference for compatibility
model = None

# Load model on startup using lifespan for FastAPI 0.109+
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the XGBoost model on startup and cleanup on shutdown."""
    global model
    try:
        model = get_model()
        print(f"Model loaded successfully from {MODEL_PATH}")
    except Exception as e:
        print(f"Error loading model: {e}")
        raise
    
    # Initialize database tables
    try:
        Base.metadata.create_all(bind=engine)
        print("Database tables initialized")
        if db_ops.is_persistence_enabled():
            print("Database persistence is ENABLED")
        else:
            print("Database persistence is DISABLED (set ENABLE_PERSISTENCE=true to enable)")
    except Exception as e:
        print(f"Warning: Database initialization failed: {e}")
        print("Continuing without database persistence...")
    
    yield
    # Cleanup (if needed)
    print("Shutting down...")

# Initialize FastAPI app with lifespan
app = FastAPI(
    title="RNA/Protein Binding Classifier",
    description="Binary classification of molecules as RNA-binding or Protein-binding",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for request/response
class MoleculeInput(BaseModel):
<<<<<<< HEAD
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "smiles": "CC(C)Cc1ccc(cc1)C(C)C(O)=O"
=======
    smiles: str = Field(..., description="SMILES string of the molecule")
    
    class Config:
        json_schema_extra = {
            "example": {
                "smiles": "CC(C)Cc1ccc(cc1)C(C)C(O)=O"
            }
>>>>>>> origin/copilot/add-file-upload-api
        }
    })
    
    smiles: str = Field(..., description="SMILES string of the molecule")


class MoleculesBatchInput(BaseModel):
<<<<<<< HEAD
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "smiles_list": [
                "CC(C)Cc1ccc(cc1)C(C)C(O)=O",
                "c1ccccc1"
            ]
=======
    smiles_list: List[str] = Field(..., description="List of SMILES strings")
    
    class Config:
        json_schema_extra = {
            "example": {
                "smiles_list": [
                    "CC(C)Cc1ccc(cc1)C(C)C(O)=O",
                    "c1ccccc1"
                ]
            }
>>>>>>> origin/copilot/add-file-upload-api
        }
    })
    
    smiles_list: List[str] = Field(..., description="List of SMILES strings")


class PubChemInput(BaseModel):
<<<<<<< HEAD
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "compound_ids": ["2244", "aspirin"]
=======
    compound_ids: List[str] = Field(..., description="List of PubChem CIDs or compound names")
    
    class Config:
        json_schema_extra = {
            "example": {
                "compound_ids": ["2244", "aspirin"]
            }
>>>>>>> origin/copilot/add-file-upload-api
        }
    })
    
    compound_ids: List[str] = Field(..., description="List of PubChem CIDs or compound names")


class ClassificationResult(BaseModel):
    smiles: str
    prediction: str = Field(..., description="RNA_binding or Protein_binding")
    probability_rna: float = Field(..., description="Probability of RNA binding")
    probability_protein: float = Field(..., description="Probability of Protein binding")
    confidence: float = Field(..., description="Confidence score (max probability)")
    valid: bool = Field(..., description="Whether the SMILES is valid")
    error: Optional[str] = None


class BatchClassificationResult(BaseModel):
    results: List[ClassificationResult]
    summary: dict
    job_id: Optional[str] = Field(None, description="Job ID if persistence is enabled")


class JobResponse(BaseModel):
    job_id: str
    created_at: str
    input_type: str
    params: Optional[dict] = None
    status: str
    duration_ms: Optional[int] = None
    summary: Optional[dict] = None
    results: List[ClassificationResult]


def classify_molecule(smiles: str) -> ClassificationResult:
    """
    Classify a single molecule using core logic.
    
    Args:
        smiles: SMILES string
    
    Returns:
        ClassificationResult object
    """
    results, _ = classify_smiles_list([smiles])
    core_result = results[0]
    
    # Convert core ClassificationResult to Pydantic model
    return ClassificationResult(
        smiles=core_result.smiles,
        prediction=core_result.prediction,
        probability_rna=core_result.probability_rna,
        probability_protein=core_result.probability_protein,
        confidence=core_result.confidence,
        valid=core_result.valid,
        error=core_result.error
    )


# API Endpoints
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "RNA/Protein Binding Classifier API",
        "version": "1.0.0",
        "model": "XGBoost Ensemble (Set 1)",
        "endpoints": {
            "classify": "/api/classify",
            "classify_batch": "/api/classify/batch",
            "classify_pubchem": "/api/classify/pubchem",
            "get_job": "/api/jobs/{job_id}",
            "health": "/health",
            "docs": "/docs"
        },
        "persistence_enabled": db_ops.is_persistence_enabled()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model_loaded": model is not None
    }


@app.post("/api/classify", response_model=ClassificationResult)
async def classify_single(molecule: MoleculeInput):
    """
    Classify a single molecule from SMILES string.
    
    Args:
        molecule: MoleculeInput with SMILES string
    
    Returns:
        ClassificationResult with prediction and probabilities
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    return classify_molecule(molecule.smiles)


@app.post("/api/classify/batch", response_model=BatchClassificationResult)
async def classify_batch(molecules: MoleculesBatchInput, db: Session = Depends(get_db)):
    """
    Classify multiple molecules from SMILES strings.
    
    Args:
        molecules: MoleculesBatchInput with list of SMILES strings
        db: Database session (optional, for persistence)
    
    Returns:
        BatchClassificationResult with all predictions and summary statistics
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
<<<<<<< HEAD
    # Use core classify_smiles_list function
    core_results, summary = classify_smiles_list(molecules.smiles_list)
=======
    start_time = time.time()
    
    results = []
    for smiles in molecules.smiles_list:
        result = classify_molecule(smiles)
        results.append(result)
>>>>>>> origin/copilot/add-file-upload-api
    
    # Convert core results to Pydantic models
    results = [
        ClassificationResult(
            smiles=r.smiles,
            prediction=r.prediction,
            probability_rna=r.probability_rna,
            probability_protein=r.probability_protein,
            confidence=r.confidence,
            valid=r.valid,
            error=r.error
        )
        for r in core_results
    ]
    
    duration_ms = int((time.time() - start_time) * 1000)
    job_id = None
    
    # Optionally persist to database
    if db_ops.is_persistence_enabled():
        try:
            job = db_ops.create_job(
                db=db,
                input_type="batch",
                params={"smiles_count": len(molecules.smiles_list)},
                summary=summary,
                duration_ms=duration_ms
            )
            # Convert results to dicts for persistence
            results_dicts = [r.model_dump() for r in results]
            db_ops.add_molecules_and_predictions(db, job, results_dicts)
            job_id = job.id
        except Exception as e:
            print(f"Warning: Failed to persist job to database: {e}")
    
    return BatchClassificationResult(results=results, summary=summary, job_id=job_id)


@app.post("/api/classify/pubchem", response_model=BatchClassificationResult)
async def classify_from_pubchem(pubchem_input: PubChemInput, db: Session = Depends(get_db)):
    """
    Fetch molecules from PubChem and classify them.
    
    Args:
        pubchem_input: PubChemInput with list of compound IDs or names
        db: Database session (optional, for persistence)
    
    Returns:
        BatchClassificationResult with all predictions and summary statistics
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        import pubchempy as pcp
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="PubChemPy not installed. Install with: pip install pubchempy"
        )
    
<<<<<<< HEAD
    smiles_list = []
    errors = {}
    
=======
    start_time = time.time()
    
    results = []
>>>>>>> origin/copilot/add-file-upload-api
    for compound_id in pubchem_input.compound_ids:
        try:
            # Try to get compound by CID or name
            compounds = pcp.get_compounds(compound_id, 'name')
            if not compounds:
                # Try as CID
                compounds = [pcp.Compound.from_cid(compound_id)]
            
            if compounds and compounds[0]:
                smiles_list.append(compounds[0].canonical_smiles)
            else:
                smiles_list.append("")
                errors[len(smiles_list) - 1] = f"Compound not found: {compound_id}"
        except Exception as e:
            smiles_list.append("")
            errors[len(smiles_list) - 1] = f"Error fetching {compound_id}: {str(e)}"
    
    # Classify all SMILES using core function
    core_results, summary = classify_smiles_list(smiles_list)
    
    # Convert core results to Pydantic models, applying PubChem-specific errors
    results = [
        ClassificationResult(
            smiles=r.smiles,
            prediction=r.prediction,
            probability_rna=r.probability_rna,
            probability_protein=r.probability_protein,
            confidence=r.confidence,
            valid=r.valid,
            error=errors.get(idx, r.error)  # Use PubChem error if available, otherwise core error
        )
        for idx, r in enumerate(core_results)
    ]
    
    duration_ms = int((time.time() - start_time) * 1000)
    job_id = None
    
    # Optionally persist to database
    if db_ops.is_persistence_enabled():
        try:
            job = db_ops.create_job(
                db=db,
                input_type="pubchem",
                params={"compound_ids": pubchem_input.compound_ids},
                summary=summary,
                duration_ms=duration_ms
            )
            # Convert results to dicts for persistence
            results_dicts = [r.model_dump() for r in results]
            db_ops.add_molecules_and_predictions(db, job, results_dicts)
            job_id = job.id
        except Exception as e:
            print(f"Warning: Failed to persist job to database: {e}")
    
    return BatchClassificationResult(results=results, summary=summary, job_id=job_id)


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, db: Session = Depends(get_db)):
    """
    Retrieve a stored classification job by ID.
    
    Args:
        job_id: Job UUID
        db: Database session
    
    Returns:
        JobResponse with job metadata and all results
    
    Raises:
        HTTPException: If persistence is not enabled or job not found
    """
    if not db_ops.is_persistence_enabled():
        raise HTTPException(
            status_code=501,
            detail="Database persistence is not enabled. Set ENABLE_PERSISTENCE=true to enable."
        )
    
    job_data = db_ops.get_job_results(db, job_id)
    if not job_data:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    # Convert results dict to ClassificationResult objects
    results = [ClassificationResult(**r) for r in job_data["results"]]
    
    return JobResponse(
        job_id=job_data["job_id"],
        created_at=job_data["created_at"],
        input_type=job_data["input_type"],
        params=job_data["params"],
        status=job_data["status"],
        duration_ms=job_data["duration_ms"],
        summary=job_data["summary"],
        results=results
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
