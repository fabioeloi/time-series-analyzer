import asyncio
import os
import pytest
from pathlib import Path

# Add the backend directory to the path to import modules
# This is necessary because conftest.py is in tests/backend,
# and we need to import from backend.infrastructure.database.config
import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "backend"))

# Now we can import from the backend
from infrastructure.database.config import init_db, close_db, DATABASE_URL, TEST_MODE


@pytest.fixture(scope="session")
def session_event_loop():
    """Create an instance of the default event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def db_setup_session(session_event_loop): # Depends on the session_event_loop
    """
    Set up the test database before any tests run and tear it down afterwards.
    This fixture is session-scoped and autouse=True, so it runs automatically
    once per test session.
    It is a synchronous fixture that runs async code on the session_event_loop.
    """
    is_test_mode = TEST_MODE
    db_url = DATABASE_URL

    if is_test_mode and db_url and "sqlite" in db_url.lower():
        backend_dir = Path(__file__).parent.parent.parent / "backend"
        db_file_path_str = db_url.split("///")[-1]

        db_file_to_manage = None
        if db_file_path_str and db_file_path_str != ":memory:":
            if not Path(db_file_path_str).is_absolute():
                 db_file_to_manage = backend_dir / db_file_path_str
            else:
                db_file_to_manage = Path(db_file_path_str)

            if db_file_to_manage.exists():
                # print(f"Removing existing test database: {db_file_to_manage}")
                db_file_to_manage.unlink()
        
        # print("Initializing test database schema...")
        session_event_loop.run_until_complete(init_db()) # Run async init_db
        # print("Test database schema initialized.")
        
        yield # Run tests
        
        # print("Closing test database connection...")
        session_event_loop.run_until_complete(close_db()) # Run async close_db
        # print("Test database connection closed.")
        
        if db_file_to_manage and db_file_to_manage.exists():
            # print(f"Removing test database file after tests: {db_file_to_manage}")
            db_file_to_manage.unlink()
    else:
        # print("Not in SQLite test mode, skipping automatic DB setup/teardown.")
        yield