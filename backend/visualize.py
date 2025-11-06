"""
Visualization utilities for classification results.

This module provides functions to visualize classification results,
including probability distributions, confidence scores, and molecule structures.
"""

import matplotlib.pyplot as plt
import numpy as np
from typing import List, Dict
import os


def plot_probability_distribution(results: List[Dict], output_path: str = None):
    """
    Plot the distribution of RNA vs Protein binding probabilities.
    
    Args:
        results: List of classification results
        output_path: Optional path to save the plot
    """
    valid_results = [r for r in results if r['valid']]
    
    if not valid_results:
        print("No valid results to plot")
        return
    
    rna_probs = [r['probability_rna'] for r in valid_results]
    protein_probs = [r['probability_protein'] for r in valid_results]
    
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    
    # RNA binding probabilities
    axes[0].hist(rna_probs, bins=20, color='blue', alpha=0.7, edgecolor='black')
    axes[0].set_xlabel('Probability')
    axes[0].set_ylabel('Count')
    axes[0].set_title('RNA Binding Probability Distribution')
    axes[0].grid(True, alpha=0.3)
    
    # Protein binding probabilities
    axes[1].hist(protein_probs, bins=20, color='green', alpha=0.7, edgecolor='black')
    axes[1].set_xlabel('Probability')
    axes[1].set_ylabel('Count')
    axes[1].set_title('Protein Binding Probability Distribution')
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Plot saved to {output_path}")
    else:
        plt.show()


def plot_confidence_scores(results: List[Dict], output_path: str = None):
    """
    Plot confidence scores for all predictions.
    
    Args:
        results: List of classification results
        output_path: Optional path to save the plot
    """
    valid_results = [r for r in results if r['valid']]
    
    if not valid_results:
        print("No valid results to plot")
        return
    
    confidences = [r['confidence'] for r in valid_results]
    predictions = [r['prediction'] for r in valid_results]
    
    # Separate by prediction type
    rna_conf = [c for c, p in zip(confidences, predictions) if p == 'RNA_binding']
    protein_conf = [c for c, p in zip(confidences, predictions) if p == 'Protein_binding']
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    positions = []
    colors = []
    labels = []
    
    if rna_conf:
        positions.append(1)
        colors.append('blue')
        labels.append(f'RNA Binding\n(n={len(rna_conf)})')
    
    if protein_conf:
        positions.append(2)
        colors.append('green')
        labels.append(f'Protein Binding\n(n={len(protein_conf)})')
    
    data = [d for d in [rna_conf, protein_conf] if d]
    
    bp = ax.boxplot(data, positions=positions, widths=0.6, patch_artist=True,
                    showmeans=True, meanline=True)
    
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    ax.set_xticks(positions)
    ax.set_xticklabels(labels)
    ax.set_ylabel('Confidence Score')
    ax.set_title('Confidence Scores by Prediction Type')
    ax.set_ylim(0, 1.05)
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Plot saved to {output_path}")
    else:
        plt.show()


def plot_classification_summary(summary: Dict, output_path: str = None):
    """
    Plot a pie chart of classification summary.
    
    Args:
        summary: Summary dictionary from batch classification
        output_path: Optional path to save the plot
    """
    rna_count = summary.get('rna_binding', 0)
    protein_count = summary.get('protein_binding', 0)
    invalid_count = summary.get('invalid', 0)
    
    labels = []
    sizes = []
    colors = []
    
    if rna_count > 0:
        labels.append(f'RNA Binding\n({rna_count})')
        sizes.append(rna_count)
        colors.append('#3498db')
    
    if protein_count > 0:
        labels.append(f'Protein Binding\n({protein_count})')
        sizes.append(protein_count)
        colors.append('#2ecc71')
    
    if invalid_count > 0:
        labels.append(f'Invalid\n({invalid_count})')
        sizes.append(invalid_count)
        colors.append('#e74c3c')
    
    if not sizes:
        print("No data to plot")
        return
    
    fig, ax = plt.subplots(figsize=(8, 8))
    
    wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors,
                                        autopct='%1.1f%%', startangle=90,
                                        textprops={'fontsize': 12})
    
    ax.set_title('Classification Results Summary', fontsize=16, fontweight='bold')
    
    # Add total count
    total = summary.get('total', sum(sizes))
    avg_conf = summary.get('average_confidence', 0)
    
    info_text = f"Total: {total}\nAvg Confidence: {avg_conf:.2%}"
    ax.text(0, -1.3, info_text, ha='center', fontsize=12,
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    
    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"Plot saved to {output_path}")
    else:
        plt.show()


def generate_report(results_data: Dict, output_dir: str = "/tmp/classification_report"):
    """
    Generate a complete visualization report.
    
    Args:
        results_data: Dictionary containing 'results' and 'summary' keys
        output_dir: Directory to save the report
    """
    os.makedirs(output_dir, exist_ok=True)
    
    results = results_data.get('results', [])
    summary = results_data.get('summary', {})
    
    print(f"Generating classification report in {output_dir}...")
    
    # Generate all plots
    plot_probability_distribution(results, 
                                  os.path.join(output_dir, 'probability_distribution.png'))
    plot_confidence_scores(results, 
                          os.path.join(output_dir, 'confidence_scores.png'))
    plot_classification_summary(summary, 
                               os.path.join(output_dir, 'classification_summary.png'))
    
    # Generate text summary
    with open(os.path.join(output_dir, 'summary.txt'), 'w') as f:
        f.write("RNA/Protein Binding Classification Report\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total molecules: {summary.get('total', 0)}\n")
        f.write(f"Valid predictions: {summary.get('valid', 0)}\n")
        f.write(f"Invalid SMILES: {summary.get('invalid', 0)}\n\n")
        f.write(f"RNA binding: {summary.get('rna_binding', 0)}\n")
        f.write(f"Protein binding: {summary.get('protein_binding', 0)}\n\n")
        f.write(f"Average confidence: {summary.get('average_confidence', 0):.4f}\n\n")
        
        valid_results = [r for r in results if r['valid']]
        if valid_results:
            confidences = [r['confidence'] for r in valid_results]
            f.write(f"Confidence statistics:\n")
            f.write(f"  Min: {min(confidences):.4f}\n")
            f.write(f"  Max: {max(confidences):.4f}\n")
            f.write(f"  Mean: {np.mean(confidences):.4f}\n")
            f.write(f"  Median: {np.median(confidences):.4f}\n")
            f.write(f"  Std Dev: {np.std(confidences):.4f}\n")
    
    print(f"Report generated successfully!")
    print(f"Files created:")
    print(f"  - probability_distribution.png")
    print(f"  - confidence_scores.png")
    print(f"  - classification_summary.png")
    print(f"  - summary.txt")


if __name__ == "__main__":
    # Example usage
    print("This module provides visualization utilities.")
    print("Import it in your script to use the visualization functions.")
    print("\nExample:")
    print("  from visualize import plot_classification_summary")
    print("  plot_classification_summary(summary_dict)")
