"""
FastAPI backend for RNA/Protein binding molecule classification.

This application provides endpoints to classify molecules as RNA-binding or 
Protein-binding using a pre-trained XGBoost ensemble model.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import joblib
import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit import RDLogger
import os

# Disable RDKit warnings
RDLogger.DisableLog('rdApp.error')

# Initialize FastAPI app
app = FastAPI(
    title="RNA/Protein Binding Classifier",
    description="Binary classification of molecules as RNA-binding or Protein-binding",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load the pre-trained model
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "ensemble", "set1", "best_xgb.joblib")
model = None

@app.on_event("startup")
async def load_model():
    """Load the XGBoost model on startup."""
    global model
    try:
        model = joblib.load(MODEL_PATH)
        print(f"Model loaded successfully from {MODEL_PATH}")
    except Exception as e:
        print(f"Error loading model: {e}")
        raise


# Pydantic models for request/response
class MoleculeInput(BaseModel):
    smiles: str = Field(..., description="SMILES string of the molecule")
    
    class Config:
        schema_extra = {
            "example": {
                "smiles": "CC(C)Cc1ccc(cc1)C(C)C(O)=O"
            }
        }


class MoleculesBatchInput(BaseModel):
    smiles_list: List[str] = Field(..., description="List of SMILES strings")
    
    class Config:
        schema_extra = {
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
        schema_extra = {
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
    
    return BatchClassificationResult(results=results, summary=summary)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
