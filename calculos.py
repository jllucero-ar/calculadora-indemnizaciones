# calculos.py
# Liquidador de indemnizaciones laborales
# Regímenes: LCT anterior | Ley 27.802 | Ley 27.802 + FAL

import calendar
from datetime import date
from dateutil.relativedelta import relativedelta

# ─────────────────────────────────────────
# CONSTANTES — verificar contra el texto vigente
# ─────────────────────────────────────────

# Vigencia de la Ley 27.802 (el régimen anterior rige hasta el día previo)
FECHA_VIGENCIA_27802 = date(2026, 3, 6)

# FAL — Fondo de Asistencia Laboral
FAL_ALICUOTA_GRANDE = 0.01    # 1% grandes empresas
FAL_ALICUOTA_PYME   = 0.025   # 2,5% PyMEs
FAL_INICIO          = date(2026, 6, 1)   # vigencia FAL
FAL_CARENCIA_MESES  = 6       # el fondo se puede usar recién con 6 meses de aportes
FAL_RENDIMIENTO_ANUAL = 0.05  # supuesto de rendimiento (ajustable por el usuario)

# Tope art. 245: 3 × promedio de remuneraciones del CCT aplicable.
# El promedio varía por convenio: siempre lo ingresa el usuario.

# ─────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────

def calcular_años_indemnizables(fecha_ingreso: date, fecha_egreso: date) -> int:
    """
    Años para la indemnización por antigüedad (art. 245 LCT).
    Fracción > 3 meses se computa como año completo. Mínimo: 1 año.
    """
    delta = relativedelta(fecha_egreso, fecha_ingreso)
    fraccion_mayor_a_3_meses = delta.months > 3 or (delta.months == 3 and delta.days > 0)
    años = delta.years + (1 if fraccion_mayor_a_3_meses else 0)
    return max(años, 1)


def antigüedad_excede(fecha_ingreso: date, fecha_egreso: date, años: int) -> bool:
    """True si la antigüedad real es MAYOR a `años` (no igual)."""
    delta = relativedelta(fecha_egreso, fecha_ingreso)
    return delta.years > años or (
        delta.years == años and (delta.months > 0 or delta.days > 0)
    )


def aplicar_tope(remuneracion: float, promedio_cct: float) -> tuple[float, float]:
    """Devuelve (base con tope aplicado, tope máximo)."""
    tope = promedio_cct * 3
    return min(remuneracion, tope), tope


def calcular_preaviso_meses(fecha_ingreso: date, fecha_egreso: date) -> int:
    """Art. 231 LCT: 1 mes hasta 5 años de antigüedad, 2 meses si excede de 5."""
    return 2 if antigüedad_excede(fecha_ingreso, fecha_egreso, 5) else 1


def calcular_integracion(remuneracion: float, fecha_egreso: date) -> tuple[int, float]:
    """
    Art. 233 LCT: días que faltan para fin de mes (1/30 de la remuneración por día).
    Devuelve (días, monto).
    """
    ultimo_dia = calendar.monthrange(fecha_egreso.year, fecha_egreso.month)[1]
    dias = ultimo_dia - fecha_egreso.day
    return dias, (remuneracion / 30) * dias


def calcular_sac_proporcional(
    remuneracion: float, fecha_ingreso: date, fecha_egreso: date
) -> tuple[int, float]:
    """SAC proporcional del semestre en curso. Devuelve (días, monto)."""
    mes_inicio = 1 if fecha_egreso.month <= 6 else 7
    inicio = max(date(fecha_egreso.year, mes_inicio, 1), fecha_ingreso)
    dias = (fecha_egreso - inicio).days + 1
    return dias, (remuneracion / 365) * dias


def calcular_vacaciones(
    remuneracion: float, fecha_ingreso: date, fecha_egreso: date
) -> tuple[int, float]:
    """
    Vacaciones proporcionales no gozadas (arts. 150 y 156 LCT).
    Días según antigüedad (14/21/28/35), proporcionales a lo trabajado en el año.
    Valor del día: remuneración / 25. Devuelve (días proporcionales, monto).
    Supuesto: no se gozó ninguna vacación del año.
    """
    if antigüedad_excede(fecha_ingreso, fecha_egreso, 20):
        dias_vac = 35
    elif antigüedad_excede(fecha_ingreso, fecha_egreso, 10):
        dias_vac = 28
    elif antigüedad_excede(fecha_ingreso, fecha_egreso, 5):
        dias_vac = 21
    else:
        dias_vac = 14

    inicio = max(date(fecha_egreso.year, 1, 1), fecha_ingreso)
    dias_trabajados = (fecha_egreso - inicio).days + 1
    dias_proporcionales = round(dias_vac * dias_trabajados / 365)
    return dias_proporcionales, (remuneracion / 25) * dias_proporcionales


def advertencias_vigencia(fecha_egreso: date) -> list[str]:
    """Avisos cuando la fecha de egreso cae fuera de la vigencia de algún régimen."""
    avisos = []
    if fecha_egreso < FECHA_VIGENCIA_27802:
        avisos.append(
            "La fecha de egreso es anterior a la vigencia de la Ley 27.802 "
            f"({FECHA_VIGENCIA_27802.strftime('%d/%m/%Y')}): en un caso real solo "
            "sería aplicable el régimen anterior. Las demás columnas son hipotéticas."
        )
    else:
        avisos.append(
            "La fecha de egreso es posterior a la vigencia de la Ley 27.802: "
            "la columna 'LCT anterior' es hipotética (solo a fines comparativos)."
        )
    if fecha_egreso < FAL_INICIO:
        avisos.append(
            f"El FAL entra en vigencia el {FAL_INICIO.strftime('%d/%m/%Y')}: "
            "a esta fecha de egreso no hay aportes acumulados."
        )
    return avisos

# ─────────────────────────────────────────
# RÉGIMEN 1 — LCT anterior (hasta 5/3/2026)
# ─────────────────────────────────────────

def lct_anterior(
    remuneracion: float,
    fecha_ingreso: date,
    fecha_egreso: date,
    promedio_cct: float,
) -> dict:
    """
    Art. 245 LCT texto anterior a Ley 27.802.
    Base: mejor remuneración mensual, normal y habitual
          (sin exclusión expresa del SAC — criterio jurisprudencial variable).
    Tope: 3 × promedio CCT. No contempla el piso "Vizzoti" (CSJN).
    """
    base, tope = aplicar_tope(remuneracion, promedio_cct)
    años = calcular_años_indemnizables(fecha_ingreso, fecha_egreso)
    indemnizacion = base * años

    return {
        "regimen": "LCT anterior (hasta 5/3/2026)",
        "remuneracion_ingresada": remuneracion,
        "promedio_cct": promedio_cct,
        "tope_maximo": tope,
        "base_calculo": base,
        "tope_aplicado": remuneracion > tope,
        "años_indemnizables": años,
        "indemnizacion": round(indemnizacion, 2),
    }

# ─────────────────────────────────────────
# RÉGIMEN 2 — Ley 27.802 (desde 6/3/2026)
# ─────────────────────────────────────────

def lct_27802(
    remuneracion: float,
    fecha_ingreso: date,
    fecha_egreso: date,
    promedio_cct: float,
    sac_mensualizado: float = 0.0,
    premios_no_mensuales: float = 0.0,
) -> dict:
    """
    Art. 245 LCT según Ley 27.802.
    Base: mejor remuneración mensual, normal y habitual
          EXCLUYENDO expresamente SAC y premios no mensuales.
    Tope: 3 × promedio CCT aplicable.
    """
    remuneracion_depurada = remuneracion - sac_mensualizado - premios_no_mensuales
    base, tope = aplicar_tope(remuneracion_depurada, promedio_cct)
    años = calcular_años_indemnizables(fecha_ingreso, fecha_egreso)
    indemnizacion = base * años

    return {
        "regimen": "Ley 27.802 (desde 6/3/2026)",
        "remuneracion_bruta": remuneracion,
        "sac_excluido": sac_mensualizado,
        "premios_excluidos": premios_no_mensuales,
        "remuneracion_depurada": round(remuneracion_depurada, 2),
        "promedio_cct": promedio_cct,
        "tope_maximo": tope,
        "base_calculo": base,
        "tope_aplicado": remuneracion_depurada > tope,
        "años_indemnizables": años,
        "indemnizacion": round(indemnizacion, 2),
    }

# ─────────────────────────────────────────
# RÉGIMEN 3 — Ley 27.802 + FAL
# ─────────────────────────────────────────

def lct_27802_con_fal(
    remuneracion: float,
    fecha_ingreso: date,
    fecha_egreso: date,
    promedio_cct: float,
    tipo_empresa: str = "grande",   # "grande" | "pyme"
    sac_mensualizado: float = 0.0,
    premios_no_mensuales: float = 0.0,
    rendimiento_anual_fal: float = FAL_RENDIMIENTO_ANUAL,
) -> dict:
    """
    Ley 27.802 + FAL vigente desde 1/6/2026.
    El FAL no reemplaza la indemnización: la cubre total o parcialmente.
    El empleador paga la diferencia si el fondo no alcanza.

    Supuestos del modelo:
    - Aporte mensual = alícuota × remuneración depurada (misma base que la indemnización).
    - Capitalización mensual con el rendimiento estimado.
    - Carencia: el fondo es utilizable solo si hay al menos FAL_CARENCIA_MESES
      de aportes; en ese caso se usa el saldo total acumulado.
    """
    resultado_base = lct_27802(
        remuneracion, fecha_ingreso, fecha_egreso,
        promedio_cct, sac_mensualizado, premios_no_mensuales
    )
    indemnizacion_total = resultado_base["indemnizacion"]

    alicuota = FAL_ALICUOTA_GRANDE if tipo_empresa == "grande" else FAL_ALICUOTA_PYME
    aporte_mensual = resultado_base["remuneracion_depurada"] * alicuota
    tasa_mensual = rendimiento_anual_fal / 12

    # Meses de aporte: desde el mayor entre ingreso y vigencia del FAL
    inicio_fal = max(fecha_ingreso, FAL_INICIO)
    if fecha_egreso <= inicio_fal:
        meses_fal = 0
    else:
        delta_fal = relativedelta(fecha_egreso, inicio_fal)
        meses_fal = delta_fal.years * 12 + delta_fal.months

    saldo_fal = 0.0
    for _ in range(meses_fal):
        saldo_fal = (saldo_fal + aporte_mensual) * (1 + tasa_mensual)

    utilizable = meses_fal >= FAL_CARENCIA_MESES
    saldo_utilizable = min(saldo_fal, indemnizacion_total) if utilizable else 0.0
    diferencia_empleador = max(indemnizacion_total - saldo_utilizable, 0)

    return {
        "regimen": "Ley 27.802 + FAL",
        "indemnizacion_total": round(indemnizacion_total, 2),
        "tipo_empresa": tipo_empresa,
        "alicuota_fal": f"{alicuota * 100:g}%",
        "rendimiento_anual_fal": rendimiento_anual_fal,
        "aporte_mensual_fal": round(aporte_mensual, 2),
        "meses_aportados": meses_fal,
        "fal_utilizable": utilizable,
        "saldo_fal_total": round(saldo_fal, 2),
        "saldo_fal_utilizable": round(saldo_utilizable, 2),
        "diferencia_a_cargo_empleador": round(diferencia_empleador, 2),
        "cobertura_fal_pct": round(
            (saldo_utilizable / indemnizacion_total * 100) if indemnizacion_total > 0 else 0, 1
        ),
    }

# ─────────────────────────────────────────
# COMPARADOR UNIFICADO
# ─────────────────────────────────────────

def comparar_regimenes(
    remuneracion: float,
    fecha_ingreso: date,
    fecha_egreso: date,
    promedio_cct: float,
    tipo_empresa: str = "grande",
    sac_mensualizado: float = 0.0,
    premios_no_mensuales: float = 0.0,
    rendimiento_anual_fal: float = FAL_RENDIMIENTO_ANUAL,
) -> list:
    return [
        lct_anterior(remuneracion, fecha_ingreso, fecha_egreso, promedio_cct),
        lct_27802(remuneracion, fecha_ingreso, fecha_egreso,
                  promedio_cct, sac_mensualizado, premios_no_mensuales),
        lct_27802_con_fal(remuneracion, fecha_ingreso, fecha_egreso,
                          promedio_cct, tipo_empresa,
                          sac_mensualizado, premios_no_mensuales,
                          rendimiento_anual_fal),
    ]


# ─────────────────────────────────────────
# DEMO (python calculos.py)
# ─────────────────────────────────────────

if __name__ == "__main__":
    from pprint import pprint

    resultados = comparar_regimenes(
        remuneracion=900_000,
        fecha_ingreso=date(2019, 4, 1),
        fecha_egreso=date(2026, 9, 30),
        promedio_cct=500_000,
        tipo_empresa="pyme",
        sac_mensualizado=75_000,
        premios_no_mensuales=20_000,
    )

    for r in resultados:
        pprint(r)
        print()
