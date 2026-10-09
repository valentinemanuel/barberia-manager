"""Ajustes de cierre y tardíos: crea ajustes_cierre + es_tardio.

Revision ID: 012_ajustes_cierre
Revises: 011_imputacion_corte

Aditivo con guard (patrón 010/011). No toca datos ni cierres legacy.
Prohibido aplicar contra bases reales sin aprobación explícita + backup
verificado (gate vigente).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "012_ajustes_cierre"
down_revision: Union[str, Sequence[str], None] = "011_imputacion_corte"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    tablas = inspect(op.get_bind()).get_table_names()
    if "ajustes_cierre" not in tablas:
        op.create_table(
            "ajustes_cierre",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column(
                "tipo",
                sa.Enum("tardio", "correccion", name="tipoajuste"),
                nullable=False,
            ),
            sa.Column("corte_id", sa.Integer(), nullable=True),
            sa.Column("movimiento_uuid", sa.String(length=36), nullable=True),
            sa.Column("jornada_origen_id", sa.Integer(), nullable=True),
            sa.Column("jornada_destino_id", sa.Integer(), nullable=True),
            sa.Column("detalle", sa.JSON(), nullable=False),
            sa.Column("autor_id", sa.Integer(), nullable=False),
            sa.Column("motivo", sa.String(length=255), nullable=False),
            sa.Column("creado_en", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["autor_id"], ["usuarios.id"]),
            sa.ForeignKeyConstraint(["corte_id"], ["cortes.id"]),
            sa.ForeignKeyConstraint(["jornada_destino_id"], ["jornadas_caja.id"]),
            sa.ForeignKeyConstraint(["jornada_origen_id"], ["jornadas_caja.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_ajustes_cierre_id", "ajustes_cierre", ["id"])
    else:
        print("INFO 012_ajustes_cierre: ajustes_cierre ya existente, nada que crear.")
    if "pertenencias_cierre" in tablas:
        existentes = [
            c["name"] for c in inspect(op.get_bind()).get_columns("pertenencias_cierre")
        ]
        if "es_tardio" not in existentes:
            with op.batch_alter_table("pertenencias_cierre") as batch:
                batch.add_column(sa.Column("es_tardio", sa.Boolean(), nullable=True))
        else:
            print("INFO 012_ajustes_cierre: es_tardio ya existente, nada que agregar.")
    else:
        print("INFO 012_ajustes_cierre: sin tabla pertenencias_cierre, nada que agregar.")


def downgrade() -> None:
    with op.batch_alter_table("pertenencias_cierre") as batch:
        batch.drop_column("es_tardio")
    op.drop_index("ix_ajustes_cierre_id", table_name="ajustes_cierre")
    op.drop_table("ajustes_cierre")
