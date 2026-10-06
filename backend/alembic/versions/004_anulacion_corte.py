"""Anulación terminal: agrega columnas nullable a cortes.

Revision ID: 004_anulacion_corte
Revises: 003_movimientos_corte

Solo ADD COLUMN nullable (compatible SQLite sin batch). No toca datos.
Prohibido aplicar contra bases reales sin aprobación explícita + backup
verificado (gate del paquete 7).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "004_anulacion_corte"
down_revision: Union[str, Sequence[str], None] = "003_movimientos_corte"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNAS = ("anulado_en", "anulado_motivo", "anulado_por")


def upgrade() -> None:
    tablas = inspect(op.get_bind()).get_table_names()
    if "cortes" not in tablas:
        # Instalación nueva: create_all crea el schema desde metadata.
        print("INFO 004_anulacion_corte: sin tabla cortes, nada que migrar.")
        return
    existentes = [c["name"] for c in inspect(op.get_bind()).get_columns("cortes")]
    faltantes = [c for c in COLUMNAS if c not in existentes]
    if not faltantes:
        # Coexistencia con create_all (main.py:22): nada que agregar.
        print("INFO 004_anulacion_corte: columnas ya existentes, nada que crear.")
        return
    # Batch: en SQLite recrea la tabla (ADD COLUMN nativo no admite FK
    # separada); en PostgreSQL emite ADDs directos. Nullable sin default.
    with op.batch_alter_table("cortes") as batch:
        if "anulado_en" in faltantes:
            batch.add_column(sa.Column("anulado_en", sa.DateTime(), nullable=True))
        if "anulado_motivo" in faltantes:
            batch.add_column(
                sa.Column("anulado_motivo", sa.String(length=255), nullable=True)
            )
        if "anulado_por" in faltantes:
            batch.add_column(sa.Column("anulado_por", sa.Integer(), nullable=True))
            batch.create_foreign_key(
                "fk_cortes_anulado_por", "usuarios", ["anulado_por"], ["id"]
            )


def downgrade() -> None:
    with op.batch_alter_table("cortes") as batch:
        batch.drop_constraint("fk_cortes_anulado_por", type_="foreignkey")
        batch.drop_column("anulado_por")
        batch.drop_column("anulado_motivo")
        batch.drop_column("anulado_en")
