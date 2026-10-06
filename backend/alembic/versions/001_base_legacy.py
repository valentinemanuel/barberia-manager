"""Baseline legacy: solo inspecciona, nunca crea ni modifica.

Revision ID: 001_base_legacy
Revises: None (primera revision).

Comportamiento:
- Base vacía: informa y termina (instalación nueva usará migraciones).
- Tablas legacy presentes: verifica que el conjunto esperado esté completo;
  ante una instalación parcial (algunas sí, otras no) se detiene con error,
  sin escribir nada.
- Jamás emite DDL ni toca datos. Prohibido aplicarla contra bases reales;
  solo copias temporales con ALEMBIC_SQLALCHEMY_URL.
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect

revision: str = "001_base_legacy"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLAS_LEGACY_ESPERADAS = frozenset(
    {
        "usuarios",
        "servicios",
        "cortes",
        "productos",
        "consumibles",
        "ventas",
        "gastos",
        "cierres_caja",
        "auditorias",
    }
)


def upgrade() -> None:
    existentes = set(inspect(op.get_bind()).get_table_names())
    legacy_presentes = existentes & TABLAS_LEGACY_ESPERADAS
    if not legacy_presentes:
        print("INFO 001_base_legacy: base vacía, nada que inspeccionar.")
        return
    faltantes = TABLAS_LEGACY_ESPERADAS - existentes
    if faltantes:
        raise RuntimeError(
            "001_base_legacy: instalación parcial, faltan tablas legacy "
            f"{sorted(faltantes)}; detenerse y diagnosticar, no migrar."
        )
    print(f"INFO 001_base_legacy: schema legacy completo ({len(legacy_presentes)} tablas).")


def downgrade() -> None:
    # La baseline no escribió nada: no hay nada que revertir.
    pass
