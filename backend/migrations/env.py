from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.db.base import Base
from app.models import CandidateProfile  # noqa: F401


# Configuration Alembic provenant du fichier alembic.ini.
config = context.config

# Utilise l’adresse PostgreSQL définie dans la configuration de l’application.
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

# Configuration des logs Alembic.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Métadonnées utilisées pour générer automatiquement les migrations.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Exécute les migrations sans connexion directe à la base."""
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Exécute les migrations avec une connexion à la base."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()