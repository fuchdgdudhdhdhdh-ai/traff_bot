# Единственный файл, который нужно заполнить вручную.
BOT_TOKEN = "PASTE_BOT_TOKEN_HERE"
ADMIN_IDS = [123456789]

# Оставьте None для Render: приложение попробует DATABASE_URL из окружения.
# Если хотите указать строку локально — вставьте её сюда.
DATABASE_URL = __import__("os").environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required. Add PostgreSQL connection string in Render.")
