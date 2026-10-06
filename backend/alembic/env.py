"""Entorno de migraciones Alembic (spec 002, paquete 2).

Garantías de este esqueleto:
- Nunca importa ``app.main`` (que ejecuta ``create_all`` al importar).
- Importar ``app.database`` solo crea el engine perezoso, no conecta.
- La URL real jamás se versiona: ``alembic.ini`` trae un placeholder inerte y
  solo ``ALEMBIC_SQLALCHEMY_URL`` (copias temporales) puede sustituirla.
- Prohibido ejecutar ``upgrade`` contra ``barberia.db`` u otra base real.
"""
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

sqlalchemy_url = os.environ.get(
    "ALEMBIC_SQLALCHEMY_URL", config.get_main_option("sqlalchemy.url")
)
config.set_main_option("sqlalchemy.url", sqlalchemy_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=sqlalchemy_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
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
