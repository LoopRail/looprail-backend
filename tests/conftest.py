import os

os.environ["TESTING"] = "true"
from fastapi.testclient import TestClient

from src.main import app


client = TestClient(app)
