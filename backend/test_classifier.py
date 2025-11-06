"""
Test script for the RNA/Protein Binding Classifier API.

This script tests the basic functionality of the classifier without starting the full server.
"""

import sys
import os

# Add parent directory to path to import app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import smiles_to_ecfp6, classify_molecule, model, load_model
import asyncio


async def test_classifier():
    """Test the classifier with sample molecules."""
    
    print("=" * 60)
    print("RNA/Protein Binding Classifier - Test Script")
    print("=" * 60)
    
    # Load model
    print("\n1. Loading model...")
    try:
        await load_model()
        print("   ✓ Model loaded successfully")
    except Exception as e:
        print(f"   ✗ Error loading model: {e}")
        return
    
    # Test SMILES to fingerprint conversion
    print("\n2. Testing SMILES to ECFP6 conversion...")
    test_smiles = "c1ccccc1"  # benzene
    fp = smiles_to_ecfp6(test_smiles)
    if fp is not None:
        print(f"   ✓ Successfully converted '{test_smiles}' to fingerprint")
        print(f"   - Fingerprint shape: {fp.shape}")
        print(f"   - Non-zero bits: {fp.sum()}")
    else:
        print(f"   ✗ Failed to convert SMILES")
    
    # Test classification with sample molecules
    print("\n3. Testing classification...")
    test_molecules = [
        ("c1ccccc1", "Benzene"),
        ("CC(C)Cc1ccc(cc1)C(C)C(O)=O", "Ibuprofen"),
        ("CCO", "Ethanol"),
        ("CC(=O)O", "Acetic acid"),
        ("c1ccc2c(c1)ccc3c2nccc3", "Acridine"),
    ]
    
    print("\n   Classification Results:")
    print("   " + "-" * 56)
    print(f"   {'Molecule':<20} {'Prediction':<15} {'Confidence':>10}")
    print("   " + "-" * 56)
    
    for smiles, name in test_molecules:
        result = classify_molecule(smiles)
        if result.valid:
            print(f"   {name:<20} {result.prediction:<15} {result.confidence:>9.2%}")
            print(f"   {'  SMILES: ' + smiles}")
            print(f"   {'  P(RNA): '}{result.probability_rna:.4f}  {'P(Protein): '}{result.probability_protein:.4f}")
            print()
        else:
            print(f"   {name:<20} {'INVALID':<15} {'N/A':>10}")
            print(f"   {'  Error: ' + (result.error or 'Unknown')}")
            print()
    
    print("   " + "-" * 56)
    
    # Test with invalid SMILES
    print("\n4. Testing error handling...")
    invalid_smiles = "INVALID_SMILES_STRING"
    result = classify_molecule(invalid_smiles)
    if not result.valid:
        print(f"   ✓ Correctly handled invalid SMILES: {result.error}")
    else:
        print(f"   ✗ Failed to detect invalid SMILES")
    
    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)
    print("\nTo start the API server, run:")
    print("  python app.py")
    print("  or")
    print("  uvicorn app:app --reload")
    print("\nAPI documentation will be available at:")
    print("  http://localhost:8000/docs")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_classifier())
