"""
<<<<<<< HEAD
Core classification logic for RNA/Protein binding molecule classification.

This module provides centralized feature generation and classification functions
that are shared across the API and CLI interfaces.
"""

from typing import List, Optional, Dict, Any
=======
Core classification logic for RNA/Protein binding classifier.

This module provides the shared core functionality used by both the API
and CLI interfaces, including model loading, feature generation, and
classification logic.
"""

import joblib
>>>>>>> origin/copilot/add-file-upload-api
import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit import RDLogger
<<<<<<< HEAD
import joblib
import os
=======
from typing import Optional, List, Dict, Any
import os
import sys
>>>>>>> origin/copilot/add-file-upload-api

# Disable RDKit warnings
RDLogger.DisableLog('rdApp.error')

<<<<<<< HEAD
# Global model variable (lazy loaded)
_model = None
_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "ensemble", "set1", "best_xgb.joblib")


def load_model(model_path: Optional[str] = None):
    """
    Load the XGBoost model (lazy loading).
    
    Args:
        model_path: Optional path to model file. Uses default if not provided.
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
>>>>>>> origin/copilot/add-file-upload-api
    
    Returns:
        Loaded model object
    
    Raises:
<<<<<<< HEAD
        Exception if model cannot be loaded
    """
    global _model
    
    if _model is not None:
        return _model
    
    path = model_path or _MODEL_PATH
    try:
        _model = joblib.load(path)
        print(f"Model loaded successfully from {path}")
        return _model
    except Exception as e:
        print(f"Error loading model: {e}")
        raise


def smiles_to_ecfp6(smiles: str, radius: int = 3, n_bits: int = 2048) -> Optional[np.ndarray]:
=======
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
def classify_smiles_list(
    smiles_list: List[str],
    model=None
) -> Dict[str, Any]:
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
        model: Pre-loaded model (if None, will load default model)
    
    Returns:
        Dictionary with 'results' and 'summary' keys containing classification data
    """
    # Load model if not provided
=======
        model: Pre-loaded model (if None, will load from default path)
    
    Returns:
        Dictionary with:
        - results: List of classification results
        - summary: Summary statistics
    """
>>>>>>> origin/copilot/add-file-upload-api
    if model is None:
        model = load_model()
    
    results = []
<<<<<<< HEAD
    
    for smiles in smiles_list:
        # Convert SMILES to fingerprint
        fp = smiles_to_ecfp6(smiles)
        
        if fp is None:
            results.append({
                'smiles': smiles,
                'prediction': 'Invalid',
                'probability_rna': 0.0,
                'probability_protein': 0.0,
                'confidence': 0.0,
                'valid': False,
                'error': 'Invalid SMILES string'
            })
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
        
        results.append({
            'smiles': smiles,
            'prediction': prediction_label,
            'probability_rna': prob_rna,
            'probability_protein': prob_protein,
            'confidence': confidence,
            'valid': True,
            'error': None
        })
=======
    for smiles in smiles_list:
        result = classify_smiles(smiles, model)
        results.append(result)
>>>>>>> origin/copilot/add-file-upload-api
    
    # Calculate summary statistics
    valid_results = [r for r in results if r['valid']]
    rna_count = sum(1 for r in valid_results if r['prediction'] == "RNA_binding")
    protein_count = sum(1 for r in valid_results if r['prediction'] == "Protein_binding")
    avg_confidence = sum(r['confidence'] for r in valid_results) / len(valid_results) if valid_results else 0
    
    summary = {
        "total": len(results),
        "valid": len(valid_results),
        "invalid": len(results) - len(valid_results),
        "rna_binding": rna_count,
        "protein_binding": protein_count,
        "average_confidence": round(avg_confidence, 4)
    }
    
    return {
<<<<<<< HEAD
        'results': results,
        'summary': summary
=======
        "results": results,
        "summary": summary
>>>>>>> origin/copilot/add-file-upload-api
    }
