#!/bin/bash

# Define the directory containing the Jupyter Notebooks
NOTEBOOK_DIR="/home/dodo/Download/diplomka_output/mvi/diploma_project_gnn/set2_ml_models/model2_rna_b_prot_b/sageconv/"

# Activate the Python environment if necessary
# source /path/to/env/bin/activate

# Loop through all ipynb files in the directory
for notebook in "$NOTEBOOK_DIR"/*.ipynb; do
    echo "Processing $notebook"
    # Run the notebook with Papermill
    papermill "$notebook" "$notebook" -k python3
done

echo "All notebooks have been executed."