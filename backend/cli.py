"""
Command-line interface for RNA/Protein binding classification.

This module provides a CLI built with Typer that shares core logic with the API.
Supports multiple input formats and output options (JSON/CSV).
"""

import typer
from typing import List, Optional
from pathlib import Path
import json
import csv
import sys
from enum import Enum

from backend.core import load_model, classify_smiles_list
from backend.visualize import generate_report

# Create Typer app
app = typer.Typer(
    name="classifier",
    help="RNA/Protein Binding Classifier CLI",
    add_completion=False
)

# Subcommand for classify operations
classify_app = typer.Typer(help="Classification commands")
app.add_typer(classify_app, name="classify")


class OutputFormat(str, Enum):
    """Output format options."""
    json = "json"
    csv = "csv"


class FileFormat(str, Enum):
    """Input file format options."""
    csv = "csv"
    tsv = "tsv"
    sdf = "sdf"


def output_json(results_data: dict, output_file: Optional[Path] = None):
    """
    Output results in JSON format.
    
    Args:
        results_data: Dictionary with results and summary
        output_file: Optional file path to write output
    """
    json_str = json.dumps(results_data, indent=2)
    
    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json_str)
        typer.echo(f"Results saved to {output_file}", err=True)
    else:
        typer.echo(json_str)


def output_csv(results_data: dict, output_file: Optional[Path] = None):
    """
    Output results in CSV format.
    
    Args:
        results_data: Dictionary with results and summary
        output_file: Optional file path to write output
    """
    results = results_data.get('results', [])
    
    # Define CSV headers
    fieldnames = ['smiles', 'prediction', 'probability_rna', 'probability_protein', 
                  'confidence', 'valid', 'error']
    
    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for result in results:
                writer.writerow(result)
        typer.echo(f"Results saved to {output_file}", err=True)
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(result)


@classify_app.command("smiles")
def classify_smiles_cmd(
    smiles_strings: List[str] = typer.Argument(..., help="SMILES strings to classify"),
    output_format: OutputFormat = typer.Option(OutputFormat.json, "--output-format", "-f", help="Output format"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    report: Optional[Path] = typer.Option(None, "--report", "-r", help="Generate visualization report in directory"),
):
    """
    Classify molecules from SMILES strings.
    
    Example:
        python -m backend.cli classify smiles "c1ccccc1" "CCO"
    """
    try:
        # Load model
        model = load_model()
        
        # Classify SMILES
        results_data = classify_smiles_list(smiles_strings, model)
        
        # Output results
        if output_format == OutputFormat.json:
            output_json(results_data, output)
        else:
            output_csv(results_data, output)
        
        # Generate report if requested
        if report:
            generate_report(results_data, str(report))
            typer.echo(f"Report generated in {report}", err=True)
        
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)


@classify_app.command("file")
def classify_file_cmd(
    path: Path = typer.Option(..., "--path", "-p", help="Input file path"),
    format: FileFormat = typer.Option(FileFormat.csv, "--format", help="Input file format"),
    smiles_col: str = typer.Option("smiles", "--smiles-col", help="Column name containing SMILES"),
    delimiter: Optional[str] = typer.Option(None, "--delimiter", help="CSV/TSV delimiter (auto-detect if not specified)"),
    chunksize: Optional[int] = typer.Option(None, "--chunksize", help="Process file in chunks of this size"),
    output_format: OutputFormat = typer.Option(OutputFormat.json, "--output-format", "-f", help="Output format"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    report: Optional[Path] = typer.Option(None, "--report", "-r", help="Generate visualization report in directory"),
):
    """
    Classify molecules from a CSV, TSV, or SDF file.
    
    Example:
        python -m backend.cli classify file --path molecules.csv --format csv
    """
    try:
        # Load model
        model = load_model()
        
        # Read SMILES from file
        smiles_list = []
        
        if format == FileFormat.sdf:
            # Parse SDF file
            from rdkit import Chem
            suppl = Chem.SDMolSupplier(str(path))
            for mol in suppl:
                if mol is not None:
                    smiles = Chem.MolToSmiles(mol)
                    smiles_list.append(smiles)
        else:
            # Parse CSV/TSV file
            import pandas as pd
            
            # Determine delimiter
            if delimiter is None:
                delimiter = '\t' if format == FileFormat.tsv else ','
            
            # Read file
            if chunksize:
                # Process in chunks
                all_results = []
                for chunk in pd.read_csv(path, delimiter=delimiter, chunksize=chunksize):
                    if smiles_col not in chunk.columns:
                        raise ValueError(f"Column '{smiles_col}' not found in file")
                    
                    chunk_smiles = chunk[smiles_col].dropna().tolist()
                    chunk_results = classify_smiles_list(chunk_smiles, model)
                    all_results.extend(chunk_results['results'])
                
                # Recalculate summary
                valid_results = [r for r in all_results if r['valid']]
                rna_count = sum(1 for r in valid_results if r['prediction'] == "RNA_binding")
                protein_count = sum(1 for r in valid_results if r['prediction'] == "Protein_binding")
                avg_confidence = sum(r['confidence'] for r in valid_results) / len(valid_results) if valid_results else 0
                
                results_data = {
                    "results": all_results,
                    "summary": {
                        "total": len(all_results),
                        "valid": len(valid_results),
                        "invalid": len(all_results) - len(valid_results),
                        "rna_binding": rna_count,
                        "protein_binding": protein_count,
                        "average_confidence": round(avg_confidence, 4)
                    }
                }
            else:
                # Read entire file
                df = pd.read_csv(path, delimiter=delimiter)
                if smiles_col not in df.columns:
                    raise ValueError(f"Column '{smiles_col}' not found in file")
                
                smiles_list = df[smiles_col].dropna().tolist()
                results_data = classify_smiles_list(smiles_list, model)
        
        # For SDF files, classify collected SMILES
        if format == FileFormat.sdf:
            results_data = classify_smiles_list(smiles_list, model)
        
        # Output results
        if output_format == OutputFormat.json:
            output_json(results_data, output)
        else:
            output_csv(results_data, output)
        
        # Generate report if requested
        if report:
            generate_report(results_data, str(report))
            typer.echo(f"Report generated in {report}", err=True)
        
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)


@classify_app.command("pubchem")
def classify_pubchem_cmd(
    id: List[str] = typer.Option(..., "--id", help="PubChem CID or compound name (repeatable)"),
    output_format: OutputFormat = typer.Option(OutputFormat.json, "--output-format", "-f", help="Output format"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    report: Optional[Path] = typer.Option(None, "--report", "-r", help="Generate visualization report in directory"),
):
    """
    Classify molecules from PubChem by CID or compound name.
    
    Example:
        python -m backend.cli classify pubchem --id 2244 --id aspirin
    """
    try:
        # Import PubChemPy
        try:
            import pubchempy as pcp
        except ImportError:
            typer.echo("Error: PubChemPy not installed. Install with: pip install pubchempy", err=True)
            raise typer.Exit(code=1)
        
        # Load model
        model = load_model()
        
        # Fetch SMILES from PubChem
        smiles_list = []
        errors = []
        
        for compound_id in id:
            try:
                # Try to get compound by name
                compounds = pcp.get_compounds(compound_id, 'name')
                if not compounds:
                    # Try as CID
                    try:
                        compounds = [pcp.Compound.from_cid(compound_id)]
                    except:
                        errors.append(f"Compound not found: {compound_id}")
                        continue
                
                if compounds and compounds[0]:
                    smiles = compounds[0].canonical_smiles
                    smiles_list.append(smiles)
                else:
                    errors.append(f"Compound not found: {compound_id}")
            except Exception as e:
                errors.append(f"Error fetching {compound_id}: {str(e)}")
        
        # Show errors if any
        if errors:
            typer.echo("Errors encountered:", err=True)
            for error in errors:
                typer.echo(f"  - {error}", err=True)
        
        if not smiles_list:
            typer.echo("Error: No valid compounds found", err=True)
            raise typer.Exit(code=1)
        
        # Classify SMILES
        results_data = classify_smiles_list(smiles_list, model)
        
        # Output results
        if output_format == OutputFormat.json:
            output_json(results_data, output)
        else:
            output_csv(results_data, output)
        
        # Generate report if requested
        if report:
            generate_report(results_data, str(report))
            typer.echo(f"Report generated in {report}", err=True)
        
    except Exception as e:
        if not isinstance(e, typer.Exit):
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(code=1)
        raise


@app.command()
def version():
    """Show version information."""
    typer.echo("RNA/Protein Binding Classifier CLI v1.0.0")


if __name__ == "__main__":
    app()
