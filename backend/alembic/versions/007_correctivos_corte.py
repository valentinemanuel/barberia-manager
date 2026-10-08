"""Movimientos correctivos: columnas aditivas en movimientos_corte.

Revision ID: 007_correctivos_corte
Revises: 006_revision_abono

Solo ADD COLUMN nullable (compatible SQLite sin batch). No toca datos.
Prohibido aplicar contra bases reales sin aprobación explícita + backup
verificado (gate vigente).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "007_correctivos_corte"
down_revision: Union[str, Sequence[str], None] = "006_revision_abono"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNAS = ("original_uuid", "motivo", "evidencia")


def upgrade() -> None:
    tablas = inspect(op.get_bind()).get_table_names()
    if "movimientos_corte" not in tablas:
        # Instalación nueva: create_all crea el schema desde metadata.
        print("INFO 007_correctivos_corte: sin tabla movimientos_corte, nada que migrar.")
        return
    existentes = [c["name"] for c in inspect(op.get_bind()).get_columns("movimientos_corte")]
    faltantes = [c for c in COLUMNAS if c not in existentes]
    if not faltantes:
        # Coexistencia con create_all (main.py): nada que agregar.
        print("INFO 007_correctivos_corte: columnas ya existentes, nada que crear.")
        return
    with op.batch_alter_table("movimientos_corte") as batch:
        if "original_uuid" in faltantes:
            batch.add_column(sa.Column("original_uuid", sa.String(length=36), nullable=True))
        if "motivo" in faltantes:
            batch.add_column(sa.Column("motivo", sa.String(length=255), nullable=True))
        if "evidencia" in faltantes:
            batch.add_column(sa.Column("evidencia", sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("movimientos_corte") as batch:
        batch.drop_column("evidencia")
        batch.drop_column("motivo")
        batch.drop_column("original_uuid")
