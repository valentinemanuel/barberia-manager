"""Journal de auditoría de cortes: crea solo auditoria_corte.

Revision ID: 005_auditoria_corte
Revises: 004_anulacion_corte

No toca tablas ni datos legacy. Prohibido aplicar contra bases reales sin
aprobación explícita + backup verificado (gate vigente).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "005_auditoria_corte"
down_revision: Union[str, Sequence[str], None] = "004_anulacion_corte"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "auditoria_corte" in inspect(op.get_bind()).get_table_names():
        # Coexistencia con create_all (main.py:22): nada que crear.
        print("INFO 005_auditoria_corte: tabla ya existente, nada que crear.")
        return
    op.create_table(
        "auditoria_corte",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("corte_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), nullable=False),
        sa.Column(
            "accion",
            sa.Enum("edicion", "anulacion", name="accionauditoriacorte"),
            nullable=False,
        ),
        sa.Column("antes", sa.JSON(), nullable=False),
        sa.Column("despues", sa.JSON(), nullable=False),
        sa.Column("motivo", sa.String(length=255), nullable=True),
        sa.Column("momento_utc", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["corte_id"], ["cortes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auditoria_corte_id", "auditoria_corte", ["id"])


def downgrade() -> None:
    op.drop_index("ix_auditoria_corte_id", table_name="auditoria_corte")
    op.drop_table("auditoria_corte")
