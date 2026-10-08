"""Relojes LWW y titularidad: columnas aditivas + backfill conservador.

Revision ID: 008_lww_reasignacion
Revises: 007_correctivos_corte

Solo ADD COLUMN nullable (compatible SQLite sin batch) + UPDATE de
backfill que no pisa valores ya puestos (repetible). No toca datos
conocidos. Prohibido aplicar contra bases reales sin aprobación
explícita + backup verificado (gate vigente).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "008_lww_reasignacion"
down_revision: Union[str, Sequence[str], None] = "007_correctivos_corte"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CORTES = (
    "version",
    "unidad_metodo_ts",
    "unidad_momento_ts",
    "unidad_finanzas_ts",
    "deuda_conocida",
    "comision_conocida",
)
MOVIMIENTOS = ("profesional_id",)


def upgrade() -> None:
    tablas = inspect(op.get_bind()).get_table_names()
    if "cortes" in tablas:
        existentes = [c["name"] for c in inspect(op.get_bind()).get_columns("cortes")]
        faltantes = [c for c in CORTES if c not in existentes]
        if faltantes:
            with op.batch_alter_table("cortes") as batch:
                if "version" in faltantes:
                    batch.add_column(
                        sa.Column("version", sa.Integer(), nullable=True)
                    )
                for columna in (
                    "unidad_metodo_ts",
                    "unidad_momento_ts",
                    "unidad_finanzas_ts",
                ):
                    if columna in faltantes:
                        batch.add_column(sa.Column(columna, sa.DateTime(), nullable=True))
                for columna in ("deuda_conocida", "comision_conocida"):
                    if columna in faltantes:
                        batch.add_column(sa.Column(columna, sa.Boolean(), nullable=True))
            # Filas preexistentes: versión 1 donde no la puso la app.
            op.execute("UPDATE cortes SET version = 1 WHERE version IS NULL")
        else:
            print("INFO 008_lww_reasignacion: cortes ya migrada, nada que crear.")
    else:
        print("INFO 008_lww_reasignacion: sin tabla cortes, nada que migrar.")
    if "movimientos_corte" in tablas:
        existentes = [
            c["name"] for c in inspect(op.get_bind()).get_columns("movimientos_corte")
        ]
        faltantes = [c for c in MOVIMIENTOS if c not in existentes]
        if faltantes:
            with op.batch_alter_table("movimientos_corte") as batch:
                batch.add_column(sa.Column("profesional_id", sa.Integer(), nullable=True))
            # Backfill: la comisión pertenecía al titular vigente entonces.
            # Solo nulos (repetible; no pisa correcciones del admin).
            op.execute(
                "UPDATE movimientos_corte SET profesional_id = "
                "(SELECT barbero_id FROM cortes WHERE cortes.id = movimientos_corte.corte_id) "
                "WHERE concepto = 'comision' AND profesional_id IS NULL"
            )
        else:
            print("INFO 008_lww_reasignacion: movimientos ya migrada, nada que crear.")
    else:
        print("INFO 008_lww_reasignacion: sin tabla movimientos_corte, nada que migrar.")


def downgrade() -> None:
    with op.batch_alter_table("movimientos_corte") as batch:
        batch.drop_column("profesional_id")
    with op.batch_alter_table("cortes") as batch:
        batch.drop_column("comision_conocida")
        batch.drop_column("deuda_conocida")
        batch.drop_column("unidad_finanzas_ts")
        batch.drop_column("unidad_momento_ts")
        batch.drop_column("unidad_metodo_ts")
        batch.drop_column("version")
