import asyncio
from sqlalchemy import text
from sqlmodel import create_engine
from src.core.config import settings

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))

with engine.connect() as conn:
    result = conn.execute(text("SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_transactions_reference'"))
    row = result.fetchone()
    if row:
        print("Index exists:", row[0])
    else:
        print("Index does not exist.")
