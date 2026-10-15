from datetime import date

from calculos import (
    advertencias_vigencia,
    antigüedad_excede,
    calcular_años_indemnizables,
    calcular_integracion,
    calcular_preaviso_meses,
    calcular_sac_proporcional,
    calcular_vacaciones,
    comparar_regimenes,
    lct_27802_con_fal,
)


def test_años_indemnizables_fraccion_mayor_a_tres_meses():
    assert calcular_años_indemnizables(date(2020, 1, 1), date(2022, 4, 1)) == 2  # 3 meses justos
    assert calcular_años_indemnizables(date(2020, 1, 1), date(2022, 4, 2)) == 3  # 3 meses y 1 día
    assert calcular_años_indemnizables(date(2026, 1, 1), date(2026, 2, 1)) == 1  # mínimo 1 año


def test_preaviso_cinco_años_justos_es_un_mes():
    assert calcular_preaviso_meses(date(2021, 10, 1), date(2026, 10, 1)) == 1
    assert calcular_preaviso_meses(date(2021, 10, 1), date(2026, 10, 2)) == 2


def test_preaviso_no_usa_redondeo_de_fraccion():
    # 4 años y 5 meses: indemnizables = 5, pero la antigüedad real no excede 5 años
    assert calcular_años_indemnizables(date(2021, 5, 1), date(2025, 10, 1)) == 5
    assert calcular_preaviso_meses(date(2021, 5, 1), date(2025, 10, 1)) == 1


def test_antigüedad_excede():
    assert not antigüedad_excede(date(2016, 1, 1), date(2026, 1, 1), 10)
    assert antigüedad_excede(date(2016, 1, 1), date(2026, 1, 2), 10)


def test_vacaciones_dias_segun_antigüedad():
    # Egreso el 31/12: año completo trabajado -> días plenos
    assert calcular_vacaciones(1000, date(2022, 1, 1), date(2026, 12, 31))[0] == 14  # < 5
    assert calcular_vacaciones(1000, date(2021, 1, 1), date(2026, 12, 31))[0] == 21  # > 5
    assert calcular_vacaciones(1000, date(2016, 1, 1), date(2026, 12, 31))[0] == 28  # > 10
    assert calcular_vacaciones(1000, date(2006, 1, 1), date(2026, 12, 31))[0] == 35  # > 20


def test_vacaciones_valor_dia_es_remuneracion_sobre_25():
    dias, monto = calcular_vacaciones(2500, date(2022, 1, 1), date(2026, 12, 31))
    assert monto == 100 * dias


def test_vacaciones_proporcional_desde_ingreso_en_el_mismo_año():
    dias, _ = calcular_vacaciones(1000, date(2026, 7, 1), date(2026, 12, 31))
    assert dias == round(14 * 184 / 365)


def test_integracion_del_mes():
    dias, monto = calcular_integracion(30_000, date(2026, 9, 20))
    assert dias == 10 and monto == 10_000
    assert calcular_integracion(30_000, date(2026, 9, 30)) == (0, 0)


def test_sac_proporcional_desde_ingreso_en_el_semestre():
    dias, _ = calcular_sac_proporcional(1000, date(2026, 8, 1), date(2026, 9, 30))
    assert dias == 61


def test_tope_y_exclusiones():
    r1, r2, _ = comparar_regimenes(
        900_000, date(2019, 4, 1), date(2026, 9, 30), 500_000,
        sac_mensualizado=75_000, premios_no_mensuales=20_000,
    )
    assert r1["base_calculo"] == 900_000          # tope = 1.5M, no se aplica
    assert r2["base_calculo"] == 805_000          # 900k - 75k - 20k
    assert r1["años_indemnizables"] == 8
    assert r1["indemnizacion"] == 900_000 * 8
    assert r2["indemnizacion"] == 805_000 * 8


def test_tope_aplicado():
    r1, _, _ = comparar_regimenes(5_000_000, date(2019, 4, 1), date(2026, 9, 30), 500_000)
    assert r1["tope_aplicado"] and r1["base_calculo"] == 1_500_000


def test_fal_carencia_condicion_de_uso():
    # 3 meses de aportes: no utilizable
    corto = lct_27802_con_fal(900_000, date(2026, 6, 1), date(2026, 9, 1), 500_000)
    assert corto["meses_aportados"] == 3
    assert not corto["fal_utilizable"] and corto["saldo_fal_utilizable"] == 0
    # 12 meses: se usa el saldo total acumulado
    largo = lct_27802_con_fal(900_000, date(2026, 6, 1), date(2027, 6, 1), 500_000)
    assert largo["meses_aportados"] == 12
    assert largo["fal_utilizable"]
    assert largo["saldo_fal_utilizable"] == largo["saldo_fal_total"]


def test_fal_aporte_sobre_remuneracion_depurada():
    r = lct_27802_con_fal(
        1_000_000, date(2026, 6, 1), date(2027, 6, 1), 5_000_000,
        tipo_empresa="grande", sac_mensualizado=100_000,
    )
    assert r["aporte_mensual_fal"] == 9_000  # 1% de 900k


def test_fal_sin_aportes_antes_de_su_vigencia():
    r = lct_27802_con_fal(900_000, date(2015, 1, 1), date(2026, 5, 1), 500_000)
    assert r["meses_aportados"] == 0 and r["saldo_fal_total"] == 0


def test_advertencias_vigencia():
    assert any("anterior a la vigencia" in a for a in advertencias_vigencia(date(2025, 1, 1)))
    assert any("hipotética" in a for a in advertencias_vigencia(date(2026, 9, 30)))
    assert any("FAL" in a for a in advertencias_vigencia(date(2026, 4, 1)))
