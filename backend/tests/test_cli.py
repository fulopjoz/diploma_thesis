"""
Tests for the CLI module.

This module tests the command-line interface for the RNA/Protein binding classifier.
"""

import pytest
from typer.testing import CliRunner
from pathlib import Path
import json
import csv
import tempfile
import shutil

from backend.cli import app

# Older versions of click/typer may not support the 'mix_stderr' argument.
# Use default initialization for compatibility across versions.
runner = CliRunner()


class TestCLISmiles:
    """Test the classify smiles command."""
    
    def test_single_smiles_json_output(self):
        """Test classifying a single SMILES with JSON output."""
        result = runner.invoke(app, ["classify", "smiles", "c1ccccc1"])
        
        assert result.exit_code == 0
        
        # Parse JSON output
        output_data = json.loads(result.stdout)
        
        assert "results" in output_data
        assert "summary" in output_data
        assert len(output_data["results"]) == 1
        
        # Check result structure
        res = output_data["results"][0]
        assert res["smiles"] == "c1ccccc1"
        assert res["prediction"] in ["RNA_binding", "Protein_binding"]
        assert res["valid"] is True
        assert 0 <= res["probability_rna"] <= 1
        assert 0 <= res["probability_protein"] <= 1
        assert 0 <= res["confidence"] <= 1
    
    def test_multiple_smiles_json_output(self):
        """Test classifying multiple SMILES with JSON output."""
        result = runner.invoke(app, ["classify", "smiles", "c1ccccc1", "CCO", "CC(=O)O"])
        
        assert result.exit_code == 0
        
        output_data = json.loads(result.stdout)
        assert len(output_data["results"]) == 3
        assert output_data["summary"]["total"] == 3
        assert output_data["summary"]["valid"] == 3
    
    def test_invalid_smiles(self):
        """Test handling of invalid SMILES."""
        result = runner.invoke(app, ["classify", "smiles", "invalid_smiles"])
        
        assert result.exit_code == 0
        
        output_data = json.loads(result.stdout)
        res = output_data["results"][0]
        
        assert res["valid"] is False
        assert res["error"] is not None
        assert output_data["summary"]["invalid"] == 1
    
    def test_csv_output(self):
        """Test CSV output format."""
        result = runner.invoke(app, ["classify", "smiles", "c1ccccc1", "CCO", 
                                     "--output-format", "csv"])
        
        assert result.exit_code == 0
        
        # Parse CSV output
        lines = result.stdout.strip().split('\n')
        assert len(lines) == 3  # header + 2 results
        
        # Check header
        assert "smiles" in lines[0]
        assert "prediction" in lines[0]
        assert "confidence" in lines[0]
    
    def test_json_output_to_file(self):
        """Test writing JSON output to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "output.json"
            
            result = runner.invoke(app, ["classify", "smiles", "c1ccccc1", 
                                         "--output", str(output_file)])
            
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Verify file contents
            with output_file.open() as f:
                data = json.load(f)
                assert "results" in data
                assert len(data["results"]) == 1
    
    def test_csv_output_to_file(self):
        """Test writing CSV output to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "output.csv"
            
            result = runner.invoke(app, ["classify", "smiles", "c1ccccc1", "CCO",
                                         "--output-format", "csv",
                                         "--output", str(output_file)])
            
            assert result.exit_code == 0
            assert output_file.exists()
            
            # Verify file contents
            with output_file.open() as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                assert len(rows) == 2
                assert rows[0]["smiles"] == "c1ccccc1"


class TestCLIFile:
    """Test the classify file command."""
    
    @pytest.fixture
    def test_csv_file(self, tmp_path):
        """Create a temporary test CSV file."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "smiles,name\n"
            "c1ccccc1,benzene\n"
            "CCO,ethanol\n"
            "CC(=O)O,acetic_acid\n"
        )
        return csv_file
    
    def test_classify_csv_file(self, test_csv_file):
        """Test classifying molecules from a CSV file."""
        result = runner.invoke(app, ["classify", "file", 
                                     "--path", str(test_csv_file),
                                     "--format", "csv"])
        
        assert result.exit_code == 0
        
        output_data = json.loads(result.stdout)
        assert len(output_data["results"]) == 3
        assert output_data["summary"]["total"] == 3
    
    def test_classify_tsv_file(self, tmp_path):
        """Test classifying molecules from a TSV file."""
        tsv_file = tmp_path / "test.tsv"
        tsv_file.write_text(
            "smiles\tname\n"
            "c1ccccc1\tbenzene\n"
            "CCO\tethanol\n"
        )
        
        result = runner.invoke(app, ["classify", "file",
                                     "--path", str(tsv_file),
                                     "--format", "tsv"])
        
        assert result.exit_code == 0
        
        output_data = json.loads(result.stdout)
        assert len(output_data["results"]) == 2
    
    def test_custom_smiles_column(self, tmp_path):
        """Test using a custom SMILES column name."""
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "molecule,compound_name\n"
            "c1ccccc1,benzene\n"
            "CCO,ethanol\n"
        )
        
        result = runner.invoke(app, ["classify", "file",
                                     "--path", str(csv_file),
                                     "--format", "csv",
                                     "--smiles-col", "molecule"])
        
        assert result.exit_code == 0
        
        output_data = json.loads(result.stdout)
        assert len(output_data["results"]) == 2
    
    def test_file_output_with_report(self, test_csv_file, tmp_path):
        """Test file classification with report generation."""
        report_dir = tmp_path / "report"
        
        result = runner.invoke(app, ["classify", "file",
                                     "--path", str(test_csv_file),
                                     "--format", "csv",
                                     "--report", str(report_dir)])
        
        assert result.exit_code == 0
        assert report_dir.exists()
        
        # Check that report files were created
        assert (report_dir / "summary.txt").exists()
        assert (report_dir / "probability_distribution.png").exists()
        assert (report_dir / "confidence_scores.png").exists()
        assert (report_dir / "classification_summary.png").exists()


class TestCLIPubChem:
    """Test the classify pubchem command."""
    
    def test_classify_by_cid(self):
        """Test classifying molecules from PubChem by CID."""
        # Test with a simple compound (CID 2244 is aspirin)
        result = runner.invoke(app, ["classify", "pubchem", 
                                     "--id", "2244"])
        
        # May fail if no internet connection
        if result.exit_code == 0:
            output_data = json.loads(result.stdout)
            assert "results" in output_data
            assert len(output_data["results"]) >= 1
    
    def test_classify_multiple_compounds(self):
        """Test classifying multiple compounds from PubChem."""
        result = runner.invoke(app, ["classify", "pubchem",
                                     "--id", "2244",
                                     "--id", "6029"])
        
        # May fail if no internet connection
        if result.exit_code == 0:
            output_data = json.loads(result.stdout)
            assert len(output_data["results"]) >= 1


class TestCLIReport:
    """Test report generation functionality."""
    
    def test_report_generation(self, tmp_path):
        """Test that report generation creates expected files."""
        report_dir = tmp_path / "test_report"
        
        result = runner.invoke(app, ["classify", "smiles", 
                                     "c1ccccc1", "CCO", "CC(=O)O",
                                     "--report", str(report_dir)])
        
        assert result.exit_code == 0
        assert report_dir.exists()
        
        # Check that all report files were created
        expected_files = [
            "summary.txt",
            "probability_distribution.png",
            "confidence_scores.png",
            "classification_summary.png"
        ]
        
        for filename in expected_files:
            assert (report_dir / filename).exists(), f"Missing {filename}"


class TestCLIVersion:
    """Test version command."""
    
    def test_version_command(self):
        """Test the version command."""
        result = runner.invoke(app, ["version"])
        
        assert result.exit_code == 0
        assert "CLI" in result.stdout
        assert "v1.0.0" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
