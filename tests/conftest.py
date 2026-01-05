import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from src.infrastructure.db import get_session
from src.main import app

pytest_plugins = [
    "tests.fixtures.usecases",
    "tests.fixtures.dependencies",
]

os.environ["TESTING"] = "true"

# Use an in-memory SQLite database for testing
engine = create_engine("sqlite:///./test.db")


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


@pytest.fixture(name="db_session")
def db_session_fixture() -> Generator[Session, None, None]:
    create_db_and_tables()
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)  # Clean up after tests


@pytest.fixture(name="client")
def client_fixture(db_session: Session) -> Generator[TestClient, None, None]:
    def get_session_override():
        return db_session

    app.dependency_overrides[get_session] = get_session_override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
