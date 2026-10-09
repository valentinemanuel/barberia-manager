"""Jornadas de negocio: crea jornadas_caja y pertenencias_cierre.

Revision ID: 010_jornadas_caja
Revises: 009_intervenciones_corte

No toca tablas ni datos existentes (el cierre legacy queda intacto).
Prohibido aplicar contra bases reales sin aprobación explícita + backup
verificado (gate vigente).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "010_jornadas_caja"
down_revision: Union[str, Sequence[str], None] = "009_intervenciones_corte"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    tablas = inspect(op.get_bind()).get_table_names()
    if "jornadas_caja" not in tablas:
        op.create_table(
            "jornadas_caja",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("fecha_negocio", sa.Date(), nullable=False),
            sa.Column(
                "estado",
                sa.Enum("abierta", "cerrada", name="estadojornada"),
                nullable=False,
            ),
            sa.Column("abierta_por", sa.Integer(), nullable=False),
            sa.Column("abierta_en", sa.DateTime(), nullable=False),
            sa.Column("cerrada_por", sa.Integer(), nullable=True),
            sa.Column("cerrada_en", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["abierta_por"], ["usuarios.id"]),
            sa.ForeignKeyConstraint(["cerrada_por"], ["usuarios.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("fecha_negocio"),
        )
        op.create_index("ix_jornadas_caja_id", "jornadas_caja", ["id"])
    else:
        print("INFO 010_jornadas_caja: jornadas_caja ya existente, nada que crear.")
    if "pertenencias_cierre" not in tablas:
        op.create_table(
            "pertenencias_cierre",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("jornada_id", sa.Integer(), nullable=False),
            sa.Column("corte_id", sa.Integer(), nullable=False),
            sa.Column("servicio_id", sa.Integer(), nullable=False),
            sa.Column("precio", sa.Numeric(10, 2), nullable=False),
            sa.Column("porcentaje_barbero", sa.Numeric(5, 2), nullable=False),
            sa.Column("parte_barbero", sa.Numeric(10, 2), nullable=False),
            sa.Column("version_corte", sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(["corte_id"], ["cortes.id"]),
            sa.ForeignKeyConstraint(["jornada_id"], ["jornadas_caja.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("jornada_id", "corte_id", name="uq_pertenencia"),
        )
        op.create_index("ix_pertenencias_cierre_id", "pertenencias_cierre", ["id"])
    else:
        print("INFO 010_jornadas_caja: pertenencias_cierre ya existente, nada que crear.")


def downgrade() -> None:
    op.drop_index("ix_pertenencias_cierre_id", table_name="pertenencias_cierre")
    op.drop_table("pertenencias_cierre")
    op.drop_index("ix_jornadas_caja_id", table_name="jornadas_caja")
    op.drop_table("jornadas_caja")
