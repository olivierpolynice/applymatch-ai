from sqlalchemy import text

from app.db.session import DATABASE_URL, engine


def safe_database_name() -> str:
    return DATABASE_URL.rsplit("/", maxsplit=1)[-1]


with engine.connect() as connection:
    connection.execute(text("SELECT 1"))

print(
    "Connexion PostgreSQL réussie : "
    f"{safe_database_name()}"
)

