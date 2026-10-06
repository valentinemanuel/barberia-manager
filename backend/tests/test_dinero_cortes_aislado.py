"""Pruebas monetarias puras, sin importar la aplicación ni sus bases."""

from decimal import (
    Context,
    Decimal,
    Inexact,
    MAX_EMAX,
    Overflow,
    ROUND_DOWN,
    ROUND_HALF_EVEN,
    Rounded,
    getcontext,
    localcontext,
)

import pytest

from app.services.dinero_cortes import (
    calcular_partes,
    validar_importe_abono,
    validar_porcentaje,
)


@pytest.mark.parametrize(
    "texto",
    ["0", "0.00", "100", "100.00", "50.25", "50.20", "1E+2", "-0.00", "1E-2"],
)
def test_porcentaje_valido_conserva_identidad_y_representacion(texto: str) -> None:
    valor = Decimal(texto)
    representacion_original = valor.as_tuple()

    resultado = validar_porcentaje(valor)

    assert resultado is valor
    assert resultado.as_tuple() == representacion_original


@pytest.mark.parametrize("texto", ["NaN", "-NaN", "sNaN", "-sNaN", "Infinity", "-Infinity"])
def test_porcentaje_no_finito_se_rechaza_antes_de_precision_y_rango(texto: str) -> None:
    with pytest.raises(ValueError) as error:
        validar_porcentaje(Decimal(texto))

    assert str(error.value) == "El porcentaje debe ser finito"


@pytest.mark.parametrize("texto", ["50.000", "50.251", "0.000", "-0.001", "-1.000", "101.000"])
def test_porcentaje_precision_excesiva_se_rechaza_antes_de_rango(texto: str) -> None:
    valor = Decimal(texto)
    representacion_original = valor.as_tuple()

    with pytest.raises(ValueError) as error:
        validar_porcentaje(valor)

    assert str(error.value) == "El porcentaje debe tener como máximo dos decimales"
    assert valor.as_tuple() == representacion_original


@pytest.mark.parametrize("texto", ["-0.01", "-1", "100.01", "101"])
def test_porcentaje_fuera_de_rango_se_rechaza(texto: str) -> None:
    with pytest.raises(ValueError) as error:
        validar_porcentaje(Decimal(texto))

    assert str(error.value) == "El porcentaje debe estar entre 0 y 100"


@pytest.mark.parametrize("valor", ["50.25", "NaN", 50, True, False, 50.25, None, []])
def test_porcentaje_no_decimal_se_rechaza_sin_conversion(valor: object) -> None:
    with pytest.raises(TypeError) as error:
        validar_porcentaje(valor)

    assert str(error.value) == "El porcentaje debe ser Decimal"


@pytest.mark.parametrize(
    "texto", ["0.01", "1", "1.0", "1.00", "50.25", "1E+2", "1000000000000.01"]
)
def test_abono_valido_conserva_identidad_y_representacion(texto: str) -> None:
    importe = Decimal(texto)
    representacion_original = importe.as_tuple()

    resultado = validar_importe_abono(importe)

    assert resultado is importe
    assert resultado.as_tuple() == representacion_original


@pytest.mark.parametrize("texto", ["NaN", "-NaN", "sNaN", "-sNaN", "Infinity", "-Infinity"])
def test_abono_no_finito_se_rechaza_antes_de_precision_y_positividad(texto: str) -> None:
    with pytest.raises(ValueError) as error:
        validar_importe_abono(Decimal(texto))

    assert str(error.value) == "El importe del abono debe ser finito"


@pytest.mark.parametrize("texto", ["50.000", "1.001", "0.000", "-0.000", "-0.001", "-1.000"])
def test_abono_precision_excesiva_se_rechaza_antes_de_positividad(texto: str) -> None:
    importe = Decimal(texto)
    representacion_original = importe.as_tuple()

    with pytest.raises(ValueError) as error:
        validar_importe_abono(importe)

    assert str(error.value) == "El importe del abono debe tener como máximo dos decimales"
    assert importe.as_tuple() == representacion_original


@pytest.mark.parametrize("texto", ["0", "0.00", "-0", "-0.00", "0E+2", "-0E+2", "-0.01", "-1"])
def test_abono_cero_o_negativo_se_rechaza(texto: str) -> None:
    with pytest.raises(ValueError) as error:
        validar_importe_abono(Decimal(texto))

    assert str(error.value) == "El importe del abono debe ser positivo"


@pytest.mark.parametrize("importe", ["50.25", "NaN", 50, True, False, 50.25, None, []])
def test_abono_no_decimal_se_rechaza_sin_conversion(importe: object) -> None:
    with pytest.raises(TypeError) as error:
        validar_importe_abono(importe)

    assert str(error.value) == "El importe del abono debe ser Decimal"


@pytest.mark.parametrize(
    ("texto", "error_esperado"),
    [
        ("0.01", None),
        ("1000000000000.01", None),
        ("sNaN", ValueError),
        ("Infinity", ValueError),
        ("50.000", ValueError),
        ("-1", ValueError),
        ("-0.00", ValueError),
    ],
)
def test_validar_abono_no_altera_contexto_decimal(
    texto: str, error_esperado: type[Exception] | None
) -> None:
    importe = Decimal(texto)
    with localcontext() as contexto:
        contexto.prec = 2
        contexto.traps[Inexact] = True
        contexto.traps[Rounded] = True
        contexto.flags[Rounded] = True
        estado_original = repr(contexto)

        if error_esperado is None:
            assert validar_importe_abono(importe) is importe
        else:
            with pytest.raises(error_esperado):
                validar_importe_abono(importe)

        assert repr(contexto) == estado_original


@pytest.mark.parametrize(
    ("texto_precio", "texto_porcentaje", "barbero_esperado", "barberia_esperada"),
    [
        ("100", "50", "50.00", "50.00"),
        ("100", "0", "0.00", "100.00"),
        ("100", "100", "100.00", "0.00"),
        ("100", "-0.00", "0.00", "100.00"),
        ("0", "50", "0.00", "0.00"),
        ("0.00", "50", "0.00", "0.00"),
        ("-0.00", "50", "0.00", "0.00"),
        ("1E+2", "50", "50.00", "50.00"),
        ("100", "1E+2", "100.00", "0.00"),
    ],
)
def test_reparto_nominal_es_decimal_al_centavo_y_conserva_entradas(
    texto_precio: str,
    texto_porcentaje: str,
    barbero_esperado: str,
    barberia_esperada: str,
) -> None:
    precio = Decimal(texto_precio)
    porcentaje = Decimal(texto_porcentaje)
    entradas_originales = (precio.as_tuple(), porcentaje.as_tuple())

    resultado = calcular_partes(precio, porcentaje)

    assert isinstance(resultado, tuple)
    assert len(resultado) == 2
    parte_barbero, parte_barberia = resultado
    assert isinstance(parte_barbero, Decimal)
    assert isinstance(parte_barberia, Decimal)
    assert parte_barbero == Decimal(barbero_esperado)
    assert parte_barberia == Decimal(barberia_esperada)
    assert parte_barbero.as_tuple().exponent == -2
    assert parte_barberia.as_tuple().exponent == -2
    assert parte_barbero + parte_barberia == precio
    assert (precio.as_tuple(), porcentaje.as_tuple()) == entradas_originales


@pytest.mark.parametrize("precio", ["100", "NaN", 100, True, False, 100.0, None, []])
def test_reparto_precio_no_decimal_se_rechaza_sin_conversion(precio: object) -> None:
    with pytest.raises(TypeError) as error:
        calcular_partes(precio, Decimal("50"))

    assert str(error.value) == "El precio del servicio debe ser Decimal"


@pytest.mark.parametrize("texto", ["NaN", "-NaN", "sNaN", "-sNaN", "Infinity", "-Infinity"])
def test_reparto_precio_no_finito_se_rechaza_antes_de_precision_y_rango(texto: str) -> None:
    with pytest.raises(ValueError) as error:
        calcular_partes(Decimal(texto), Decimal("50"))

    assert str(error.value) == "El precio del servicio debe ser finito"


@pytest.mark.parametrize("texto", ["100.000", "1.001", "0.000", "-0.000", "-0.001", "-1.000"])
def test_reparto_precio_precision_excesiva_se_rechaza_antes_de_rango(texto: str) -> None:
    precio = Decimal(texto)
    representacion_original = precio.as_tuple()

    with pytest.raises(ValueError) as error:
        calcular_partes(precio, Decimal("50"))

    assert str(error.value) == "El precio del servicio debe tener como máximo dos decimales"
    assert precio.as_tuple() == representacion_original


@pytest.mark.parametrize("texto", ["-0.01", "-1", "-100.00"])
def test_reparto_precio_negativo_se_rechaza(texto: str) -> None:
    with pytest.raises(ValueError) as error:
        calcular_partes(Decimal(texto), Decimal("50"))

    assert str(error.value) == "El precio del servicio no puede ser negativo"


@pytest.mark.parametrize(
    ("texto", "mensaje"),
    [
        ("NaN", "El porcentaje debe ser finito"),
        ("sNaN", "El porcentaje debe ser finito"),
        ("Infinity", "El porcentaje debe ser finito"),
        ("50.000", "El porcentaje debe tener como máximo dos decimales"),
        ("-0.01", "El porcentaje debe estar entre 0 y 100"),
        ("100.01", "El porcentaje debe estar entre 0 y 100"),
    ],
)
def test_reparto_reutiliza_validacion_de_porcentaje(texto: str, mensaje: str) -> None:
    with pytest.raises(ValueError) as error:
        calcular_partes(Decimal("100"), Decimal(texto))

    assert str(error.value) == mensaje


@pytest.mark.parametrize("porcentaje", ["50", 50, True, 50.0])
def test_reparto_porcentaje_no_decimal_se_rechaza(porcentaje: object) -> None:
    with pytest.raises(TypeError) as error:
        calcular_partes(Decimal("100"), porcentaje)

    assert str(error.value) == "El porcentaje debe ser Decimal"


@pytest.mark.parametrize("redondeo_llamador", [ROUND_DOWN, ROUND_HALF_EVEN])
@pytest.mark.parametrize(
    ("texto_precio", "texto_porcentaje", "barbero_esperado", "barberia_esperada"),
    [
        ("0.08", "30", "0.02", "0.06"),
        ("0.05", "50", "0.03", "0.02"),
        ("1.01", "50", "0.51", "0.50"),
        ("0.03", "50", "0.02", "0.01"),
    ],
)
def test_reparto_redondea_comision_matematicamente_y_conserva_resto_exacto(
    texto_precio: str,
    texto_porcentaje: str,
    barbero_esperado: str,
    barberia_esperada: str,
    redondeo_llamador: str,
) -> None:
    precio = Decimal(texto_precio)
    porcentaje = Decimal(texto_porcentaje)
    with localcontext() as contexto:
        contexto.rounding = redondeo_llamador

        parte_barbero, parte_barberia = calcular_partes(precio, porcentaje)

        assert isinstance(parte_barbero, Decimal)
        assert isinstance(parte_barberia, Decimal)
        assert parte_barbero == Decimal(barbero_esperado)
        assert parte_barberia == Decimal(barberia_esperada)
        assert parte_barbero.as_tuple().exponent == -2
        assert parte_barberia.as_tuple().exponent == -2
        assert parte_barberia == precio - parte_barbero
        assert parte_barbero + parte_barberia == precio
        assert contexto.rounding == redondeo_llamador


def _contexto_hostil(redondeo: str) -> Context:
    return Context(
        prec=2,
        rounding=redondeo,
        Emin=-2,
        Emax=2,
        capitals=0,
        clamp=1,
        flags=[Inexact, Rounded, Overflow],
        traps=[Inexact, Rounded, Overflow],
    )


def _estado_contexto(contexto: Context) -> tuple[object, ...]:
    return (
        contexto.prec,
        contexto.rounding,
        contexto.Emin,
        contexto.Emax,
        contexto.capitals,
        contexto.clamp,
        dict(contexto.traps),
        dict(contexto.flags),
    )


@pytest.mark.parametrize("redondeo", [ROUND_DOWN, ROUND_HALF_EVEN])
@pytest.mark.parametrize(
    ("texto_precio", "texto_porcentaje", "barbero_esperado", "barberia_esperada"),
    [
        ("100", "50", "50.00", "50.00"),
        ("0.08", "30", "0.02", "0.06"),
        ("0.05", "50", "0.03", "0.02"),
        ("1.01", "50", "0.51", "0.50"),
        ("0.03", "50", "0.02", "0.01"),
        ("1000000000000.01", "50", "500000000000.01", "500000000000.00"),
        ("100", "50.25", "50.25", "49.75"),
        ("1E+12", "33.33", "333300000000.00", "666700000000.00"),
    ],
)
def test_reparto_exacto_independiente_de_contexto_hostil(
    texto_precio: str,
    texto_porcentaje: str,
    barbero_esperado: str,
    barberia_esperada: str,
    redondeo: str,
) -> None:
    precio = Decimal(texto_precio)
    porcentaje = Decimal(texto_porcentaje)
    entradas_originales = (precio.as_tuple(), porcentaje.as_tuple())
    with localcontext(_contexto_hostil(redondeo)) as llamador:
        estado_original = _estado_contexto(llamador)
        try:
            resultado = calcular_partes(precio, porcentaje)
            assert resultado == (Decimal(barbero_esperado), Decimal(barberia_esperada))
            assert isinstance(resultado, tuple)
            assert all(isinstance(parte, Decimal) for parte in resultado)
            assert all(parte.as_tuple().exponent == -2 for parte in resultado)
        finally:
            assert getcontext() is llamador
            assert _estado_contexto(llamador) == estado_original
        # La suma de comprobación tampoco hereda la precisión baja del llamador.
        with localcontext(Context(prec=40, flags=[], traps=[])):
            assert sum(resultado, Decimal("0")) == precio
    assert (precio.as_tuple(), porcentaje.as_tuple()) == entradas_originales


@pytest.mark.parametrize("redondeo", [ROUND_DOWN, ROUND_HALF_EVEN])
@pytest.mark.parametrize(
    ("precio", "porcentaje", "tipo_error", "mensaje"),
    [
        (Decimal("NaN"), Decimal("50"), ValueError, "El precio del servicio debe ser finito"),
        (Decimal("-1.000"), Decimal("50"), ValueError,
         "El precio del servicio debe tener como máximo dos decimales"),
        (Decimal("-1"), Decimal("50"), ValueError, "El precio del servicio no puede ser negativo"),
        (Decimal("100"), Decimal("sNaN"), ValueError, "El porcentaje debe ser finito"),
        (Decimal("100"), Decimal("50.000"), ValueError,
         "El porcentaje debe tener como máximo dos decimales"),
        (Decimal("100"), Decimal("-1"), ValueError, "El porcentaje debe estar entre 0 y 100"),
        ("100", Decimal("50"), TypeError, "El precio del servicio debe ser Decimal"),
        (Decimal("100"), "50", TypeError, "El porcentaje debe ser Decimal"),
    ],
)
def test_reparto_conserva_contexto_hostil_ante_entrada_invalida(
    precio: object,
    porcentaje: object,
    tipo_error: type[Exception],
    mensaje: str,
    redondeo: str,
) -> None:
    with localcontext(_contexto_hostil(redondeo)) as llamador:
        estado_original = _estado_contexto(llamador)
        with pytest.raises(tipo_error) as error:
            calcular_partes(precio, porcentaje)
        assert str(error.value) == mensaje
        assert getcontext() is llamador
        assert _estado_contexto(llamador) == estado_original


@pytest.mark.parametrize("redondeo", [ROUND_DOWN, ROUND_HALF_EVEN])
@pytest.mark.parametrize("texto_porcentaje", ["0", "50", "100"])
def test_reparto_limite_tecnico_se_rechaza_sin_asignacion_gigante(
    texto_porcentaje: str, redondeo: str
) -> None:
    # Decimal finito simbólico: representarlo al centavo excede MAX_PREC.
    precio = Decimal((0, (1,), MAX_EMAX))
    porcentaje = Decimal(texto_porcentaje)
    with localcontext(_contexto_hostil(redondeo)) as llamador:
        estado_original = _estado_contexto(llamador)
        try:
            with pytest.raises(ValueError) as error:
                calcular_partes(precio, porcentaje)
            assert str(error.value) == "No se puede representar el reparto con exactitud"
        finally:
            assert getcontext() is llamador
            assert _estado_contexto(llamador) == estado_original


@pytest.mark.parametrize("redondeo", [ROUND_DOWN, ROUND_HALF_EVEN])
@pytest.mark.parametrize("cero_en_precio", [True, False])
def test_reparto_cero_con_exponente_grande_es_representable(
    cero_en_precio: bool, redondeo: str
) -> None:
    cero = Decimal((1, (0,), MAX_EMAX))
    precio = cero if cero_en_precio else Decimal("100")
    porcentaje = Decimal("50") if cero_en_precio else cero
    entradas_originales = (precio.as_tuple(), porcentaje.as_tuple())
    esperado = (Decimal("0.00"), Decimal("0.00" if cero_en_precio else "100.00"))
    with localcontext(_contexto_hostil(redondeo)) as llamador:
        estado_original = _estado_contexto(llamador)
        try:
            resultado = calcular_partes(precio, porcentaje)
            assert resultado == esperado
            assert all(parte.as_tuple().exponent == -2 for parte in resultado)
        finally:
            assert getcontext() is llamador
            assert _estado_contexto(llamador) == estado_original
    assert (precio.as_tuple(), porcentaje.as_tuple()) == entradas_originales
