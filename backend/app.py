"""
FastAPI backend for RNA/Protein binding molecule classification.

This application provides endpoints to classify molecules as RNA-binding or 
Protein-binding using a pre-trained XGBoost ensemble model.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from contextlib import asynccontextmanager
import joblib
import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit import RDLogger
import os
import time

# Database imports
from sqlalchemy.orm import Session
from db.session import get_db, engine
from db.models import Base
from db import operations as db_ops

# Disable RDKit warnings
RDLogger.DisableLog('rdApp.error')

# Load the pre-trained model
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "ensemble", "set1", "best_xgb.joblib")
model = None

# Load model on startup using lifespan for FastAPI 0.109+
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the XGBoost model on startup and cleanup on shutdown."""
    global model
    try:
        model = joblib.load(MODEL_PATH)
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
    smiles: str = Field(..., description="SMILES string of the molecule")
    
    class Config:
        json_schema_extra = {
            "example": {
                "smiles": "CC(C)Cc1ccc(cc1)C(C)C(O)=O"
            }
        }


class MoleculesBatchInput(BaseModel):
    smiles_list: List[str] = Field(..., description="List of SMILES strings")
    
    class Config:
        json_schema_extra = {
            "example": {
                "smiles_list": [
                    "CC(C)Cc1ccc(cc1)C(C)C(O)=O",
                    "c1ccccc1"
                ]
            }
        }


class PubChemInput(BaseModel):
    compound_ids: List[str] = Field(..., description="List of PubChem CIDs or compound names")
    
    class Config:
        json_schema_extra = {
            "example": {
                "compound_ids": ["2244", "aspirin"]
            }
        }


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


# Helper functions
def smiles_to_ecfp6(smiles: str, radius: int = 3, n_bits: int = 2048) -> Optional[np.ndarray]:
    """
    Convert SMILES string to ECFP6 fingerprint.
    
    Args:
        smiles: SMILES string
        radius: Morgan fingerprint radius (3 for ECFP6)
        n_bits: Number of bits in the fingerprint
    
    Returns:
        Numpy array of fingerprint or None if invalid
    """
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return None
        
        # Generate Morgan fingerprint (ECFP6 uses radius=3)
        fp = AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
        
        # Convert to numpy array
        arr = np.zeros((n_bits,), dtype=np.int8)
        Chem.DataStructs.ConvertToNumpyArray(fp, arr)
        
        return arr
    except Exception as e:
        print(f"Error converting SMILES to fingerprint: {e}")
        return None


def classify_molecule(smiles: str) -> ClassificationResult:
    """
    Classify a single molecule.
    
    Args:
        smiles: SMILES string
    
    Returns:
        ClassificationResult object
    """
    # Convert SMILES to fingerprint
    fp = smiles_to_ecfp6(smiles)
    
    if fp is None:
        return ClassificationResult(
            smiles=smiles,
            prediction="Invalid",
            probability_rna=0.0,
            probability_protein=0.0,
            confidence=0.0,
            valid=False,
            error="Invalid SMILES string"
        )
    
    # Reshape for prediction
    fp_reshaped = fp.reshape(1, -1)
    
    # Get prediction and probabilities
    prediction = model.predict(fp_reshaped)[0]
    probabilities = model.predict_proba(fp_reshaped)[0]
    
    # Assuming class 0 is RNA_binding and class 1 is Protein_binding
    # This should be verified with the actual model training
    prob_rna = float(probabilities[0])
    prob_protein = float(probabilities[1])
    
    prediction_label = "RNA_binding" if prediction == 0 else "Protein_binding"
    confidence = float(max(probabilities))
    
    return ClassificationResult(
        smiles=smiles,
        prediction=prediction_label,
        probability_rna=prob_rna,
        probability_protein=prob_protein,
        confidence=confidence,
        valid=True
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
    
    start_time = time.time()
    
    results = []
    for smiles in molecules.smiles_list:
        result = classify_molecule(smiles)
        results.append(result)
    
    # Calculate summary statistics
    valid_results = [r for r in results if r.valid]
    rna_count = sum(1 for r in valid_results if r.prediction == "RNA_binding")
    protein_count = sum(1 for r in valid_results if r.prediction == "Protein_binding")
    avg_confidence = sum(r.confidence for r in valid_results) / len(valid_results) if valid_results else 0
    
    summary = {
        "total": len(results),
        "valid": len(valid_results),
        "invalid": len(results) - len(valid_results),
        "rna_binding": rna_count,
        "protein_binding": protein_count,
        "average_confidence": round(avg_confidence, 4)
    }
    
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
    
    start_time = time.time()
    
    results = []
    for compound_id in pubchem_input.compound_ids:
        try:
            # Try to get compound by CID or name
            compounds = pcp.get_compounds(compound_id, 'name')
            if not compounds:
                # Try as CID
                compounds = [pcp.Compound.from_cid(compound_id)]
            
            if compounds and compounds[0]:
                smiles = compounds[0].canonical_smiles
                result = classify_molecule(smiles)
                results.append(result)
            else:
                results.append(ClassificationResult(
                    smiles="",
                    prediction="Invalid",
                    probability_rna=0.0,
                    probability_protein=0.0,
                    confidence=0.0,
                    valid=False,
                    error=f"Compound not found: {compound_id}"
                ))
        except Exception as e:
            results.append(ClassificationResult(
                smiles="",
                prediction="Invalid",
                probability_rna=0.0,
                probability_protein=0.0,
                confidence=0.0,
                valid=False,
                error=f"Error fetching {compound_id}: {str(e)}"
            ))
    
    # Calculate summary statistics
    valid_results = [r for r in results if r.valid]
    rna_count = sum(1 for r in valid_results if r.prediction == "RNA_binding")
    protein_count = sum(1 for r in valid_results if r.prediction == "Protein_binding")
    avg_confidence = sum(r.confidence for r in valid_results) / len(valid_results) if valid_results else 0
    
    summary = {
        "total": len(results),
        "valid": len(valid_results),
        "invalid": len(results) - len(valid_results),
        "rna_binding": rna_count,
        "protein_binding": protein_count,
        "average_confidence": round(avg_confidence, 4)
    }
    
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
