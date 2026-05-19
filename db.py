from datetime import datetime
import os
from typing import Optional, List
from sqlmodel import Field, SQLModel, create_engine, Session
from main import VAULT_ROOT

sqlite_url = f"sqlite:///{os.path.join(VAULT_ROOT, 'vault_core.db')}"
engine = create_engine(sqlite_url, echo=True)


def init_db():
    SQLModel.metadata.create_all(engine)