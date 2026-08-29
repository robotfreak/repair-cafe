import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
import app.db as db

@pytest.fixture
def tmp_db(tmp_path):
    p = tmp_path / "test.db"
    return db.init_db(str(p))

@pytest.fixture
def app_client(tmp_path):
    from app import create_app
    application = create_app(data_dir=str(tmp_path))
    application.config["TESTING"] = True
    with application.test_client() as c:
        yield c