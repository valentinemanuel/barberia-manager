"""Journal idempotente mínimo: crea solo operaciones_corte.

Revision ID: 002_operaciones_corte
Revises: 001_base_legacy

No toca tablas ni datos legacy. Prohibido aplicar contra bases reales sin
aprobación explícita + backup verificado (gate del paquete 5).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "002_operaciones_corte"
down_revision: Union[str, Sequence[str], None] = "001_base_legacy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "operaciones_corte" in inspect(op.get_bind()).get_table_names():
        # Coexistencia con create_all (main.py:22): la tabla ya existe
        # vacía; no se recrea ni se toca. Solo registra la versión.
        print("INFO 002_operaciones_corte: tabla ya existente, nada que crear.")
        return
    op.create_table(
        "operaciones_corte",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column("namespace_cliente", sa.String(length=32), nullable=False),
        sa.Column("operacion_id", sa.String(length=36), nullable=False),
        sa.Column("accion", sa.String(length=32), nullable=False),
        sa.Column("hash_operacion", sa.String(length=64), nullable=False),
        sa.Column("modo_captura", sa.Enum("online", "offline", name="modocaptura"), nullable=False),
        sa.Column("estado", sa.Enum("aceptada", "rechazada", name="estadooperacion"), nullable=False),
        sa.Column("resultado", sa.JSON(), nullable=False),
        sa.Column("recibida_en", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "actor_id", "namespace_cliente", "operacion_id", name="uq_operacion_clave"
        ),
    )
    op.create_index("ix_operaciones_corte_id", "operaciones_corte", ["id"])


def downgrade() -> None:
    op.drop_index("ix_operaciones_corte_id", table_name="operaciones_corte")
    op.drop_table("operaciones_corte")
