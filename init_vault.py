import os

from main import VAULT_ROOT


def init_vault():
    # 画像、记忆审核和关系图谱均由 vault_core.db 承载。
    directories = [
        os.path.join(VAULT_ROOT, "knowledge", "inbox"),
        os.path.join(VAULT_ROOT, "knowledge", "archives"),
        os.path.join(VAULT_ROOT, "cache"),
        os.path.join(VAULT_ROOT, "plugins"),
        os.path.join(VAULT_ROOT, "tools"),
    ]

    for folder in directories:
        os.makedirs(folder, exist_ok=True)
        print(f"✅ 已就绪: {folder}")

    from db import init_db

    init_db()
    print("✅ SQLite 画像/关系图谱表已就绪")


if __name__ == "__main__":
    init_vault()
