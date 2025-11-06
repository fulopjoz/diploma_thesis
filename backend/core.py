"""
<<<<<<< HEAD
Core classification logic for RNA/Protein binding molecule classification.

This module provides shared functionality for feature generation and classification
that can be used by both the API and CLI interfaces.

Model Class Mapping:
    - Class 0: RNA_binding
    - Class 1: Protein_binding
    
Note: This mapping is determined by the training data and should remain consistent
with the model training process. The model was trained with RNA-binding as class 0
and Protein-binding as class 1.
"""

from typing import List, Tuple, Dict, Any, Optional
=======
Core classification logic for RNA/Protein binding classifier.

This module provides the shared core functionality used by both the API
and CLI interfaces, including model loading, feature generation, and
classification logic.
"""

>>>>>>> origin/copilot/add-file-upload-api
import joblib
import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit import RDLogger
<<<<<<< HEAD
import os
=======
from typing import Optional, List, Dict, Any
import os
import sys
>>>>>>> origin/copilot/add-file-upload-api

# Disable RDKit warnings
RDLogger.DisableLog('rdApp.error')

<<<<<<< HEAD
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
=======
# Model configuration constants
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "ensemble", "set1", "best_xgb.joblib")
ECFP_RADIUS = 3  # radius=3 for ECFP6
ECFP_NBITS = 2048

# Global model instance (lazy loaded)
_model = None


def load_model(model_path: str = MODEL_PATH) -> Any:
    """
    Load the XGBoost model from disk.
    
    Args:
        model_path: Path to the model file
    
    Returns:
        Loaded model object
    
    Raises:
        FileNotFoundError: If model file does not exist
        Exception: If model loading fails
    """
    global _model
    
    if _model is None:
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        try:
            _model = joblib.load(model_path)
            print(f"Model loaded successfully from {model_path}", file=sys.stderr)
        except Exception as e:
            raise Exception(f"Error loading model: {e}")
    
    return _model


def smiles_to_ecfp6(smiles: str, radius: int = ECFP_RADIUS, n_bits: int = ECFP_NBITS) -> Optional[np.ndarray]:
>>>>>>> origin/copilot/add-file-upload-api
    """
    Convert SMILES string to ECFP6 fingerprint.
    
    Args:
        smiles: SMILES string
        radius: Morgan fingerprint radius (3 for ECFP6)
        n_bits: Number of bits in the fingerprint
    
    Returns:
        Numpy array of fingerprint or None if invalid
<<<<<<< HEAD
        
    Note:
        Uses print() for error logging to maintain consistency with the existing
        codebase and RDKit's logging approach. Errors are also indicated by
        returning None, allowing callers to handle invalid SMILES gracefully.
=======
>>>>>>> origin/copilot/add-file-upload-api
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


<<<<<<< HEAD
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
=======
def classify_smiles(smiles: str, model: Any = None) -> Dict[str, Any]:
    """
    Classify a single SMILES string.
    
    Args:
        smiles: SMILES string to classify
        model: Pre-loaded model (if None, will load from default path)
    
    Returns:
        Dictionary with classification results containing:
        - smiles: Input SMILES string
        - prediction: "RNA_binding" or "Protein_binding"
        - probability_rna: Probability of RNA binding
        - probability_protein: Probability of Protein binding
        - confidence: Maximum probability
        - valid: Whether SMILES is valid
        - error: Error message if invalid
    """
    if model is None:
        model = load_model()
    
    # Convert SMILES to fingerprint
    fp = smiles_to_ecfp6(smiles)
    
    if fp is None:
        return {
            "smiles": smiles,
            "prediction": "Invalid",
            "probability_rna": 0.0,
            "probability_protein": 0.0,
            "confidence": 0.0,
            "valid": False,
            "error": "Invalid SMILES string"
        }
    
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
    
    return {
        "smiles": smiles,
        "prediction": prediction_label,
        "probability_rna": prob_rna,
        "probability_protein": prob_protein,
        "confidence": confidence,
        "valid": True,
        "error": None
    }


def classify_smiles_list(smiles_list: List[str], model: Any = None) -> Dict[str, Any]:
>>>>>>> origin/copilot/add-file-upload-api
    """
    Classify a list of SMILES strings.
    
    Args:
        smiles_list: List of SMILES strings to classify
<<<<<<< HEAD
    
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
=======
        model: Pre-loaded model (if None, will load from default path)
    
    Returns:
        Dictionary with:
        - results: List of classification results
        - summary: Summary statistics
    """
    if model is None:
        model = load_model()
    
    results = []
    for smiles in smiles_list:
        result = classify_smiles(smiles, model)
        results.append(result)
    
    # Calculate summary statistics
    valid_results = [r for r in results if r['valid']]
    rna_count = sum(1 for r in valid_results if r['prediction'] == "RNA_binding")
    protein_count = sum(1 for r in valid_results if r['prediction'] == "Protein_binding")
    avg_confidence = sum(r['confidence'] for r in valid_results) / len(valid_results) if valid_results else 0
>>>>>>> origin/copilot/add-file-upload-api
    
    summary = {
        "total": len(results),
        "valid": len(valid_results),
        "invalid": len(results) - len(valid_results),
        "rna_binding": rna_count,
        "protein_binding": protein_count,
        "average_confidence": round(avg_confidence, 4)
    }
    
<<<<<<< HEAD
    return results, summary
=======
    return {
        "results": results,
        "summary": summary
    }
>>>>>>> origin/copilot/add-file-upload-api
