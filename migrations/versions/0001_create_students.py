"""Create the student registry.

Revision ID: 0001
Revises:
"""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'students',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('first_name', sa.String(80), nullable=False),
        sa.Column('last_name', sa.String(80), nullable=False),
        sa.Column('email', sa.String(254), nullable=False),
        sa.Column('group', sa.String(40), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('email', name='uq_students_email'),
        sa.CheckConstraint('email = lower(email)', name='ck_students_email_lower'),
    )
    op.create_index('ix_students_group', 'students', ['group'])


def downgrade():
    op.drop_index('ix_students_group', table_name='students')
    op.drop_table('students')
