"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-12-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create repositories table
    op.create_table(
        'repositories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('url', sa.String(500), nullable=False, unique=True),
        sa.Column('provider', sa.String(50), default='github'),
        sa.Column('name', sa.String(255)),
        sa.Column('owner', sa.String(255)),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_repositories_url', 'repositories', ['url'])

    # Create analysis_runs table
    op.create_table(
        'analysis_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('repository_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('repositories.id'), nullable=False),
        sa.Column('status', sa.String(20), default='queued'),
        sa.Column('branch', sa.String(255)),
        sa.Column('commit_sha', sa.String(40)),
        sa.Column('region_mode', sa.String(10), default='EU_UA'),
        sa.Column('started_at', sa.DateTime()),
        sa.Column('finished_at', sa.DateTime()),
        sa.Column('error_message', sa.Text()),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
    )
    op.create_index('ix_analysis_runs_repository_id', 'analysis_runs', ['repository_id'])
    op.create_index('ix_analysis_runs_status', 'analysis_runs', ['status'])

    # Create metrics table
    op.create_table(
        'metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('analysis_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('analysis_runs.id'), nullable=False, unique=True),
        sa.Column('repo_health', postgresql.JSON()),
        sa.Column('tech_debt', postgresql.JSON()),
        sa.Column('product_level', sa.String(50)),
        sa.Column('complexity', sa.String(10)),
        sa.Column('cost_estimates', postgresql.JSON()),
        sa.Column('historical_estimate', postgresql.JSON()),
        sa.Column('structure_data', postgresql.JSON()),
        sa.Column('static_metrics', postgresql.JSON()),
        sa.Column('semgrep_findings', postgresql.JSON()),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
    )
    op.create_index('ix_metrics_analysis_id', 'metrics', ['analysis_id'])

    # Create tasks table
    op.create_table(
        'tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('analysis_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('analysis_runs.id'), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('category', sa.String(50)),
        sa.Column('priority', sa.String(10), default='P2'),
        sa.Column('status', sa.String(20), default='open'),
        sa.Column('estimate_hours', sa.Integer()),
        sa.Column('labels', postgresql.JSON()),
        sa.Column('github_issue_number', sa.Integer()),
        sa.Column('github_issue_url', sa.String(500)),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
    )
    op.create_index('ix_tasks_analysis_id', 'tasks', ['analysis_id'])
    op.create_index('ix_tasks_priority', 'tasks', ['priority'])


def downgrade() -> None:
    op.drop_table('tasks')
    op.drop_table('metrics')
    op.drop_table('analysis_runs')
    op.drop_table('repositories')
