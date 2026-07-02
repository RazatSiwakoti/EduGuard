"""
Alembic environment configuration.

IMPORTANT: DATABASE_URL is passed directly to create_engine() here,
NOT via config.set_main_option("sqlalchemy.url", ...). Routing it through
config.set_main_option() writes the URL into a configparser-backed config
object, which treats '%' as special interpolation syntax — so any password
containing '%' (e.g. from URL-encoded special characters like '@' -> '%40')
crashes with "invalid interpolation syntax". Setting the URL directly on
the engine avoids configparser entirely, so this is safe regardless of
what characters end up in the password (Python Software Foundation, 2025).
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import settings
from app.models.base import Base
import app.models  # noqa: F401  (registers all models on Base.metadata — required, do not remove)

config = context.config

# NOTE: we deliberately do NOT call config.set_main_option("sqlalchemy.url", ...)
# here — see module docstring above for why.

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Generate SQL scripts without a live DB connection."""
    context.configure(
        url=settings.DATABASE_URL,   # read straight from Pydantic settings, never through configparser
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect to PostgreSQL directly and apply migrations."""
    # Build engine config from alembic.ini's [alembic] section, but override
    # the URL with the real one afterward — never passed through set_main_option.
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.DATABASE_URL

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()