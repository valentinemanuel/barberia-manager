"""Revisión de abonos offline: columnas aditivas en movimientos_corte.

Revision ID: 006_revision_abono
Revises: 005_auditoria_corte

Solo ADD COLUMN nullable (compatible SQLite sin batch). No toca datos.
Prohibido aplicar contra bases reales sin aprobación explícita + backup
verificado (gate vigente).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "006_revision_abono"
down_revision: Union[str, Sequence[str], None] = "005_auditoria_corte"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

COLUMNAS = ("estado", "motivo_revision")


def upgrade() -> None:
    tablas = inspect(op.get_bind()).get_table_names()
    if "movimientos_corte" not in tablas:
        # Instalación nueva: create_all crea el schema desde metadata.
        print("INFO 006_revision_abono: sin tabla movimientos_corte, nada que migrar.")
        return
    existentes = [c["name"] for c in inspect(op.get_bind()).get_columns("movimientos_corte")]
    faltantes = [c for c in COLUMNAS if c not in existentes]
    if not faltantes:
        # Coexistencia con create_all (main.py): nada que agregar.
        print("INFO 006_revision_abono: columnas ya existentes, nada que crear.")
        return
    with op.batch_alter_table("movimientos_corte") as batch:
        if "estado" in faltantes:
            batch.add_column(sa.Column("estado", sa.String(length=9), nullable=True))
        if "motivo_revision" in faltantes:
            batch.add_column(sa.Column("motivo_revision", sa.String(length=64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("movimientos_corte") as batch:
        batch.drop_column("motivo_revision")
        batch.drop_column("estado")
