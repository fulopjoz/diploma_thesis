"""
SQLAlchemy models for classification job persistence.

Models:
- Job: Represents a classification job with metadata
- Molecule: Individual molecules processed in a job
- Prediction: Classification predictions for each molecule
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship
from uuid import uuid4

Base = declarative_base()


class Job(Base):
    """
    Classification job metadata.
    
    Stores information about batch classification requests including
    input parameters, timing, and summary statistics.
    """
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Input metadata
    input_type = Column(String(50), nullable=False, index=True)  # smiles, file, pubchem, batch
    params = Column(JSON, nullable=True)  # Additional parameters (file format, column names, etc.)
    
    # Status and timing
    status = Column(String(20), nullable=False, default="completed", index=True)  # completed, failed, processing
    duration_ms = Column(Integer, nullable=True)  # Processing duration in milliseconds
    
    # Summary statistics (cached from aggregation)
    summary = Column(JSON, nullable=True)  # {total, valid, invalid, rna_binding, protein_binding, average_confidence}
    
    # Optional report paths
    report_path = Column(String(500), nullable=True)
    
    # Relationships
    molecules = relationship("Molecule", back_populates="job", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Job(id={self.id}, input_type={self.input_type}, status={self.status})>"


class Molecule(Base):
    """
    Individual molecule in a classification job.
    
    Stores input SMILES, validation status, and links to predictions.
    """
    __tablename__ = "molecules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Input data
    input_smiles = Column(Text, nullable=False)  # Original SMILES string
    normalized_smiles = Column(Text, nullable=True)  # Normalized/canonical SMILES if different
    
    # Validation
    is_valid = Column(Boolean, nullable=False, default=True, index=True)
    error = Column(Text, nullable=True)  # Error message if invalid
    
    # Relationships
    job = relationship("Job", back_populates="molecules")
    prediction = relationship("Prediction", back_populates="molecule", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Molecule(id={self.id}, smiles={self.input_smiles[:30]}, valid={self.is_valid})>"


class Prediction(Base):
    """
    Classification prediction for a molecule.
    
    Stores the model's prediction, probabilities, and confidence scores.
    """
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    molecule_id = Column(Integer, ForeignKey("molecules.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Prediction results
    label = Column(String(50), nullable=False, index=True)  # RNA_binding, Protein_binding, Invalid
    probability_rna = Column(Float, nullable=False)
    probability_protein = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False, index=True)  # max(probability_rna, probability_protein)
    
    # Relationships
    molecule = relationship("Molecule", back_populates="prediction")
    
    def __repr__(self):
        return f"<Prediction(id={self.id}, label={self.label}, confidence={self.confidence:.3f})>"
