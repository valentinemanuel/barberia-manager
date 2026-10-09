"""Imputación contable: crea solo imputaciones_movimiento.

Revision ID: 011_imputacion_corte
Revises: 010_jornadas_caja

No toca tablas ni datos existentes. Prohibido aplicar contra bases reales
sin aprobación explícita + backup verificado (gate vigente).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "011_imputacion_corte"
down_revision: Union[str, Sequence[str], None] = "010_jornadas_caja"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "imputaciones_movimiento" in inspect(op.get_bind()).get_table_names():
        print("INFO 011_imputacion_corte: tabla ya existente, nada que crear.")
        return
    op.create_table(
        "imputaciones_movimiento",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("movimiento_uuid", sa.String(length=36), nullable=False),
        sa.Column("jornada_real", sa.Date(), nullable=False),
        sa.Column("jornada_destino_id", sa.Integer(), nullable=True),
        sa.Column(
            "estado",
            sa.Enum("imputado", "pendiente", name="estadoimputacion"),
            nullable=False,
        ),
        sa.Column("creada_en", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["jornada_destino_id"], ["jornadas_caja.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("movimiento_uuid"),
    )
    op.create_index("ix_imputaciones_movimiento_id", "imputaciones_movimiento", ["id"])


def downgrade() -> None:
    op.drop_index("ix_imputaciones_movimiento_id", table_name="imputaciones_movimiento")
    op.drop_table("imputaciones_movimiento")
