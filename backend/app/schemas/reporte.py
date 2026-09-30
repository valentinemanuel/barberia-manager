from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel
from typing import List, Optional


class ReporteDia(BaseModel):
    fecha: date
    total_cortes: Decimal
    total_productos: Decimal
    total_consumibles: Decimal
    total_ingresos: Decimal
    total_gastos: Decimal
    ganancia_neta: Decimal
    cantidad_cortes: int


class ReporteBarbero(BaseModel):
    barbero_id: int
    nombre_barbero: str
    cantidad_cortes: int
    total_bruto: Decimal
    parte_barbero: Decimal
    parte_barberia: Decimal


class DashboardAdmin(BaseModel):
    ganancias_hoy: Decimal
    ganancias_semana: Decimal
    ganancias_mes: Decimal
    cortes_hoy: int
    cortes_semana: int
    cortes_mes: int
    top_barberos: List[ReporteBarbero]
    productos_mas_vendidos: List[dict]


class DashboardBarbero(BaseModel):
    cortes_hoy: int
    acumulado_hoy: Decimal
    cortes_semana: int
    acumulado_semana: Decimal
    cortes_mes: int
    acumulado_mes: Decimal
    porcentaje_asignado: Decimal
    historial_cortes: List[dict]
