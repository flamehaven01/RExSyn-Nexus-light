"""
Project Workspace Models
=========================

Addresses researcher feedback: "여러 실험과 결과물을 하나의 '프로젝트'로 묶고,
팀원을 초대하여 데이터를 공유하고 함께 작업할 수 있는 워크스페이스 기능을 도입해야 합니다."

This module provides:
- Project-based workspace organization
- Team member management
- Shared experiment collections
- Collaborative result discussion
- Project-level permissions
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, ForeignKey, Enum, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.db.database import Base


class ProjectRole(str, enum.Enum):
    """Roles within a project."""
    OWNER = "owner"              # Created project, full control
    ADMIN = "admin"              # Can manage members and settings
    CONTRIBUTOR = "contributor"  # Can add/edit experiments
    VIEWER = "viewer"           # Read-only access


class ProjectStatus(str, enum.Enum):
    """Project status."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    COMPLETED = "completed"


# Association table for project members
project_members = Table(
    'project_members',
    Base.metadata,
    Column('project_id', String(50), ForeignKey('projects.id'), primary_key=True),
    Column('user_id', String(50), ForeignKey('users.id'), primary_key=True),
    Column('role', Enum(ProjectRole), nullable=False, default=ProjectRole.VIEWER),
    Column('joined_at', DateTime(timezone=True), server_default=func.now()),
    Column('invited_by', String(50), ForeignKey('users.id')),
)


class Project(Base):
    """
    Research project workspace.

    Allows teams to:
    - Group related experiments
    - Share results and data
    - Collaborate with comments and discussions
    - Track progress toward research goals
    """
    __tablename__ = "projects"

    id = Column(String(50), primary_key=True)  # e.g., "proj-lab123-001"

    # Project metadata
    name = Column(Text, nullable=False)
    description = Column(Text)
    research_area = Column(String(100))  # e.g., "protein-folding", "drug-discovery"
    tags = Column(JSON)  # ["antibody", "covid-19", "high-throughput"]

    # Organization
    org_id = Column(String(50), ForeignKey("organizations.id"), nullable=False)
    created_by = Column(String(50), ForeignKey("users.id"), nullable=False)

    # Status
    status = Column(Enum(ProjectStatus), default=ProjectStatus.ACTIVE, index=True)
    is_public = Column(Boolean, default=False)  # Publicly visible
    is_featured = Column(Boolean, default=False)  # Featured by platform

    # Progress tracking
    target_experiments = Column(Integer)  # Goal: 100 experiments
    completed_experiments = Column(Integer, default=0)
    success_rate = Column(Integer)  # % of successful experiments

    # Publication info
    paper_title = Column(Text)
    paper_doi = Column(String(255))
    paper_url = Column(Text)

    # Collaboration settings
    allow_external_collaborators = Column(Boolean, default=False)
    require_approval_for_join = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    archived_at = Column(DateTime(timezone=True))

    # Relationships
    experiments = relationship("ProjectExperiment", back_populates="project")
    discussions = relationship("ProjectDiscussion", back_populates="project")
    milestones = relationship("ProjectMilestone", back_populates="project")


class ProjectExperiment(Base):
    """
    Link between projects and experiments (jobs).

    One experiment can belong to multiple projects.
    """
    __tablename__ = "project_experiments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(50), ForeignKey("projects.id"), nullable=False, index=True)
    job_id = Column(String(50), ForeignKey("jobs.id"), nullable=False, index=True)

    # Metadata
    added_by = Column(String(50), ForeignKey("users.id"), nullable=False)
    notes = Column(Text)  # Why this experiment is relevant to project
    tags = Column(JSON)  # Project-specific tags

    # Status
    is_featured = Column(Boolean, default=False)  # Highlight important results
    is_milestone = Column(Boolean, default=False)  # Marks a milestone achievement

    # Timestamps
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    project = relationship("Project", back_populates="experiments")
    comments = relationship("ExperimentComment", back_populates="experiment_link")


class ExperimentComment(Base):
    """
    Comments on experiment results within project context.

    Allows team discussion about specific results.
    """
    __tablename__ = "experiment_comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    experiment_link_id = Column(Integer, ForeignKey("project_experiments.id"), nullable=False, index=True)
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)

    # Comment content
    content = Column(Text, nullable=False)
    comment_type = Column(String(50), default="general")  # general, question, suggestion, issue

    # Threading
    parent_comment_id = Column(Integer, ForeignKey("experiment_comments.id"))

    # Status
    is_resolved = Column(Boolean, default=False)
    resolved_by = Column(String(50), ForeignKey("users.id"))
    resolved_at = Column(DateTime(timezone=True))

    # Reactions
    reactions = Column(JSON)  # {"thumbs_up": 5, "important": 2}

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    experiment_link = relationship("ProjectExperiment", back_populates="comments")


class ProjectDiscussion(Base):
    """
    General discussions within project (not tied to specific experiment).

    For brainstorming, planning, announcements, etc.
    """
    __tablename__ = "project_discussions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(50), ForeignKey("projects.id"), nullable=False, index=True)
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)

    # Discussion content
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    discussion_type = Column(String(50), default="general")  # general, announcement, question, decision

    # Status
    is_pinned = Column(Boolean, default=False)
    is_locked = Column(Boolean, default=False)
    is_resolved = Column(Boolean, default=False)

    # Engagement
    view_count = Column(Integer, default=0)
    reply_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    project = relationship("Project", back_populates="discussions")
    replies = relationship("DiscussionReply", back_populates="discussion")


class DiscussionReply(Base):
    """Replies to project discussions."""
    __tablename__ = "discussion_replies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    discussion_id = Column(Integer, ForeignKey("project_discussions.id"), nullable=False, index=True)
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)

    # Reply content
    content = Column(Text, nullable=False)

    # Threading
    parent_reply_id = Column(Integer, ForeignKey("discussion_replies.id"))

    # Reactions
    reactions = Column(JSON)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    discussion = relationship("ProjectDiscussion", back_populates="replies")


class ProjectMilestone(Base):
    """
    Project milestones and goals.

    Track progress toward research objectives.
    """
    __tablename__ = "project_milestones"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String(50), ForeignKey("projects.id"), nullable=False, index=True)

    # Milestone details
    title = Column(Text, nullable=False)
    description = Column(Text)
    target_date = Column(DateTime(timezone=True))

    # Progress
    is_completed = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True))
    completion_notes = Column(Text)

    # Linked experiments
    linked_experiments = Column(JSON)  # List of job_ids that achieved this milestone

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    project = relationship("Project", back_populates="milestones")


# Helper functions
def get_user_role_in_project(project_id: str, user_id: str) -> ProjectRole:
    """
    Get user's role in a project.

    Returns:
        ProjectRole if user is member, None otherwise
    """
    # This would query the database
    # Placeholder for now
    return ProjectRole.VIEWER


def can_user_edit_project(project_id: str, user_id: str) -> bool:
    """
    Check if user can edit project (add experiments, modify settings).

    Returns:
        True if user is OWNER, ADMIN, or CONTRIBUTOR
    """
    role = get_user_role_in_project(project_id, user_id)
    return role in [ProjectRole.OWNER, ProjectRole.ADMIN, ProjectRole.CONTRIBUTOR]


def get_project_statistics(project_id: str) -> dict:
    """
    Calculate project statistics.

    Returns:
        Dict with experiment count, success rate, avg quality, etc.
    """
    # This would aggregate from database
    # Placeholder for now
    return {
        "total_experiments": 0,
        "successful_experiments": 0,
        "success_rate": 0.0,
        "avg_plddt": 0.0,
        "total_members": 0,
        "total_discussions": 0,
        "completed_milestones": 0,
        "total_milestones": 0,
    }
