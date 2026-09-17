from pathlib import Path

from flask_sqlalchemy import SQLAlchemy


# Keep the database file inside the project's database folder.
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_DIR = BASE_DIR / "database"
DATABASE_DIR.mkdir(exist_ok=True)

DATABASE_PATH = DATABASE_DIR / "parking.db"

db = SQLAlchemy()
