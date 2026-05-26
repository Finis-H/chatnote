from datetime import datetime
import os
from typing import Optional, List
from sqlmodel import Field, SQLModel, create_engine, Session
from main import VAULT_ROOT
import memory_system  # noqa: F401 - registers Vault OS memory tables with SQLModel

sqlite_url = f"sqlite:///{os.path.join(VAULT_ROOT, 'vault_core.db')}"
engine = create_engine(sqlite_url, echo=True)


def init_db():
    SQLModel.metadata.create_all(engine)
    memory_system.MemoryRepository(VAULT_ROOT)
