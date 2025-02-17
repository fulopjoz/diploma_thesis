# Diploma Thesis Repository: Cheminformatics Analysis of RNA-Binding Ligands

**Author:** Jozef Fulop  
**Institution:** UCT in Prague  

Welcome to the repository for my diploma thesis. This project explores both ensemble and graph neural network (GNN) models applied to cheminformatics data. The repository includes documentation, code, and data resources aimed in machine learning and cheminformatics.

## Data

The raw and machine learning datasets for **Set 1** and **Set 2** are hosted externally due to their size. You can access them via the following link: [Dataset Link](https://owncloud.cesnet.cz/index.php/s/juPLpmojqktq0IU).

## Notebooks
**Additional notebooks and processing using GNN** can be found here: [Github Repo for GNN](https://github.com/fulopjoz/gnn-rna-ligands-thesis/tree/master)

## Project Overview

### Objectives

The primary objective of this research is to develop, train, and evaluate advanced machine learning models, focusing specifically on:

- **Ensemble Learning Techniques:** Application for molecular classification tasks.
- **Graph Neural Networks (GNNs):** Exploration of their effectiveness in molecular classification.

### Methodology

1. **Data Collection and Preparation:**  
   - Extensive datasets compiled from chemical libraries.  
   - Separate datasets created for RNA-binding and protein-binding ligands.
     
2. **Model Architectures:**  
   - **Ensemble Models:**  
     - Ensemble architectures tailored for cheminformatics data.  
   - **Graph Neural Networks (GNNs):**  
     - Implemented advanced GNN architectures such as Gated Graph Neural Network, GATv2Conv, and SaGEConv.  
     - An [IPython Notebook for creating graph representations from molecules](models/gnn/mol2graphs.ipynb) is provided to demonstrate the conversion of molecular data into graph structures.

3. **Feature Engineering and Property Analysis:**  
   - Used RDKit to compute molecular properties like molecular weight, ClogP, and hydrogen bond acceptors/donors.
   - Scaffold analysis performed using Murcko and CSK scaffolds.

4. **Model Optimization and Validation:**  
   - Optimized models with Optuna.  
   - Evaluated using accuracy, F1-score, and other metrics.

### Key Contributions

1. **Model Architectures:**  
   - GNN and ensemble architectures tailored to cheminformatics.

2. **Dataset Curation:**  
   - Comprehensive pre-processing and curation of diverse molecular datasets.

3. **Performance Evaluation:**  
   - Evaluation through performance metrics and visualization.

## Directory Structure

The repository is structured into the following directories:

- `models`:  
  - **Ensemble:** Ensemble model configurations and results.  
  - **GNN:** Graph neural network models with results.
- `notebooks`:  
  - Analysis notebooks for data exploration, feature engineering, and modeling.
- `output`:  
  - Final outputs like figures, tables, scaffold analysis, and model validation metrics.

