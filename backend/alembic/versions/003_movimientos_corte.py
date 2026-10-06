"""Movimientos de corte: crea solo movimientos_corte.

Revision ID: 003_movimientos_corte
Revises: 002_operaciones_corte

No toca tablas ni datos legacy. Prohibido aplicar contra bases reales sin
aprobación explícita + backup verificado (gate del paquete 6).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "003_movimientos_corte"
down_revision: Union[str, Sequence[str], None] = "002_operaciones_corte"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "movimientos_corte" in inspect(op.get_bind()).get_table_names():
        # Coexistencia con create_all (main.py:22): nada que crear.
        print("INFO 003_movimientos_corte: tabla ya existente, nada que crear.")
        return
    op.create_table(
        "movimientos_corte",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=36), nullable=False),
        sa.Column("corte_id", sa.Integer(), nullable=False),
        sa.Column(
            "concepto",
            sa.Enum("cliente", "comision", name="conceptomovimiento"),
            nullable=False,
        ),
        sa.Column("tipo", sa.Enum("abono", name="tipomovimiento"), nullable=False),
        sa.Column("importe", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("autor_id", sa.Integer(), nullable=False),
        sa.Column(
            "metodo_pago",
            sa.Enum(
                "efectivo", "tarjeta", "transferencia", name="metodopago"
            ),
            nullable=False,
        ),
        sa.Column("momento_real", sa.DateTime(), nullable=True),
        sa.Column("registrado_en", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["autor_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["corte_id"], ["cortes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("uuid", name="uq_movimiento_uuid"),
    )
    op.create_index("ix_movimientos_corte_id", "movimientos_corte", ["id"])


def downgrade() -> None:
    op.drop_index("ix_movimientos_corte_id", table_name="movimientos_corte")
    op.drop_table("movimientos_corte")
