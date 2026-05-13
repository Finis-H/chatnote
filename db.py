from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, create_engine, Session


sqlite_url = "sqlite:///vault/vault_core.db"
engine = create_engine(sqlite_url, echo=True)


def init_db():
    SQLModel.metadata.create_all(engine)