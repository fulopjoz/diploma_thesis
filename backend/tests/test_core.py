"""
Unit tests for backend/core.py

Tests the core classification logic including feature generation and classification.
"""

import sys
import os
import pytest
import numpy as np

# Add parent directory to path to import core module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import smiles_to_ecfp6, classify_smiles_list, get_model, ClassificationResult


class TestSmilesToEcfp6:
    """Tests for smiles_to_ecfp6 function."""
    
    def test_valid_smiles_returns_expected_shape(self):
        """Test that valid SMILES returns fingerprint with correct shape."""
        smiles = "c1ccccc1"  # benzene
        fp = smiles_to_ecfp6(smiles)
        
        assert fp is not None, "Fingerprint should not be None for valid SMILES"
        assert isinstance(fp, np.ndarray), "Fingerprint should be numpy array"
        assert fp.shape == (2048,), f"Expected shape (2048,), got {fp.shape}"
        assert fp.dtype == np.int8, f"Expected dtype int8, got {fp.dtype}"
    
    def test_valid_smiles_has_nonzero_bits(self):
        """Test that valid SMILES generates fingerprint with non-zero bits."""
        smiles = "c1ccccc1"  # benzene
        fp = smiles_to_ecfp6(smiles)
        
        assert fp is not None
        assert fp.sum() > 0, "Fingerprint should have at least some non-zero bits"
    
    def test_invalid_smiles_returns_none(self):
        """Test that invalid SMILES returns None."""
        invalid_smiles = "INVALID_SMILES_STRING"
        fp = smiles_to_ecfp6(invalid_smiles)
        
        assert fp is None, "Invalid SMILES should return None"
    
    def test_empty_smiles_returns_zero_fingerprint(self):
        """Test that empty SMILES returns a zero fingerprint."""
        fp = smiles_to_ecfp6("")
        
        assert fp is not None, "Empty SMILES returns a valid fingerprint (empty molecule)"
        assert fp.sum() == 0, "Empty SMILES should have all zero bits"
    
    def test_custom_radius_and_bits(self):
        """Test that custom radius and n_bits parameters work."""
        smiles = "CCO"  # ethanol
        fp = smiles_to_ecfp6(smiles, radius=2, n_bits=1024)
        
        assert fp is not None
        assert fp.shape == (1024,), f"Expected shape (1024,) with custom n_bits"
    
    def test_different_molecules_different_fingerprints(self):
        """Test that different molecules generate different fingerprints."""
        smiles1 = "c1ccccc1"  # benzene
        smiles2 = "CCO"  # ethanol
        
        fp1 = smiles_to_ecfp6(smiles1)
        fp2 = smiles_to_ecfp6(smiles2)
        
        assert fp1 is not None
        assert fp2 is not None
        assert not np.array_equal(fp1, fp2), "Different molecules should have different fingerprints"


class TestClassifySmilesList:
    """Tests for classify_smiles_list function."""
    
    @pytest.fixture(autouse=True)
    def load_model(self):
        """Ensure model is loaded before each test."""
        get_model()
    
    def test_single_valid_smiles(self):
        """Test classification of a single valid SMILES."""
        smiles_list = ["c1ccccc1"]  # benzene
        results, summary = classify_smiles_list(smiles_list)
        
        assert len(results) == 1, "Should return one result"
        assert isinstance(results[0], ClassificationResult)
        assert results[0].valid is True
        assert results[0].smiles == "c1ccccc1"
        assert results[0].prediction in ["RNA_binding", "Protein_binding"]
        assert 0.0 <= results[0].probability_rna <= 1.0
        assert 0.0 <= results[0].probability_protein <= 1.0
        assert abs(results[0].probability_rna + results[0].probability_protein - 1.0) < 0.001
        assert results[0].confidence == max(results[0].probability_rna, results[0].probability_protein)
        assert results[0].error is None
    
    def test_invalid_smiles(self):
        """Test classification of invalid SMILES."""
        smiles_list = ["INVALID_SMILES"]
        results, summary = classify_smiles_list(smiles_list)
        
        assert len(results) == 1
        assert results[0].valid is False
        assert results[0].prediction == "Invalid"
        assert results[0].error == "Invalid SMILES string"
        assert results[0].probability_rna == 0.0
        assert results[0].probability_protein == 0.0
        assert results[0].confidence == 0.0
    
    def test_mixed_valid_invalid_smiles(self):
        """Test classification of mixed valid and invalid SMILES."""
        smiles_list = [
            "c1ccccc1",  # valid: benzene
            "INVALID",   # invalid
            "CCO"        # valid: ethanol
        ]
        results, summary = classify_smiles_list(smiles_list)
        
        assert len(results) == 3
        assert results[0].valid is True
        assert results[1].valid is False
        assert results[2].valid is True
    
    def test_summary_statistics_all_valid(self):
        """Test summary statistics with all valid SMILES."""
        smiles_list = ["c1ccccc1", "CCO", "CC(=O)O"]
        results, summary = classify_smiles_list(smiles_list)
        
        assert summary["total"] == 3
        assert summary["valid"] == 3
        assert summary["invalid"] == 0
        assert summary["rna_binding"] + summary["protein_binding"] == 3
        assert 0.0 <= summary["average_confidence"] <= 1.0
    
    def test_summary_statistics_mixed(self):
        """Test summary statistics with mixed valid/invalid SMILES."""
        smiles_list = ["c1ccccc1", "INVALID", "CCO"]
        results, summary = classify_smiles_list(smiles_list)
        
        assert summary["total"] == 3
        assert summary["valid"] == 2
        assert summary["invalid"] == 1
        assert summary["rna_binding"] + summary["protein_binding"] == 2
    
    def test_summary_statistics_all_invalid(self):
        """Test summary statistics with all invalid SMILES."""
        smiles_list = ["INVALID1", "INVALID2"]
        results, summary = classify_smiles_list(smiles_list)
        
        assert summary["total"] == 2
        assert summary["valid"] == 0
        assert summary["invalid"] == 2
        assert summary["rna_binding"] == 0
        assert summary["protein_binding"] == 0
        assert summary["average_confidence"] == 0
    
    def test_empty_list(self):
        """Test classification of empty list."""
        smiles_list = []
        results, summary = classify_smiles_list(smiles_list)
        
        assert len(results) == 0
        assert summary["total"] == 0
        assert summary["valid"] == 0
        assert summary["invalid"] == 0
    
    def test_matches_test_classifier_output(self):
        """
        Test that classify_smiles_list matches outputs from original classify_molecule.
        Uses same test molecules as backend/test_classifier.py
        """
        test_molecules = [
            "c1ccccc1",  # Benzene
            "CC(C)Cc1ccc(cc1)C(C)C(O)=O",  # Ibuprofen
            "CCO",  # Ethanol
            "CC(=O)O",  # Acetic acid
            "c1ccc2c(c1)ccc3c2nccc3",  # Acridine
        ]
        
        results, summary = classify_smiles_list(test_molecules)
        
        # Verify all are valid
        assert all(r.valid for r in results), "All test molecules should be valid"
        
        # Verify specific expected results from test_classifier.py output
        # Benzene should be Protein_binding with high confidence
        benzene_result = results[0]
        assert benzene_result.prediction == "Protein_binding"
        assert benzene_result.confidence > 0.99
        
        # Ibuprofen should be RNA_binding
        ibuprofen_result = results[1]
        assert ibuprofen_result.prediction == "RNA_binding"
        assert ibuprofen_result.probability_rna > 0.8
        
        # Summary should have correct counts
        assert summary["total"] == 5
        assert summary["valid"] == 5
        assert summary["invalid"] == 0
        assert summary["rna_binding"] + summary["protein_binding"] == 5
    
    def test_result_to_dict(self):
        """Test ClassificationResult.to_dict() method."""
        result = ClassificationResult(
            smiles="c1ccccc1",
            prediction="Protein_binding",
            probability_rna=0.1,
            probability_protein=0.9,
            confidence=0.9,
            valid=True,
            error=None
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["smiles"] == "c1ccccc1"
        assert result_dict["prediction"] == "Protein_binding"
        assert result_dict["probability_rna"] == 0.1
        assert result_dict["probability_protein"] == 0.9
        assert result_dict["confidence"] == 0.9
        assert result_dict["valid"] is True
        assert "error" not in result_dict  # Should not include None error
    
    def test_result_to_dict_with_error(self):
        """Test ClassificationResult.to_dict() with error."""
        result = ClassificationResult(
            smiles="INVALID",
            prediction="Invalid",
            probability_rna=0.0,
            probability_protein=0.0,
            confidence=0.0,
            valid=False,
            error="Invalid SMILES string"
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["valid"] is False
        assert result_dict["error"] == "Invalid SMILES string"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
