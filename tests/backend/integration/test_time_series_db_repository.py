import sys
import os
import pytest
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add the backend directory to the path to import modules
sys.path.append(str(Path(__file__).parent.parent.parent.parent / "backend"))

from infrastructure.database.models import Base, TimeSeriesMetadata, TimeSeriesDataPoint
from infrastructure.database.repositories.time_series_db_repository import TimeSeriesDBRepository
from domain.models.time_series import TimeSeries

# Use an in-memory SQLite database for testing
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="function")
async def db_session():
    """Fixture for a database session with a clean slate for each test."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
def sample_time_series():
    """Fixture for a sample TimeSeries object."""
    data = pd.DataFrame({
        'timestamp': pd.to_datetime(['2023-01-01 00:00:00', '2023-01-01 01:00:00', '2023-01-01 02:00:00']),
        'temperature': [20.0, 21.5, 22.0],
        'humidity': [60.0, 61.0, 62.5]
    })
    return TimeSeries.create(
        data=data,
        time_column='timestamp',
        value_columns=['temperature', 'humidity']
    )

@pytest.fixture
def sample_time_series_update():
    """Fixture for an updated sample TimeSeries object."""
    data = pd.DataFrame({
        'timestamp': pd.to_datetime(['2023-01-01 00:00:00', '2023-01-01 01:00:00', '2023-01-01 02:00:00', '2023-01-01 03:00:00']),
        'temperature': [25.0, 26.0, 27.0, 28.0],
        'pressure': [1000.0, 1001.0, 1002.0, 1003.0]
    })
    return TimeSeries.create(
        data=data,
        time_column='timestamp',
        value_columns=['temperature', 'pressure']
    )

@pytest.mark.asyncio
class TestTimeSeriesDBRepository:
    async def test_save_new_time_series(self, db_session, sample_time_series):
        """Test saving a new time series to the database."""
        repo = TimeSeriesDBRepository(db_session)
        await repo.save(sample_time_series)
        await db_session.commit()

        # Verify metadata was saved
        metadata = await db_session.get(TimeSeriesMetadata, sample_time_series.id)
        assert metadata is not None
        assert metadata.id == sample_time_series.id
        assert metadata.time_column == sample_time_series.time_column
        assert metadata.value_columns == '["temperature", "humidity"]'

        # Verify data points were saved
        data_points = (await db_session.execute(
            TimeSeriesDataPoint.__table__.select().where(TimeSeriesDataPoint.time_series_id == sample_time_series.id)
        )).fetchall()
        assert len(data_points) == len(sample_time_series.data) * len(sample_time_series.value_columns)

    async def test_save_existing_time_series_updates_data(self, db_session, sample_time_series, sample_time_series_update):
        """Test updating an existing time series, ensuring data points are replaced."""
        repo = TimeSeriesDBRepository(db_session)

        # Save initial time series
        await repo.save(sample_time_series)
        await db_session.commit()

        # Update the time series with new data and columns
        sample_time_series_update.id = sample_time_series.id # Ensure same ID for update
        await repo.save(sample_time_series_update)
        await db_session.commit()

        # Verify metadata was updated
        metadata = await db_session.get(TimeSeriesMetadata, sample_time_series.id)
        assert metadata is not None
        assert metadata.value_columns == '["temperature", "pressure"]' # Updated value columns

        # Verify old data points are deleted and new ones are added
        data_points = (await db_session.execute(
            TimeSeriesDataPoint.__table__.select().where(TimeSeriesDataPoint.time_series_id == sample_time_series.id)
        )).fetchall()
        assert len(data_points) == len(sample_time_series_update.data) * len(sample_time_series_update.value_columns)

    async def test_find_by_id_success(self, db_session, sample_time_series):
        """Test finding a time series by ID."""
        repo = TimeSeriesDBRepository(db_session)
        await repo.save(sample_time_series)
        await db_session.commit()

        found_ts = await repo.find_by_id(sample_time_series.id)
        assert found_ts is not None
        assert found_ts.id == sample_time_series.id
        pd.testing.assert_frame_equal(found_ts.data, sample_time_series.data)

    async def test_find_by_id_not_found(self, db_session):
        """Test finding a non-existent time series by ID."""
        repo = TimeSeriesDBRepository(db_session)
        found_ts = await repo.find_by_id("non-existent-id")
        assert found_ts is None

    async def test_find_all(self, db_session, sample_time_series):
        """Test finding all time series."""
        repo = TimeSeriesDBRepository(db_session)
        await repo.save(sample_time_series)
        
        # Create another time series
        data2 = pd.DataFrame({
            'time': pd.to_datetime(['2024-01-01', '2024-01-02']),
            'value': [10, 20]
        })
        ts2 = TimeSeries.create(data=data2, time_column='time', value_columns=['value'])
        await repo.save(ts2)
        await db_session.commit()

        all_ts = await repo.find_all()
        assert len(all_ts) == 2
        assert any(ts.id == sample_time_series.id for ts in all_ts)
        assert any(ts.id == ts2.id for ts in all_ts)

    async def test_delete_time_series(self, db_session, sample_time_series):
        """Test deleting a time series."""
        repo = TimeSeriesDBRepository(db_session)
        await repo.save(sample_time_series)
        await db_session.commit()

        assert await repo.exists(sample_time_series.id)

        await repo.delete(sample_time_series.id)
        await db_session.commit()

        assert not await repo.exists(sample_time_series.id)
        
        # Verify data points are also deleted
        data_points = (await db_session.execute(
            TimeSeriesDataPoint.__table__.select().where(TimeSeriesDataPoint.time_series_id == sample_time_series.id)
        )).fetchall()
        assert len(data_points) == 0

    async def test_delete_non_existent_time_series(self, db_session):
        """Test deleting a non-existent time series."""
        repo = TimeSeriesDBRepository(db_session)
        # Should not raise an error
        await repo.delete("non-existent-id")
        # No change in DB state, no error

    async def test_exists(self, db_session, sample_time_series):
        """Test checking if a time series exists."""
        repo = TimeSeriesDBRepository(db_session)
        assert not await repo.exists(sample_time_series.id)

        await repo.save(sample_time_series)
        await db_session.commit()

        assert await repo.exists(sample_time_series.id)

    async def test_save_data_points_timestamp_conversion(self, db_session):
        """Test _save_data_points handles various timestamp formats."""
        repo = TimeSeriesDBRepository(db_session)

        # Test with Unix timestamp (numeric)
        data_unix = pd.DataFrame({
            'time': [1672531200, 1672534800], # Jan 1, 2023 00:00:00, 01:00:00 UTC
            'value': [10, 20]
        })
        ts_unix = TimeSeries.create(data=data_unix, time_column='time', value_columns=['value'])
        await repo.save(ts_unix)
        await db_session.commit()
        found_ts_unix = await repo.find_by_id(ts_unix.id)
        assert found_ts_unix.data['time'].iloc[0] == pd.to_datetime('2023-01-01 00:00:00', unit='s')

        # Test with numeric index (treated as offset from now)
        data_index = pd.DataFrame({
            'index_col': [0, 1, 2],
            'value': [100, 110, 120]
        })
        ts_index = TimeSeries.create(data=data_index, time_column='index_col', value_columns=['value'])
        await repo.save(ts_index)
        await db_session.commit()
        found_ts_index = await repo.find_by_id(ts_index.id)
        # Check that the timestamps are datetime objects and are increasing
        assert pd.api.types.is_datetime64_any_dtype(found_ts_index.data['index_col'])
        assert found_ts_index.data['index_col'].iloc[1] > found_ts_index.data['index_col'].iloc[0]

        # Test with string timestamp
        data_str = pd.DataFrame({
            'date_str': ['2023-01-01', '2023-01-02'],
            'value': [1, 2]
        })
        ts_str = TimeSeries.create(data=data_str, time_column='date_str', value_columns=['value'])
        await repo.save(ts_str)
        await db_session.commit()
        found_ts_str = await repo.find_by_id(ts_str.id)
        assert found_ts_str.data['date_str'].iloc[0] == pd.to_datetime('2023-01-01')

    async def test_convert_to_time_series_empty_data(self, db_session):
        """Test _convert_to_time_series with no data points."""
        repo = TimeSeriesDBRepository(db_session)
        
        # Manually create metadata without data points
        metadata = TimeSeriesMetadata(
            id="empty-id",
            time_column="timestamp",
            value_columns='["value1", "value2"]'
        )
        db_session.add(metadata)
        await db_session.commit()

        # Retrieve metadata and convert
        retrieved_metadata = await db_session.get(TimeSeriesMetadata, "empty-id")
        time_series = await repo._convert_to_time_series(retrieved_metadata)

        assert time_series.id == "empty-id"
        assert time_series.data.empty
        assert list(time_series.data.columns) == ["timestamp", "value1", "value2"]
        assert time_series.time_column == "timestamp"
        assert time_series.value_columns == ["value1", "value2"]

    async def test_convert_to_time_series_missing_value_columns(self, db_session):
        """Test _convert_to_time_series handles missing value columns in data points."""
        repo = TimeSeriesDBRepository(db_session)
        
        # Create metadata
        ts_id = "missing-cols-id"
        metadata = TimeSeriesMetadata(
            id=ts_id,
            time_column="timestamp",
            value_columns='["temp", "humidity"]'
        )
        db_session.add(metadata)
        await db_session.flush() # Flush to get metadata.id for data points

        # Add only 'temp' data points, 'humidity' will be missing
        data_point1 = TimeSeriesDataPoint(
            time_series_id=ts_id,
            timestamp=pd.to_datetime('2023-01-01'),
            column_name='temp',
            value=25.0
        )
        data_point2 = TimeSeriesDataPoint(
            time_series_id=ts_id,
            timestamp=pd.to_datetime('2023-01-01'),
            column_name='humidity',
            value=70.0
        )
        db_session.add_all([data_point1, data_point2])
        await db_session.commit()

        # Retrieve metadata with data points
        stmt = TimeSeriesMetadata.__table__.select().where(TimeSeriesMetadata.id == ts_id)
        result = await db_session.execute(stmt)
        retrieved_metadata = result.scalar_one_or_none()
        
        # Manually load data_points for the retrieved_metadata
        retrieved_metadata.data_points = (await db_session.execute(
            TimeSeriesDataPoint.__table__.select().where(TimeSeriesDataPoint.time_series_id == ts_id)
        )).scalars().all()

        time_series = await repo._convert_to_time_series(retrieved_metadata)

        assert time_series.id == ts_id
        assert not time_series.data.empty
        assert list(time_series.data.columns) == ["timestamp", "temp", "humidity"]
        assert time_series.data['temp'].iloc[0] == 25.0
        assert time_series.data['humidity'].iloc[0] == 70.0