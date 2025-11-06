#!/bin/bash
# Startup script for the RNA/Protein Binding Classifier API

echo "Starting RNA/Protein Binding Classifier API..."
echo "=============================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -r requirements.txt --quiet

# Check if model exists
if [ ! -f "../models/ensemble/set1/best_xgb.joblib" ]; then
    echo "ERROR: Model file not found at ../models/ensemble/set1/best_xgb.joblib"
    echo "Please ensure the model file is in the correct location."
    exit 1
fi

echo "Model file found."
echo ""

# Run tests
echo "Running basic tests..."
python test_classifier.py

if [ $? -eq 0 ]; then
    echo ""
    echo "Tests passed! Starting API server..."
    echo "=============================================="
    echo ""
    
    # Start the server
    uvicorn app:app --host 0.0.0.0 --port 8000
else
    echo ""
    echo "Tests failed! Please check the error messages above."
    exit 1
fi
