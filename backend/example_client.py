#!/usr/bin/env python3
"""
Example client script for the RNA/Protein Binding Classifier API.

This script demonstrates how to interact with the API from Python.
"""

import requests
import json
from typing import List, Dict


class RNAProteinClassifierClient:
    """Client for the RNA/Protein Binding Classifier API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize the client.
        
        Args:
            base_url: Base URL of the API server
        """
        self.base_url = base_url.rstrip('/')
    
    def health_check(self) -> Dict:
        """Check if the API is healthy."""
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def classify_molecule(self, smiles: str) -> Dict:
        """
        Classify a single molecule.
        
        Args:
            smiles: SMILES string of the molecule
            
        Returns:
            Classification result dictionary
        """
        response = requests.post(
            f"{self.base_url}/api/classify",
            json={"smiles": smiles}
        )
        response.raise_for_status()
        return response.json()
    
    def classify_batch(self, smiles_list: List[str]) -> Dict:
        """
        Classify multiple molecules.
        
        Args:
            smiles_list: List of SMILES strings
            
        Returns:
            Batch classification results with summary
        """
        response = requests.post(
            f"{self.base_url}/api/classify/batch",
            json={"smiles_list": smiles_list}
        )
        response.raise_for_status()
        return response.json()
    
    def classify_from_pubchem(self, compound_ids: List[str]) -> Dict:
        """
        Fetch molecules from PubChem and classify them.
        
        Args:
            compound_ids: List of PubChem CIDs or compound names
            
        Returns:
            Batch classification results with summary
        """
        response = requests.post(
            f"{self.base_url}/api/classify/pubchem",
            json={"compound_ids": compound_ids}
        )
        response.raise_for_status()
        return response.json()


def print_result(result: Dict):
    """Pretty print a classification result."""
    if result['valid']:
        print(f"  SMILES: {result['smiles']}")
        print(f"  Prediction: {result['prediction']}")
        print(f"  Confidence: {result['confidence']:.2%}")
        print(f"  P(RNA binding): {result['probability_rna']:.4f}")
        print(f"  P(Protein binding): {result['probability_protein']:.4f}")
    else:
        print(f"  SMILES: {result['smiles']}")
        print(f"  Error: {result.get('error', 'Unknown error')}")


def main():
    """Main example function."""
    print("=" * 70)
    print("RNA/Protein Binding Classifier - API Client Example")
    print("=" * 70)
    
    # Initialize client
    client = RNAProteinClassifierClient()
    
    # Check health
    print("\n1. Checking API health...")
    try:
        health = client.health_check()
        print(f"   Status: {health['status']}")
        print(f"   Model loaded: {health['model_loaded']}")
    except Exception as e:
        print(f"   Error: {e}")
        print("\n   Make sure the API server is running!")
        print("   Start it with: cd backend && python app.py")
        return
    
    # Single molecule classification
    print("\n2. Single Molecule Classification")
    print("-" * 70)
    smiles = "c1ccccc1"  # benzene
    print(f"Classifying: {smiles} (benzene)")
    try:
        result = client.classify_molecule(smiles)
        print_result(result)
    except Exception as e:
        print(f"   Error: {e}")
    
    # Batch classification
    print("\n3. Batch Classification")
    print("-" * 70)
    smiles_list = [
        "c1ccccc1",  # benzene
        "CCO",  # ethanol
        "CC(=O)O",  # acetic acid
        "CC(C)Cc1ccc(cc1)C(C)C(O)=O",  # ibuprofen
    ]
    print(f"Classifying {len(smiles_list)} molecules...")
    try:
        results = client.classify_batch(smiles_list)
        print(f"\nSummary:")
        print(f"  Total: {results['summary']['total']}")
        print(f"  Valid: {results['summary']['valid']}")
        print(f"  RNA binding: {results['summary']['rna_binding']}")
        print(f"  Protein binding: {results['summary']['protein_binding']}")
        print(f"  Average confidence: {results['summary']['average_confidence']:.2%}")
        
        print("\nIndividual results:")
        for i, result in enumerate(results['results'], 1):
            print(f"\n{i}.")
            print_result(result)
    except Exception as e:
        print(f"   Error: {e}")
    
    # PubChem classification
    print("\n4. PubChem Integration")
    print("-" * 70)
    compound_ids = ["2244", "aspirin"]
    print(f"Fetching and classifying from PubChem: {compound_ids}")
    try:
        results = client.classify_from_pubchem(compound_ids)
        print(f"\nSummary:")
        print(f"  Total: {results['summary']['total']}")
        print(f"  Valid: {results['summary']['valid']}")
        print(f"  RNA binding: {results['summary']['rna_binding']}")
        print(f"  Protein binding: {results['summary']['protein_binding']}")
        
        print("\nResults:")
        for i, result in enumerate(results['results'], 1):
            print(f"\n{i}. Compound ID: {compound_ids[i-1]}")
            print_result(result)
    except Exception as e:
        print(f"   Error: {e}")
        print("   Note: PubChem integration requires 'pubchempy' package")
    
    print("\n" + "=" * 70)
    print("Example completed!")
    print("=" * 70)
    print("\nFor more examples and API documentation, visit:")
    print("  http://localhost:8000/docs")
    print("=" * 70)


if __name__ == "__main__":
    main()
