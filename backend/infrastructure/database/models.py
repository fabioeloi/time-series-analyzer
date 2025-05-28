"""SQLAlchemy models for TimescaleDB schema"""
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Float, Integer, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from .config import Base


class TimeSeriesMetadata(Base):
    """Table for storing TimeSeries metadata"""
    __tablename__ = "time_series_metadata"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    time_column = Column(String, nullable=False)
    value_columns = Column(Text, nullable=False)  # JSON string of column names
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship to data points
    data_points = relationship("TimeSeriesDataPoint", back_populates="time_series_metadata", cascade="all, delete-orphan")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_time_series_metadata_created_at', 'created_at'),
        Index('idx_time_series_metadata_time_column', 'time_column'),
    )


class TimeSeriesDataPoint(Base):
    """TimescaleDB hypertable for storing time-series data points"""
    __tablename__ = "time_series_data_points"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    time_series_id = Column(String, ForeignKey("time_series_metadata.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    
    # Dynamic value columns - we'll use a flexible approach with JSON-like storage
    # For better performance, we could have multiple value columns (value_1, value_2, etc.)
    # but for flexibility, we'll store column name and value
    column_name = Column(String, nullable=False)
    value = Column(Float, nullable=True)  # Allow NULL for NaN values
    
    # Relationship back to metadata
    time_series_metadata = relationship("TimeSeriesMetadata", back_populates="data_points")
    
    # TimescaleDB hypertable configuration (done via migration)
    # Indexes for efficient time-series queries
    __table_args__ = (
        Index('idx_time_series_data_points_timestamp', 'timestamp'),
        Index('idx_time_series_data_points_series_time', 'time_series_id', 'timestamp'),
        Index('idx_time_series_data_points_series_column', 'time_series_id', 'column_name'),
        Index('idx_time_series_data_points_series_column_time', 'time_series_id', 'column_name', 'timestamp'),
    )