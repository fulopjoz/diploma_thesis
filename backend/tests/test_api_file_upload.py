"""
Tests for file upload API endpoint.
"""

import pytest
from fastapi.testclient import TestClient
import os
import io
import json

# Import the FastAPI app
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core
from app import app

# Ensure model is loaded before tests
@pytest.fixture(scope="module", autouse=True)
def setup_model():
    """Load the model before running tests."""
    core.load_model()
    yield

client = TestClient(app)

# Test data directory
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def test_health_check():
    """Test that the API is healthy and model is loaded."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True


def test_upload_csv_default_params():
    """Test uploading a CSV file with default parameters."""
    csv_file_path = os.path.join(TEST_DATA_DIR, "test_rna_binders.csv")
    
    with open(csv_file_path, "rb") as f:
        files = {"file": ("test.csv", f, "text/csv")}
        data = {
            "format": "csv",
            "smiles_col": "Murcko_scafold"  # Using the actual column name from test data
        }
        response = client.post("/api/classify/file", files=files, data=data)
    
    assert response.status_code == 200
    result = response.json()
    
    # Check structure
    assert "results" in result
    assert "summary" in result
    
    # Check summary
    summary = result["summary"]
    assert summary["total"] == 10  # 10 molecules (excluding header)
    assert summary["valid"] >= 0
    assert summary["invalid"] >= 0
    assert summary["total"] == summary["valid"] + summary["invalid"]
    assert "rna_binding" in summary
    assert "protein_binding" in summary
    assert "average_confidence" in summary
    
    # Check results structure
    assert len(result["results"]) == 10
    for res in result["results"]:
        assert "smiles" in res
        assert "prediction" in res
        assert "probability_rna" in res
        assert "probability_protein" in res
        assert "confidence" in res
        assert "valid" in res


def test_upload_tsv_file():
    """Test uploading a TSV file."""
    tsv_file_path = os.path.join(TEST_DATA_DIR, "test_molecules.tsv")
    
    with open(tsv_file_path, "rb") as f:
        files = {"file": ("test.tsv", f, "text/tab-separated-values")}
        data = {
            "format": "tsv",
            "smiles_col": "smiles"
        }
        response = client.post("/api/classify/file", files=files, data=data)
    
    assert response.status_code == 200
    result = response.json()
    
    # Check structure
    assert "results" in result
    assert "summary" in result
    
    # Should have 5 molecules
    assert result["summary"]["total"] == 5
    
    # At least one should be invalid (invalid_smiles)
    assert result["summary"]["invalid"] >= 1


def test_upload_csv_custom_column():
    """Test uploading CSV with custom SMILES column name."""
    csv_file_path = os.path.join(TEST_DATA_DIR, "test_smiles_column.csv")
    
    with open(csv_file_path, "rb") as f:
        files = {"file": ("test.csv", f, "text/csv")}
        data = {
            "format": "csv",
            "smiles_col": "compound_smiles"
        }
        response = client.post("/api/classify/file", files=files, data=data)
    
    assert response.status_code == 200
    result = response.json()
    
    assert result["summary"]["total"] == 4
    # Should have at least one invalid (invalid_smile)
    assert result["summary"]["invalid"] >= 1


def test_upload_csv_output_format_csv():
    """Test requesting CSV output format."""
    csv_file_path = os.path.join(TEST_DATA_DIR, "test_smiles_column.csv")
    
    with open(csv_file_path, "rb") as f:
        files = {"file": ("test.csv", f, "text/csv")}
        data = {
            "format": "csv",
            "smiles_col": "compound_smiles",
            "output_format": "csv"
        }
        response = client.post("/api/classify/file", files=files, data=data)
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    
    # Check CSV content
    csv_content = response.text
    assert "smiles,prediction,probability_rna" in csv_content
    assert "# Summary" in csv_content
    assert "# Total:" in csv_content


def test_upload_invalid_format():
    """Test uploading with invalid format parameter."""
    csv_file_path = os.path.join(TEST_DATA_DIR, "test_smiles_column.csv")
    
    with open(csv_file_path, "rb") as f:
        files = {"file": ("test.csv", f, "text/csv")}
        data = {
            "format": "invalid_format",
            "smiles_col": "compound_smiles"
        }
        response = client.post("/api/classify/file", files=files, data=data)
    
    assert response.status_code == 400
    assert "Invalid format" in response.json()["detail"]


def test_upload_invalid_column_name():
    """Test uploading with non-existent SMILES column."""
    csv_file_path = os.path.join(TEST_DATA_DIR, "test_smiles_column.csv")
    
    with open(csv_file_path, "rb") as f:
        files = {"file": ("test.csv", f, "text/csv")}
        data = {
            "format": "csv",
            "smiles_col": "nonexistent_column"
        }
        response = client.post("/api/classify/file", files=files, data=data)
    
    assert response.status_code == 400
    assert "not found in file" in response.json()["detail"]


def test_upload_with_report_generation():
    """Test uploading with report generation enabled."""
    csv_file_path = os.path.join(TEST_DATA_DIR, "test_smiles_column.csv")
    
    with open(csv_file_path, "rb") as f:
        files = {"file": ("test.csv", f, "text/csv")}
        data = {
            "format": "csv",
            "smiles_col": "compound_smiles",
            "report": "true"
        }
        response = client.post("/api/classify/file", files=files, data=data)
    
    assert response.status_code == 200
    result = response.json()
    
    # Check that report_path is present
    assert "report_path" in result
    assert result["report_path"] is not None
    
    # Verify report directory exists and has files
    report_path = result["report_path"]
    assert os.path.exists(report_path)
    
    # Check for expected files
    expected_files = [
        "probability_distribution.png",
        "confidence_scores.png",
        "classification_summary.png",
        "summary.txt"
    ]
    
    for expected_file in expected_files:
        file_path = os.path.join(report_path, expected_file)
        assert os.path.exists(file_path), f"Expected file {expected_file} not found in report"


def test_invalid_handling_preservation():
    """Test that invalid entries are preserved and tracked correctly."""
    csv_file_path = os.path.join(TEST_DATA_DIR, "test_smiles_column.csv")
    
    with open(csv_file_path, "rb") as f:
        files = {"file": ("test.csv", f, "text/csv")}
        data = {
            "format": "csv",
            "smiles_col": "compound_smiles"
        }
        response = client.post("/api/classify/file", files=files, data=data)
    
    assert response.status_code == 200
    result = response.json()
    
    # Find the invalid result
    invalid_results = [r for r in result["results"] if not r["valid"]]
    assert len(invalid_results) >= 1
    
    # Check invalid result has correct structure
    for invalid_res in invalid_results:
        assert invalid_res["valid"] is False
        assert invalid_res["error"] is not None
        assert invalid_res["prediction"] == "Invalid"


def test_chunked_processing():
    """Test that chunked processing works correctly."""
    # Create a larger test file in memory
    csv_content = "smiles,name\n"
    test_smiles = ["c1ccccc1", "CCO", "CC(=O)O", "c1cccnc1", "c1ccncc1"]
    
    # Repeat to create more rows
    for i in range(20):
        for smiles in test_smiles:
            csv_content += f"{smiles},mol_{i}\n"
    
    files = {"file": ("large_test.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    data = {
        "format": "csv",
        "smiles_col": "smiles",
        "chunksize": "10"  # Small chunk size to test chunking
    }
    response = client.post("/api/classify/file", files=files, data=data)
    
    assert response.status_code == 200
    result = response.json()
    
    # Should have 100 results (20 iterations * 5 molecules)
    assert result["summary"]["total"] == 100
    assert len(result["results"]) == 100


def test_order_preservation():
    """Test that the order of results matches input order."""
    csv_content = "smiles,id\n"
    csv_content += "c1ccccc1,first\n"
    csv_content += "CCO,second\n"
    csv_content += "invalid,third\n"
    csv_content += "CC(=O)O,fourth\n"
    
    files = {"file": ("order_test.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    data = {
        "format": "csv",
        "smiles_col": "smiles"
    }
    response = client.post("/api/classify/file", files=files, data=data)
    
    assert response.status_code == 200
    result = response.json()
    
    # Check order is preserved
    assert result["results"][0]["smiles"] == "c1ccccc1"
    assert result["results"][1]["smiles"] == "CCO"
    assert result["results"][2]["smiles"] == "invalid"
    assert result["results"][3]["smiles"] == "CC(=O)O"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
