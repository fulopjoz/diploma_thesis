"""
FastAPI backend for RNA/Protein binding molecule classification.

This application provides endpoints to classify molecules as RNA-binding or 
Protein-binding using a pre-trained XGBoost ensemble model.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from contextlib import asynccontextmanager
import os

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
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "smiles": "CC(C)Cc1ccc(cc1)C(C)C(O)=O"
        }
    })
    
    smiles: str = Field(..., description="SMILES string of the molecule")


class MoleculesBatchInput(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "smiles_list": [
                "CC(C)Cc1ccc(cc1)C(C)C(O)=O",
                "c1ccccc1"
            ]
        }
    })
    
    smiles_list: List[str] = Field(..., description="List of SMILES strings")


class PubChemInput(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "compound_ids": ["2244", "aspirin"]
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
            "health": "/health",
            "docs": "/docs"
        }
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
async def classify_batch(molecules: MoleculesBatchInput):
    """
    Classify multiple molecules from SMILES strings.
    
    Args:
        molecules: MoleculesBatchInput with list of SMILES strings
    
    Returns:
        BatchClassificationResult with all predictions and summary statistics
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    # Use core classify_smiles_list function
    core_results, summary = classify_smiles_list(molecules.smiles_list)
    
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
    
    return BatchClassificationResult(results=results, summary=summary)


@app.post("/api/classify/pubchem", response_model=BatchClassificationResult)
async def classify_from_pubchem(pubchem_input: PubChemInput):
    """
    Fetch molecules from PubChem and classify them.
    
    Args:
        pubchem_input: PubChemInput with list of compound IDs or names
    
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
    
    smiles_list = []
    errors = {}
    
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
    
    return BatchClassificationResult(results=results, summary=summary)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
