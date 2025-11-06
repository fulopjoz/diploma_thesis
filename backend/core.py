"""
Core classification logic for RNA/Protein binding molecule classification.

This module provides shared functionality for feature generation and classification
that can be used by both the API and CLI interfaces.
"""

from typing import List, Tuple, Dict, Any, Optional
import joblib
import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit import RDLogger
import os

# Disable RDKit warnings
RDLogger.DisableLog('rdApp.error')

# Model path - shared across API and CLI
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "ensemble", "set1", "best_xgb.joblib")

# Global model instance for lazy loading
_model = None


def get_model():
    """
    Lazy load the XGBoost model.
    
    Returns:
        The loaded model instance
    
    Raises:
        Exception if model cannot be loaded
    """
    global _model
    if _model is None:
        _model = joblib.load(MODEL_PATH)
    return _model


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


class ClassificationResult:
    """Result of a single molecule classification."""
    
    def __init__(
        self,
        smiles: str,
        prediction: str,
        probability_rna: float,
        probability_protein: float,
        confidence: float,
        valid: bool,
        error: Optional[str] = None
    ):
        self.smiles = smiles
        self.prediction = prediction
        self.probability_rna = probability_rna
        self.probability_protein = probability_protein
        self.confidence = confidence
        self.valid = valid
        self.error = error
    
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        result = {
            "smiles": self.smiles,
            "prediction": self.prediction,
            "probability_rna": self.probability_rna,
            "probability_protein": self.probability_protein,
            "confidence": self.confidence,
            "valid": self.valid
        }
        if self.error is not None:
            result["error"] = self.error
        return result


def classify_smiles_list(smiles_list: List[str]) -> Tuple[List[ClassificationResult], Dict[str, Any]]:
    """
    Classify a list of SMILES strings.
    
    Args:
        smiles_list: List of SMILES strings to classify
    
    Returns:
        Tuple of (results, summary) where:
        - results: List of ClassificationResult objects
        - summary: Dictionary with summary statistics
    """
    model = get_model()
    results = []
    
    for smiles in smiles_list:
        # Convert SMILES to fingerprint
        fp = smiles_to_ecfp6(smiles)
        
        if fp is None:
            results.append(ClassificationResult(
                smiles=smiles,
                prediction="Invalid",
                probability_rna=0.0,
                probability_protein=0.0,
                confidence=0.0,
                valid=False,
                error="Invalid SMILES string"
            ))
            continue
        
        # Reshape for prediction
        fp_reshaped = fp.reshape(1, -1)
        
        # Get prediction and probabilities
        prediction = model.predict(fp_reshaped)[0]
        probabilities = model.predict_proba(fp_reshaped)[0]
        
        # Assuming class 0 is RNA_binding and class 1 is Protein_binding
        prob_rna = float(probabilities[0])
        prob_protein = float(probabilities[1])
        
        prediction_label = "RNA_binding" if prediction == 0 else "Protein_binding"
        confidence = float(max(probabilities))
        
        results.append(ClassificationResult(
            smiles=smiles,
            prediction=prediction_label,
            probability_rna=prob_rna,
            probability_protein=prob_protein,
            confidence=confidence,
            valid=True
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
    
    return results, summary
