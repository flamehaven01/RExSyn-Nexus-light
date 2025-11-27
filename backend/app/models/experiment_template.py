"""
Experiment Template Models
===========================

Addresses researcher feedback: "자주 사용하는 실험 설정값을 '나의 템플릿'으로 저장하고,
동료 연구자와 공유할 수 있는 기능을 추가하여 연구의 효율성과 재현성을 높여야 합니다."

This module provides:
- Personal experiment templates
- Shared/public templates
- Template versioning
- Collaboration features
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.db.database import Base


class TemplateVisibility(str, enum.Enum):
    """Template visibility levels."""
    PRIVATE = "private"        # Only creator can see
    ORGANIZATION = "organization"  # All org members can see
    PUBLIC = "public"          # Everyone can see


class TemplateCategory(str, enum.Enum):
    """Template categories for organization."""
    PROTEIN_FOLDING = "protein_folding"
    DRUG_BINDING = "drug_binding"
    DNA_STRUCTURE = "dna_structure"
    RNA_STRUCTURE = "rna_structure"
    ANTIBODY_DESIGN = "antibody_design"
    CUSTOM = "custom"


class ExperimentTemplate(Base):
    """
    Experiment template - reusable experiment configurations.

    Researchers can:
    - Save frequently used settings as templates
    - Share templates with team members
    - Fork and modify others' templates
    - Track template usage and success rates
    """
    __tablename__ = "experiment_templates"

    id = Column(String(50), primary_key=True)  # e.g., "tpl-user123-001"

    # Ownership
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False, index=True)
    org_id = Column(String(50), ForeignKey("organizations.id"), nullable=False)

    # Template metadata
    name = Column(Text, nullable=False)  # User-provided, no arbitrary limit
    description = Column(Text)
    category = Column(Enum(TemplateCategory), default=TemplateCategory.CUSTOM)
    tags = Column(JSON)  # ["protein-folding", "high-accuracy", "slow"]

    # Visibility and sharing
    visibility = Column(Enum(TemplateVisibility), default=TemplateVisibility.PRIVATE, index=True)
    is_featured = Column(Boolean, default=False)  # Featured by admins
    fork_count = Column(Integer, default=0)  # How many times forked
    usage_count = Column(Integer, default=0)  # How many times used

    # Parent template (if forked from another)
    forked_from_id = Column(String(50), ForeignKey("experiment_templates.id"))
    forked_from = relationship("ExperimentTemplate", remote_side=[id], foreign_keys=[forked_from_id])

    # Template configuration (the actual experiment settings)
    config = Column(JSON, nullable=False)
    # Example structure:
    # {
    #   "method": "alphafold3",
    #   "confidence_threshold": 0.7,
    #   "enable_md_refinement": true,
    #   "ethics_config": {...},
    #   "prediction_config": {...}
    # }

    # Template validation
    validated = Column(Boolean, default=False)  # Validated by system/admin
    validation_metrics = Column(JSON)  # Success rate, avg quality, etc.

    # Version control
    version = Column(String(20), default="1.0")
    changelog = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_used_at = Column(DateTime(timezone=True))

    # Statistics
    avg_success_rate = Column(Integer)  # 0-100
    avg_plddt_score = Column(Integer)   # Average quality

    # Relationships
    # user = relationship("User")  # Uncomment when User model is available
    comments = relationship("TemplateComment", back_populates="template")
    ratings = relationship("TemplateRating", back_populates="template")


class TemplateComment(Base):
    """
    Comments on templates for collaboration.

    Allows researchers to:
    - Discuss template parameters
    - Share tips and warnings
    - Request modifications
    """
    __tablename__ = "template_comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(String(50), ForeignKey("experiment_templates.id"), nullable=False, index=True)
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)

    # Comment content
    content = Column(Text, nullable=False)
    is_question = Column(Boolean, default=False)
    is_resolved = Column(Boolean, default=False)

    # Threading
    parent_comment_id = Column(Integer, ForeignKey("template_comments.id"))
    parent_comment = relationship("TemplateComment", remote_side=[id], foreign_keys=[parent_comment_id])

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    template = relationship("ExperimentTemplate", back_populates="comments")


class TemplateRating(Base):
    """
    User ratings for templates.

    Helps identify high-quality, reliable templates.
    """
    __tablename__ = "template_ratings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(String(50), ForeignKey("experiment_templates.id"), nullable=False, index=True)
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)

    # Rating
    rating = Column(Integer, nullable=False)  # 1-5 stars
    review = Column(Text)

    # Helpful votes
    helpful_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    template = relationship("ExperimentTemplate", back_populates="ratings")


# Helper functions
def calculate_template_quality_score(template: ExperimentTemplate) -> float:
    """
    Calculate overall quality score for a template.

    Factors:
    - Usage count (popularity)
    - Success rate (reliability)
    - Average pLDDT (effectiveness)
    - User ratings
    - Fork count (usefulness)

    Returns:
        Quality score 0-100
    """
    score = 0.0

    # Usage popularity (max 20 points)
    if template.usage_count:
        score += min(20, template.usage_count / 10)

    # Success rate (max 30 points)
    if template.avg_success_rate:
        score += (template.avg_success_rate / 100) * 30

    # Quality results (max 25 points)
    if template.avg_plddt_score:
        score += (template.avg_plddt_score / 100) * 25

    # User ratings (max 15 points)
    if template.ratings:
        avg_rating = sum(r.rating for r in template.ratings) / len(template.ratings)
        score += (avg_rating / 5) * 15

    # Fork count (max 10 points)
    if template.fork_count:
        score += min(10, template.fork_count / 5)

    return min(100, score)


def get_recommended_templates_for_sequence(
    sequence_length: int,
    category: TemplateCategory,
    org_id: str
) -> list[str]:
    """
    Recommend templates based on sequence characteristics.

    Returns list of template IDs suitable for the given sequence.
    """
    # This would query the database and apply filters
    # Placeholder for now
    return []
