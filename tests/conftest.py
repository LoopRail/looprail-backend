import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from src.main import app

os.environ["TESTING"] = "true"


@pytest.fixture(name="client")
def client_fixture() -> Generator[TestClient, None, None]:
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
