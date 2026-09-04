import os

# Все секреты берутся из переменных окружения (задайте их в настройках Render),
# а не хранятся в коде — так они не попадают в публичный репозиторий на GitHub.

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is required. Add it as an environment variable (e.g. in Render).")

_raw_admin_ids = os.environ.get("SUPERADMIN_IDS", "")
ADMIN_IDS = [int(x) for x in _raw_admin_ids.replace(",", " ").split() if x.strip()]
if not ADMIN_IDS:
    raise RuntimeError("SUPERADMIN_IDS is required (comma or space separated Telegram IDs).")

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required. Add PostgreSQL connection string in Render.")
