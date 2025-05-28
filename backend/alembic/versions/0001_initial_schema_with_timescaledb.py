"""Initial schema with TimescaleDB setup

Revision ID: 0001
Revises: 
Create Date: 2025-05-27 10:20:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable TimescaleDB extension
    op.execute('CREATE EXTENSION IF NOT EXISTS timescaledb;')
    
    # Create time_series_metadata table
    op.create_table('time_series_metadata',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('time_column', sa.String(), nullable=False),
    sa.Column('value_columns', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_time_series_metadata_created_at', 'time_series_metadata', ['created_at'], unique=False)
    op.create_index('idx_time_series_metadata_time_column', 'time_series_metadata', ['time_column'], unique=False)
    
    # Create time_series_data_points table
    op.create_table('time_series_data_points',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('time_series_id', sa.String(), nullable=False),
    sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    sa.Column('column_name', sa.String(), nullable=False),
    sa.Column('value', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['time_series_id'], ['time_series_metadata.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_time_series_data_points_timestamp', 'time_series_data_points', ['timestamp'], unique=False)
    op.create_index('idx_time_series_data_points_series_time', 'time_series_data_points', ['time_series_id', 'timestamp'], unique=False)
    op.create_index('idx_time_series_data_points_series_column', 'time_series_data_points', ['time_series_id', 'column_name'], unique=False)
    op.create_index('idx_time_series_data_points_series_column_time', 'time_series_data_points', ['time_series_id', 'column_name', 'timestamp'], unique=False)
    
    # Convert time_series_data_points to TimescaleDB hypertable
    op.execute("SELECT create_hypertable('time_series_data_points', 'timestamp');")
    
    # Create additional TimescaleDB policies for better performance
    # Compress data older than 7 days (optional - can be adjusted)
    op.execute("""
        ALTER TABLE time_series_data_points SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'time_series_id, column_name'
        );
    """)
    
    # Add compression policy (compress data older than 1 day)
    op.execute("""
        SELECT add_compression_policy('time_series_data_points', INTERVAL '1 day');
    """)


def downgrade() -> None:
    # Drop compression policy
    op.execute("SELECT remove_compression_policy('time_series_data_points');")
    
    # Drop indexes
    op.drop_index('idx_time_series_data_points_series_column_time', table_name='time_series_data_points')
    op.drop_index('idx_time_series_data_points_series_column', table_name='time_series_data_points')
    op.drop_index('idx_time_series_data_points_series_time', table_name='time_series_data_points')
    op.drop_index('idx_time_series_data_points_timestamp', table_name='time_series_data_points')
    
    # Drop tables (hypertable will be dropped automatically)
    op.drop_table('time_series_data_points')
    
    op.drop_index('idx_time_series_metadata_time_column', table_name='time_series_metadata')
    op.drop_index('idx_time_series_metadata_created_at', table_name='time_series_metadata')
    op.drop_table('time_series_metadata')
    
    # Note: We don't drop the TimescaleDB extension as it might be used by other applications