"""
Unit tests for core classification logic.
"""

import os
import sys
import numpy as np
import pytest

# Ensure backend package is importable when running tests directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def _load_model_once():
    core.load_model()
    yield


def test_smiles_to_ecfp6_valid_shape_and_dtype():
    arr = core.smiles_to_ecfp6("c1ccccc1")  # benzene
    assert isinstance(arr, np.ndarray)
    assert arr.shape == (core.ECFP_NBITS,)
    assert arr.dtype == np.int8
    # bits should be 0/1
    assert np.isin(arr, [0, 1]).all()


def test_smiles_to_ecfp6_invalid_returns_none():
    assert core.smiles_to_ecfp6("not_a_smiles") is None


def test_classify_smiles_list_basic_counts_and_structure():
    inputs = ["c1ccccc1", "CCO", "invalid", "CC(=O)O"]
    out = core.classify_smiles_list(inputs)

    assert "results" in out and "summary" in out
    results = out["results"]
    summary = out["summary"]

    # Structure
    assert len(results) == len(inputs)
    for r in results:
        assert set(["smiles", "prediction", "probability_rna", "probability_protein", "confidence", "valid", "error"]).issubset(r.keys())

    # Summary consistency
    assert summary["total"] == len(inputs)
    assert summary["total"] == summary["valid"] + summary["invalid"]
    assert "rna_binding" in summary and "protein_binding" in summary
    assert "average_confidence" in summary
