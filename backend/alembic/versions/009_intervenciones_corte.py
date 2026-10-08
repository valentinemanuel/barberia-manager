"""Intervenciones RF-40: crea solo intervenciones_corte.

Revision ID: 009_intervenciones_corte
Revises: 008_lww_reasignacion

No toca tablas ni datos existentes. Prohibido aplicar contra bases reales
sin aprobación explícita + backup verificado (gate vigente).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "009_intervenciones_corte"
down_revision: Union[str, Sequence[str], None] = "008_lww_reasignacion"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "intervenciones_corte" in inspect(op.get_bind()).get_table_names():
        # Coexistencia con create_all (main.py): nada que crear.
        print("INFO 009_intervenciones_corte: tabla ya existente, nada que crear.")
        return
    op.create_table(
        "intervenciones_corte",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("corte_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("accion", sa.String(length=16), nullable=False),
        sa.Column("cambios", sa.JSON(), nullable=False),
        sa.Column("causa", sa.String(length=64), nullable=False),
        sa.Column(
            "estado",
            sa.Enum("pendiente", "aplicada", "descartada", name="estadointervencion"),
            nullable=False,
        ),
        sa.Column("motivo_resolucion", sa.String(length=255), nullable=True),
        sa.Column("creada_en", sa.DateTime(), nullable=False),
        sa.Column("resuelta_en", sa.DateTime(), nullable=True),
        sa.Column("resuelta_por", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["actor_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["corte_id"], ["cortes.id"]),
        sa.ForeignKeyConstraint(["resuelta_por"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid"),
    )
    op.create_index("ix_intervenciones_corte_id", "intervenciones_corte", ["id"])


def downgrade() -> None:
    op.drop_index("ix_intervenciones_corte_id", table_name="intervenciones_corte")
    op.drop_table("intervenciones_corte")
