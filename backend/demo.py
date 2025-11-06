#!/usr/bin/env python3
"""
Complete example demonstrating all features of the RNA/Protein Binding Classifier API.

This script shows:
1. Single molecule classification
2. Batch processing
3. PubChem integration
4. Visualization of results
5. Report generation
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from example_client import RNAProteinClassifierClient, print_result
from visualize import generate_report


def main():
    """Main demonstration function."""
    print("=" * 80)
    print("RNA/Protein Binding Classifier - Complete Demo")
    print("=" * 80)
    
    # Initialize client
    client = RNAProteinClassifierClient()
    
    # Check health
    print("\n1. Health Check")
    print("-" * 80)
    try:
        health = client.health_check()
        print(f"API Status: {health['status']}")
        print(f"Model Loaded: {health['model_loaded']}")
    except Exception as e:
        print(f"Error connecting to API: {e}")
        print("\nMake sure the API server is running:")
        print("  cd backend && python app.py")
        return
    
    # Example molecules for classification
    print("\n2. Preparing Test Dataset")
    print("-" * 80)
    test_molecules = {
        "Simple aromatics": [
            "c1ccccc1",  # benzene
            "c1ccc2ccccc2c1",  # naphthalene
        ],
        "Common drugs": [
            "CC(C)Cc1ccc(cc1)C(C)C(O)=O",  # ibuprofen
            "CC(=O)Oc1ccccc1C(=O)O",  # aspirin
        ],
        "Small molecules": [
            "CCO",  # ethanol
            "CC(=O)O",  # acetic acid
            "CC(C)O",  # isopropanol
        ],
        "Heterocycles": [
            "c1ccc2c(c1)ccc3c2nccc3",  # acridine
            "c1cnc2c(c1)cccn2",  # quinoxaline
        ],
    }
    
    # Flatten the test molecules
    all_smiles = []
    for category, smiles_list in test_molecules.items():
        all_smiles.extend(smiles_list)
        print(f"  {category}: {len(smiles_list)} molecules")
    
    print(f"\nTotal test molecules: {len(all_smiles)}")
    
    # Batch classification
    print("\n3. Batch Classification")
    print("-" * 80)
    print("Classifying all test molecules...")
    
    try:
        results = client.classify_batch(all_smiles)
        
        print("\nClassification Summary:")
        print(f"  Total molecules: {results['summary']['total']}")
        print(f"  Valid predictions: {results['summary']['valid']}")
        print(f"  Invalid SMILES: {results['summary']['invalid']}")
        print(f"  RNA binding: {results['summary']['rna_binding']}")
        print(f"  Protein binding: {results['summary']['protein_binding']}")
        print(f"  Average confidence: {results['summary']['average_confidence']:.2%}")
        
        # Show detailed results
        print("\n4. Detailed Results")
        print("-" * 80)
        current_category = None
        molecule_idx = 0
        
        for category, smiles_list in test_molecules.items():
            print(f"\n{category}:")
            print("  " + "-" * 76)
            for smiles in smiles_list:
                result = results['results'][molecule_idx]
                molecule_idx += 1
                
                if result['valid']:
                    print(f"  {result['prediction']:<18} "
                          f"Confidence: {result['confidence']:>6.2%}  "
                          f"SMILES: {result['smiles']}")
                else:
                    print(f"  INVALID            "
                          f"Error: {result.get('error', 'Unknown')}  "
                          f"SMILES: {result['smiles']}")
        
        # Generate visualization report
        print("\n5. Generating Visualization Report")
        print("-" * 80)
        
        try:
            import matplotlib
            matplotlib.use('Agg')  # Non-interactive backend
            
            output_dir = "/tmp/rna_protein_classification_report"
            generate_report(results, output_dir)
            print(f"\nVisualization report saved to: {output_dir}")
            print("Files generated:")
            print("  - probability_distribution.png")
            print("  - confidence_scores.png")
            print("  - classification_summary.png")
            print("  - summary.txt")
        except ImportError:
            print("Matplotlib not installed. Skipping visualization.")
            print("Install with: pip install matplotlib")
        except Exception as e:
            print(f"Error generating visualizations: {e}")
        
    except Exception as e:
        print(f"Error during batch classification: {e}")
        return
    
    # PubChem example (optional)
    print("\n6. PubChem Integration Example")
    print("-" * 80)
    pubchem_compounds = ["2244", "aspirin", "caffeine"]
    print(f"Fetching from PubChem: {', '.join(pubchem_compounds)}")
    
    try:
        pubchem_results = client.classify_from_pubchem(pubchem_compounds)
        
        print("\nPubChem Classification Results:")
        for i, (compound_id, result) in enumerate(zip(pubchem_compounds, 
                                                       pubchem_results['results']), 1):
            print(f"\n{i}. Compound: {compound_id}")
            if result['valid']:
                print(f"   SMILES: {result['smiles']}")
                print(f"   Prediction: {result['prediction']}")
                print(f"   Confidence: {result['confidence']:.2%}")
            else:
                print(f"   Error: {result.get('error', 'Unknown error')}")
    except ImportError:
        print("PubChemPy not installed. Skipping PubChem integration.")
        print("Install with: pip install pubchempy")
    except Exception as e:
        print(f"Note: PubChem integration failed: {e}")
        print("This is optional and doesn't affect other functionality.")
    
    # Final summary
    print("\n" + "=" * 80)
    print("Demo Completed Successfully!")
    print("=" * 80)
    print("\nKey Features Demonstrated:")
    print("  ✓ Health check and API connectivity")
    print("  ✓ Batch classification of multiple molecules")
    print("  ✓ Detailed probability scores and confidence metrics")
    print("  ✓ Classification by molecular categories")
    print("  ✓ Visualization and report generation")
    print("  ✓ PubChem database integration (optional)")
    
    print("\nNext Steps:")
    print("  • View API documentation at http://localhost:8000/docs")
    print("  • Check visualization report in /tmp/rna_protein_classification_report/")
    print("  • Integrate the API into your own applications")
    print("  • Use the client library (example_client.py) in your projects")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
