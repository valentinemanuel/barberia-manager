"""Validaciones monetarias puras para cortes, sin efectos externos."""

from decimal import (
    Clamped,
    Context,
    Decimal,
    DecimalException,
    DivisionByZero,
    Inexact,
    InvalidOperation,
    MAX_EMAX,
    MAX_PREC,
    MIN_EMIN,
    Overflow,
    ROUND_HALF_UP,
    Rounded,
    Underflow,
    localcontext,
)


def validar_porcentaje(valor: Decimal) -> Decimal:
    """Valida tipo, finitud, escala y rango sin alterar el Decimal recibido."""
    if not isinstance(valor, Decimal):
        raise TypeError("El porcentaje debe ser Decimal")
    if not valor.is_finite():
        raise ValueError("El porcentaje debe ser finito")
    if valor.as_tuple().exponent < -2:
        raise ValueError("El porcentaje debe tener como máximo dos decimales")
    if valor < Decimal("0") or valor > Decimal("100"):
        raise ValueError("El porcentaje debe estar entre 0 y 100")
    return valor


def validar_importe_abono(importe: Decimal) -> Decimal:
    """Valida un abono positivo y exacto sin convertirlo ni consultar saldos."""
    if not isinstance(importe, Decimal):
        raise TypeError("El importe del abono debe ser Decimal")
    if not importe.is_finite():
        raise ValueError("El importe del abono debe ser finito")
    if importe.as_tuple().exponent < -2:
        raise ValueError("El importe del abono debe tener como máximo dos decimales")
    if importe <= Decimal("0"):
        raise ValueError("El importe del abono debe ser positivo")
    return importe


def calcular_partes(
    precio: Decimal, porcentaje_barbero: Decimal
) -> tuple[Decimal, Decimal]:
    """Reparte solo el precio del servicio: comisión redondeada y resto exacto."""
    if not isinstance(precio, Decimal):
        raise TypeError("El precio del servicio debe ser Decimal")
    if not precio.is_finite():
        raise ValueError("El precio del servicio debe ser finito")
    if precio.as_tuple().exponent < -2:
        raise ValueError("El precio del servicio debe tener como máximo dos decimales")
    if precio < Decimal("0"):
        raise ValueError("El precio del servicio no puede ser negativo")
    validar_porcentaje(porcentaje_barbero)

    # El cero no necesita expandir su exponente; las entradas siguen intactas.
    precio_trabajo = Decimal("0") if precio.is_zero() else precio
    porcentaje_trabajo = (
        Decimal("0") if porcentaje_barbero.is_zero() else porcentaje_barbero
    )
    datos_precio = precio_trabajo.as_tuple()
    datos_porcentaje = porcentaje_trabajo.as_tuple()
    # El producto requiere como máximo la suma de dígitos de sus coeficientes.
    # Dividir por 100 es exacto. Como 0 <= porcentaje <= 100, ambas partes
    # al centavo caben en los dígitos del precio expandido a escala -2.
    precision = max(
        len(datos_precio.digits) + len(datos_porcentaje.digits),
        len(datos_precio.digits) + max(0, datos_precio.exponent + 2),
    )
    if precision > MAX_PREC:
        raise ValueError("No se puede representar el reparto con exactitud")

    contexto_trabajo = Context(
        prec=precision,
        rounding=ROUND_HALF_UP,
        Emin=MIN_EMIN,
        Emax=MAX_EMAX,
        capitals=1,
        clamp=0,
        flags=[],
        traps=[
            InvalidOperation, DivisionByZero, Overflow, Underflow, Clamped,
            Inexact, Rounded,
        ],
    )
    try:
        with localcontext(contexto_trabajo) as contexto:
            centavo = Decimal("0.01")
            comision_exacta = precio_trabajo * porcentaje_trabajo / Decimal("100")
            # Solo la comisión puede perder fracciones de centavo, explícitamente.
            contexto.traps[Inexact] = False
            contexto.traps[Rounded] = False
            parte_barbero = comision_exacta.quantize(centavo, rounding=ROUND_HALF_UP)
            contexto.traps[Inexact] = True
            contexto.traps[Rounded] = True
            parte_barberia = (precio_trabajo - parte_barbero).quantize(centavo)
            return parte_barbero, parte_barberia
    except DecimalException as error:
        raise ValueError("No se puede representar el reparto con exactitud") from error
