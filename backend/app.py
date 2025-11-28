"""
FastAPI backend for RNA/Protein binding molecule classification.

This application provides endpoints to classify molecules as RNA-binding or 
Protein-binding using a pre-trained XGBoost ensemble model.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from contextlib import asynccontextmanager
import io
import csv
import pandas as pd
from rdkit import Chem
import os
import core

# Load model on startup using lifespan for FastAPI 0.109+
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the XGBoost model on startup and cleanup on shutdown."""
    try:
        core.load_model()
        print("Model loaded successfully via core module")
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
    smiles: str = Field(..., description="SMILES string of the molecule")
    
    class Config:
        json_schema_extra = {
            "example": {
                "smiles": "CC(C)Cc1ccc(cc1)C(C)C(O)=O"
            }
        }


class MoleculesBatchInput(BaseModel):
    smiles_list: List[str] = Field(..., description="List of SMILES strings")
    
    class Config:
        json_schema_extra = {
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
        json_schema_extra = {
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
def classify_molecule(smiles: str) -> ClassificationResult:
    """
    Classify a single molecule.
    
    Args:
        smiles: SMILES string
    
    Returns:
        ClassificationResult object
    """
    # Use core module for classification
    result_dict = core.classify_smiles_list([smiles])['results'][0]
    
    return ClassificationResult(**result_dict)


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
            "classify_file": "/api/classify/file",
            "health": "/health",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model_loaded": core._model is not None
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
    if core._model is None:
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
    if core._model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    # Use core module for batch classification
    result_data = core.classify_smiles_list(molecules.smiles_list)
    
    # Convert dict results to ClassificationResult objects
    results = [ClassificationResult(**r) for r in result_data['results']]
    
    return BatchClassificationResult(results=results, summary=result_data['summary'])


@app.post("/api/classify/pubchem", response_model=BatchClassificationResult)
async def classify_from_pubchem(pubchem_input: PubChemInput):
    """
    Fetch molecules from PubChem and classify them.
    
    Args:
        pubchem_input: PubChemInput with list of compound IDs or names
    
    Returns:
        BatchClassificationResult with all predictions and summary statistics
    """
    if core._model is None:
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


@app.post("/api/classify/file")
async def classify_file(
    file: UploadFile = File(...),
    format: str = Form("csv"),
    smiles_col: str = Form("smiles"),
    delimiter: str = Form(","),
    chunksize: int = Form(5000),
    report: bool = Form(False),
    output_format: str = Form("json")
):
    """
    Upload and classify molecules from CSV/TSV/SDF file.
    
    Args:
        file: Uploaded file
        format: File format (csv, tsv, sdf)
        smiles_col: Column name containing SMILES (for CSV/TSV)
        delimiter: Delimiter for CSV/TSV (default: ",")
        chunksize: Number of rows to process per chunk
        report: Whether to generate visualization report
        output_format: Response format (json or csv)
    
    Returns:
        Classification results and summary, optionally with report path
    """
    if core._model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    # Validate format
    if format not in ["csv", "tsv", "sdf"]:
        raise HTTPException(status_code=400, detail="Invalid format. Must be csv, tsv, or sdf")
    
    # Validate output format
    if output_format not in ["json", "csv"]:
        raise HTTPException(status_code=400, detail="Invalid output_format. Must be json or csv")
    
    # Override delimiter for TSV
    if format == "tsv":
        delimiter = "\t"
    
    all_results = []
    
    try:
        # Read file content
        content = await file.read()
        
        if format == "sdf":
            # Handle SDF format
            from io import BytesIO
            sdf_stream = BytesIO(content)
            suppl = Chem.ForwardSDMolSupplier(sdf_stream)
            
            smiles_list = []
            for mol in suppl:
                if mol is not None:
                    smiles = Chem.MolToSmiles(mol)
                    smiles_list.append(smiles)
                else:
                    smiles_list.append("")  # Invalid molecule
            
            # Process in chunks
            for i in range(0, len(smiles_list), chunksize):
                chunk = smiles_list[i:i+chunksize]
                chunk_results = core.classify_smiles_list(chunk)
                all_results.extend(chunk_results['results'])
        
        else:
            # Handle CSV/TSV format
            text_content = content.decode('utf-8')
            df_iterator = pd.read_csv(
                io.StringIO(text_content),
                delimiter=delimiter,
                chunksize=chunksize
            )
            
            for chunk_df in df_iterator:
                # Check if smiles column exists
                if smiles_col not in chunk_df.columns:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Column '{smiles_col}' not found in file. Available columns: {list(chunk_df.columns)}"
                    )
                
                # Extract SMILES and classify
                smiles_list = chunk_df[smiles_col].fillna("").astype(str).tolist()
                chunk_results = core.classify_smiles_list(smiles_list)
                all_results.extend(chunk_results['results'])
        
        # Calculate overall summary
        valid_results = [r for r in all_results if r['valid']]
        rna_count = sum(1 for r in valid_results if r['prediction'] == "RNA_binding")
        protein_count = sum(1 for r in valid_results if r['prediction'] == "Protein_binding")
        avg_confidence = sum(r['confidence'] for r in valid_results) / len(valid_results) if valid_results else 0
        
        summary = {
            "total": len(all_results),
            "valid": len(valid_results),
            "invalid": len(all_results) - len(valid_results),
            "rna_binding": rna_count,
            "protein_binding": protein_count,
            "average_confidence": round(avg_confidence, 4)
        }
        
        # Generate report if requested
        report_path = None
        if report:
            import visualize
            report_dir = f"/tmp/classification_report_{file.filename.replace('.', '_')}"
            visualize.generate_report({'results': all_results, 'summary': summary}, output_dir=report_dir)
            report_path = report_dir
        
        # Return CSV format if requested
        if output_format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'smiles', 'prediction', 'probability_rna', 'probability_protein', 
                'confidence', 'valid', 'error'
            ])
            
            # Write results
            for result in all_results:
                writer.writerow([
                    result['smiles'],
                    result['prediction'],
                    result['probability_rna'],
                    result['probability_protein'],
                    result['confidence'],
                    result['valid'],
                    result.get('error', '')
                ])
            
            # Add summary as comments at the end
            output.write(f"\n# Summary\n")
            output.write(f"# Total: {summary['total']}\n")
            output.write(f"# Valid: {summary['valid']}\n")
            output.write(f"# Invalid: {summary['invalid']}\n")
            output.write(f"# RNA_binding: {summary['rna_binding']}\n")
            output.write(f"# Protein_binding: {summary['protein_binding']}\n")
            output.write(f"# Average_confidence: {summary['average_confidence']}\n")
            
            csv_content = output.getvalue()
            
            return StreamingResponse(
                io.StringIO(csv_content),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=classification_results.csv"}
            )
        
        # Return JSON format (default)
        response = {
            "results": all_results,
            "summary": summary
        }
        
        if report_path:
            response["report_path"] = report_path
        
        return response
    
    except HTTPException:
        # Re-raise HTTPException to preserve status code
        raise
    except pd.errors.ParserError as e:
        raise HTTPException(status_code=400, detail=f"Error parsing file: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
