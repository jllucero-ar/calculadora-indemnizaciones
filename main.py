# main.py
import streamlit as st
import matplotlib.pyplot as plt
from datetime import date
from dateutil.relativedelta import relativedelta
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from calculos import (
    comparar_regimenes,
    calcular_preaviso_meses,
    calcular_integracion,
    calcular_sac_proporcional,
    calcular_vacaciones,
    advertencias_vigencia,
    FAL_RENDIMIENTO_ANUAL,
)

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────

st.set_page_config(
    page_title="Liquidador de Indemnizaciones",
    page_icon="⚖️",
    layout="centered"
)

st.markdown("""
<style>
    .main { background-color: #0f1117; }
    .block-container { padding-top: 2rem; }
    h1 { color: #e8e8e8; }
    h2 { color: #c9d1d9; border-bottom: 1px solid #30363d; padding-bottom: 0.3rem; }
    .stButton>button {
        background-color: #1f6feb;
        color: white;
        border-radius: 6px;
        font-weight: bold;
    }
    .stButton>button:hover { background-color: #388bfd; }
    .stInfo { background-color: #1c2b3a; border-left: 4px solid #1f6feb; }
</style>
""", unsafe_allow_html=True)

st.title("⚖️ Liquidador de Indemnizaciones Laborales")
st.caption("Comparativa: LCT anterior · Ley 27.802 · Ley 27.802 + FAL")

# ─────────────────────────────────────────
# INPUTS
# ─────────────────────────────────────────

st.header("Datos del trabajador")

col1, col2 = st.columns(2)

with col1:
    fecha_ingreso_str = st.text_input(
        "Fecha de ingreso (DD/MM/AAAA)",
        value="01/04/2019",
        placeholder="DD/MM/AAAA"
    )

with col2:
    fecha_egreso_str = st.text_input(
        "Fecha de egreso (DD/MM/AAAA)",
        value="30/09/2026",
        placeholder="DD/MM/AAAA"
    )

st.header("Remuneración")

remuneracion = st.number_input(
    "Mejor remuneración mensual, normal y habitual ($)",
    min_value=0.0,
    value=900_000.0,
    step=10_000.0,
    format="%.0f"
)

sac = st.number_input(
    "SAC mensualizado a excluir (Ley 27.802) ($)",
    min_value=0.0,
    value=0.0,
    step=1_000.0,
    format="%.0f",
    help="Dividí el SAC anual estimado por 12"
)

premios = st.number_input(
    "Premios no mensuales a excluir (Ley 27.802) ($)",
    min_value=0.0,
    value=0.0,
    step=1_000.0,
    format="%.0f"
)

st.header("Convenio Colectivo y empresa")

promedio_cct = st.number_input(
    "Promedio remuneraciones CCT aplicable ($)",
    min_value=0.0,
    value=500_000.0,
    step=10_000.0,
    format="%.0f",
    help="Dato INDEC por actividad. Determina el tope del art. 245. "
         "El valor por defecto es solo un ejemplo: reemplazalo por el del CCT real."
)

tipo_empresa = st.radio(
    "Tipo de empresa (para alícuota FAL)",
    options=["grande", "pyme"],
    format_func=lambda x: "Grande (1%)" if x == "grande" else "PyME (2,5%)",
    horizontal=True
)

rendimiento_fal_pct = st.number_input(
    "Rendimiento anual estimado del FAL (%)",
    min_value=0.0,
    max_value=100.0,
    value=FAL_RENDIMIENTO_ANUAL * 100,
    step=0.5,
    help="Supuesto del modelo: el FAL se capitaliza mensualmente con esta tasa."
)

sin_preaviso = st.checkbox(
    "Despido sin preaviso (se abonan preaviso e integración del mes)",
    value=True,
    help="Arts. 231 y 233 LCT. Si el empleador otorgó el preaviso, no corresponde "
         "indemnización sustitutiva ni integración."
)

# ─────────────────────────────────────────
# UTILIDADES PDF
# ─────────────────────────────────────────

def generar_pdf(
    fecha_ingreso, fecha_egreso, remuneracion, sac, premios,
    promedio_cct, tipo_empresa, preaviso_meses, preaviso,
    dias_integracion, integracion, sac_proporcional, vacaciones,
    r1, r2, r3, total_r1, total_r2, total_r3
):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    elements = []

    titulo = ParagraphStyle("titulo", fontSize=16, fontName="Helvetica-Bold",
                             spaceAfter=6, textColor=colors.HexColor("#1f6feb"))
    subtitulo = ParagraphStyle("sub", fontSize=10, fontName="Helvetica",
                                spaceAfter=12, textColor=colors.grey)
    seccion = ParagraphStyle("sec", fontSize=11, fontName="Helvetica-Bold",
                              spaceAfter=6, spaceBefore=12,
                              textColor=colors.HexColor("#333333"))

    elements.append(Paragraph("Liquidación de Indemnización Laboral", titulo))
    elements.append(Paragraph(f"Fecha de cálculo: {date.today().strftime('%d/%m/%Y')}", subtitulo))
    elements.append(Spacer(1, 0.3*cm))

    # Datos ingresados
    elements.append(Paragraph("Datos ingresados", seccion))
    datos = [
        ["Concepto", "Valor"],
        ["Fecha de ingreso", fecha_ingreso.strftime('%d/%m/%Y')],
        ["Fecha de egreso", fecha_egreso.strftime('%d/%m/%Y')],
        ["Remuneración mensual normal y habitual", f"${remuneracion:,.0f}"],
        ["SAC excluido (Ley 27.802)", f"${sac:,.0f}"],
        ["Premios excluidos (Ley 27.802)", f"${premios:,.0f}"],
        ["Promedio CCT", f"${promedio_cct:,.0f}"],
        ["Tipo de empresa", tipo_empresa.upper()],
    ]
    t = Table(datos, colWidths=[9*cm, 7*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1f6feb")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f6f8fa")]),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#d0d7de")),
        ("PADDING", (0,0), (-1,-1), 5),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.4*cm))

    # Conceptos adicionales
    elements.append(Paragraph("Conceptos adicionales", seccion))
    adicionales = [
        ["Concepto", "Detalle", "Monto"],
        ["Preaviso", f"{preaviso_meses} mes/es", f"${preaviso:,.0f}"],
        ["Integración del mes", f"{dias_integracion} días", f"${integracion:,.0f}"],
        ["SAC proporcional", "", f"${sac_proporcional:,.0f}"],
        ["Vacaciones no gozadas", "", f"${vacaciones:,.0f}"],
    ]
    t2 = Table(adicionales, colWidths=[6*cm, 5*cm, 5*cm])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1f6feb")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f6f8fa")]),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#d0d7de")),
        ("PADDING", (0,0), (-1,-1), 5),
        ("ALIGN", (2,0), (2,-1), "RIGHT"),
    ]))
    elements.append(t2)
    elements.append(Spacer(1, 0.4*cm))

    # Resultados comparativos
    elements.append(Paragraph("Resultados comparativos", seccion))
    resultados_tabla = [
        ["Concepto", "LCT anterior", "Ley 27.802", "Ley 27.802 + FAL"],
        ["Base de cálculo",
         f"${r1['base_calculo']:,.0f}",
         f"${r2['base_calculo']:,.0f}",
         f"${r2['base_calculo']:,.0f}"],
        ["Tope aplicado",
         "Sí" if r1['tope_aplicado'] else "No",
         "Sí" if r2['tope_aplicado'] else "No",
         "Sí" if r2['tope_aplicado'] else "No"],
        ["Años indemnizables",
         str(r1['años_indemnizables']),
         str(r2['años_indemnizables']),
         str(r2['años_indemnizables'])],
        ["Indemnización",
         f"${r1['indemnizacion']:,.0f}",
         f"${r2['indemnizacion']:,.0f}",
         f"${r3['indemnizacion_total']:,.0f}"],
        ["Preaviso",
         f"${preaviso:,.0f}", f"${preaviso:,.0f}", f"${preaviso:,.0f}"],
        ["Integración del mes",
         f"${integracion:,.0f}", f"${integracion:,.0f}", f"${integracion:,.0f}"],
        ["SAC proporcional",
         f"${sac_proporcional:,.0f}", f"${sac_proporcional:,.0f}", f"${sac_proporcional:,.0f}"],
        ["Vacaciones no gozadas",
         f"${vacaciones:,.0f}", f"${vacaciones:,.0f}", f"${vacaciones:,.0f}"],
        ["TOTAL",
         f"${total_r1:,.0f}", f"${total_r2:,.0f}", f"${total_r3:,.0f}"],
        ["Cobertura FAL", "—", "—",
         f"${r3['saldo_fal_utilizable']:,.0f} ({r3['cobertura_fal_pct']}%)"],
        ["A cargo empleador", "—", "—",
         f"${r3['diferencia_a_cargo_empleador']:,.0f}"],
    ]
    t3 = Table(resultados_tabla, colWidths=[5*cm, 3.5*cm, 3.5*cm, 4*cm])
    t3.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1f6feb")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ("BACKGROUND", (0,-1), (-1,-1), colors.HexColor("#e8f0fe")),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS", (0,1), (-1,-2), [colors.white, colors.HexColor("#f6f8fa")]),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#d0d7de")),
        ("PADDING", (0,0), (-1,-1), 5),
        ("ALIGN", (1,0), (-1,-1), "RIGHT"),
    ]))
    elements.append(t3)
    elements.append(Spacer(1, 0.5*cm))

    # Disclaimer
    disclaimer = ParagraphStyle("disc", fontSize=8, textColor=colors.grey,
                                 fontName="Helvetica-Oblique")
    elements.append(Paragraph(
        "Aviso: este reporte tiene fines informativos. No constituye asesoramiento jurídico. "
        "La Ley 27.802 está sujeta a reglamentación complementaria e interpretación judicial. "
        "Verificá siempre los valores de CCT con los datos INDEC vigentes.",
        disclaimer
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer

# ─────────────────────────────────────────
# CÁLCULO
# ─────────────────────────────────────────

calcular = st.button("Calcular", type="primary", use_container_width=True)

if calcular:

    # Validación formato fechas
    errores = []
    fecha_ingreso = None
    fecha_egreso = None

    for label, valor in [("ingreso", fecha_ingreso_str), ("egreso", fecha_egreso_str)]:
        if len(valor) != 10 or valor[2] != "/" or valor[5] != "/":
            errores.append(f"Formato de fecha de {label} incorrecto. Usá DD/MM/AAAA.")
        else:
            try:
                d = date(int(valor[6:10]), int(valor[3:5]), int(valor[0:2]))
                if label == "ingreso":
                    fecha_ingreso = d
                else:
                    fecha_egreso = d
            except Exception:
                errores.append(f"Fecha de {label} inválida.")

    if fecha_ingreso and fecha_egreso and fecha_egreso <= fecha_ingreso:
        errores.append("La fecha de egreso debe ser posterior a la de ingreso.")
    if remuneracion <= 0:
        errores.append("Ingresá una remuneración válida.")
    if promedio_cct <= 0:
        errores.append("Ingresá el promedio CCT.")

    if errores:
        for e in errores:
            st.error(e)
    else:
        resultados = comparar_regimenes(
            remuneracion=remuneracion,
            fecha_ingreso=fecha_ingreso,
            fecha_egreso=fecha_egreso,
            promedio_cct=promedio_cct,
            tipo_empresa=tipo_empresa,
            sac_mensualizado=sac,
            premios_no_mensuales=premios,
            rendimiento_anual_fal=rendimiento_fal_pct / 100,
        )

        r1, r2, r3 = resultados

        for aviso in advertencias_vigencia(fecha_egreso):
            st.warning(aviso)

        # ── Preaviso e integración (arts. 231 y 233: solo si no hubo preaviso) ──
        if sin_preaviso:
            preaviso_meses = calcular_preaviso_meses(fecha_ingreso, fecha_egreso)
            preaviso = remuneracion * preaviso_meses
            dias_integracion, integracion = calcular_integracion(remuneracion, fecha_egreso)
        else:
            preaviso_meses, preaviso = 0, 0.0
            dias_integracion, integracion = 0, 0.0

        # ── SAC proporcional ──
        dias_semestre, sac_proporcional = calcular_sac_proporcional(
            remuneracion, fecha_ingreso, fecha_egreso
        )

        # ── Vacaciones no gozadas ──
        dias_vac_proporcionales, vacaciones = calcular_vacaciones(
            remuneracion, fecha_ingreso, fecha_egreso
        )

        # ── Totales ──
        adicionales = preaviso + integracion + sac_proporcional + vacaciones
        total_r1 = r1["indemnizacion"] + adicionales
        total_r2 = r2["indemnizacion"] + adicionales
        total_r3 = r3["indemnizacion_total"] + adicionales

        # ── TABLA COMPARATIVA ──
        st.header("Resultado comparativo")

        st.markdown(f"""
| Concepto | LCT anterior | Ley 27.802 | Ley 27.802 + FAL |
|---|---:|---:|---:|
| **Base de cálculo** | ${r1['base_calculo']:,.0f} | ${r2['base_calculo']:,.0f} | ${r2['base_calculo']:,.0f} |
| **Tope aplicado** | {'Sí' if r1['tope_aplicado'] else 'No'} | {'Sí' if r2['tope_aplicado'] else 'No'} | {'Sí' if r2['tope_aplicado'] else 'No'} |
| **Años indemnizables** | {r1['años_indemnizables']} | {r2['años_indemnizables']} | {r2['años_indemnizables']} |
| **Indemnización** | ${r1['indemnizacion']:,.0f} | ${r2['indemnizacion']:,.0f} | ${r3['indemnizacion_total']:,.0f} |
| **Preaviso** ({preaviso_meses} mes/es) | ${preaviso:,.0f} | ${preaviso:,.0f} | ${preaviso:,.0f} |
| **Integración del mes** ({dias_integracion} días) | ${integracion:,.0f} | ${integracion:,.0f} | ${integracion:,.0f} |
| **SAC proporcional** ({dias_semestre} días) | ${sac_proporcional:,.0f} | ${sac_proporcional:,.0f} | ${sac_proporcional:,.0f} |
| **Vacaciones no gozadas** ({dias_vac_proporcionales} días) | ${vacaciones:,.0f} | ${vacaciones:,.0f} | ${vacaciones:,.0f} |
| **TOTAL** | **${total_r1:,.0f}** | **${total_r2:,.0f}** | **${total_r3:,.0f}** |
| **Cobertura FAL** | — | — | ${r3['saldo_fal_utilizable']:,.0f} ({r3['cobertura_fal_pct']}%) |
| **A cargo empleador** | — | — | ${r3['diferencia_a_cargo_empleador']:,.0f} |
""")

        st.caption(
            f"Supuestos FAL: {r3['meses_aportados']} meses de aportes "
            f"({r3['alicuota_fal']} de la remuneración depurada), rendimiento anual "
            f"{r3['rendimiento_anual_fal'] * 100:g}%, utilizable con al menos 6 meses "
            f"de aportes ({'cumplido' if r3['fal_utilizable'] else 'no cumplido'})."
        )

        diferencia = total_r1 - total_r2
        pct = diferencia / total_r1 * 100
        if diferencia > 0:
            st.info(
                f"💡 Con la Ley 27.802 el total a cobrar es "
                f"**${diferencia:,.0f} menor** que bajo el régimen anterior "
                f"({pct:.1f}% menos)."
            )
        elif diferencia < 0:
            st.info(
                f"💡 Con la Ley 27.802 el total a cobrar es "
                f"**${-diferencia:,.0f} mayor** que bajo el régimen anterior."
            )
        else:
            st.info(
                "💡 En este caso ambos regímenes dan el mismo total: no hay SAC ni "
                "premios a excluir y el tope no afecta la diferencia."
            )

        # ── DETALLE EXCLUSIONES ──
        if sac > 0 or premios > 0:
            with st.expander("📋 Detalle de conceptos excluidos (Ley 27.802)"):
                st.markdown(f"""
**Remuneración bruta ingresada:** ${remuneracion:,.0f}

**Conceptos excluidos por art. 245 Ley 27.802:**
- SAC mensualizado: ${sac:,.0f}
- Premios no mensuales: ${premios:,.0f}
- **Total excluido: ${sac + premios:,.0f}**

**Base de cálculo resultante:** ${r2['base_calculo']:,.0f}

*La Ley 27.802 excluye expresamente el SAC y los conceptos de pago no mensual \
de la base indemnizatoria (art. 245). Bajo el régimen anterior, \
la jurisprudencia era variable respecto del SAC.*
""")

        # ── GRÁFICO ──
        st.header("Comparación gráfica")

        etiquetas = ["LCT anterior", "Ley 27.802", "Ley 27.802\n+ FAL"]
        v_indem = [r1['indemnizacion'], r2['indemnizacion'], r3['indemnizacion_total']]
        v_prev  = [preaviso] * 3
        v_integ = [integracion] * 3
        v_sac   = [sac_proporcional] * 3
        v_vac   = [vacaciones] * 3

        fig, ax = plt.subplots(figsize=(8, 5))
        colores_base = ["#4C72B0", "#DD8452", "#55A868"]

        b1 = ax.bar(etiquetas, v_indem, color=colores_base, width=0.5, label="Indemnización")
        b2 = ax.bar(etiquetas, v_prev, bottom=v_indem,
                    color=["#7fa8d4","#e8aa80","#88c49a"], width=0.5, label="Preaviso")
        b3 = ax.bar(etiquetas, v_integ,
                    bottom=[a+b for a,b in zip(v_indem, v_prev)],
                    color=["#b3cfe8","#f2cc99","#b3dfc0"], width=0.5, label="Integración")
        b4 = ax.bar(etiquetas, v_sac,
                    bottom=[a+b+c for a,b,c in zip(v_indem, v_prev, v_integ)],
                    color=["#d9e8f5","#f8e4c2","#d4edd9"], width=0.5, label="SAC prop.")
        b5 = ax.bar(etiquetas, v_vac,
                    bottom=[a+b+c+d for a,b,c,d in zip(v_indem, v_prev, v_integ, v_sac)],
                    color=["#eef3f9","#fdf3e3","#edf7ee"], width=0.5, label="Vacaciones")

        totales = [total_r1, total_r2, total_r3]
        for bar, total in zip(b1, totales):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                total + max(totales) * 0.01,
                f"${total:,.0f}",
                ha="center", va="bottom", fontsize=9, fontweight="bold"
            )

        ax.set_ylabel("Monto total ($)", fontsize=11)
        ax.set_title("Liquidación total por régimen", fontsize=13, fontweight="bold")
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_ylim(0, max(totales) * 1.15)
        ax.legend(loc="upper right", fontsize=8)
        st.pyplot(fig)
        plt.close(fig)

        # ── EXPORTAR PDF ──
        st.header("Exportar")

        pdf_buffer = generar_pdf(
            fecha_ingreso, fecha_egreso, remuneracion, sac, premios,
            promedio_cct, tipo_empresa, preaviso_meses, preaviso,
            dias_integracion, integracion, sac_proporcional, vacaciones,
            r1, r2, r3, total_r1, total_r2, total_r3
        )

        st.download_button(
            label="⬇️ Descargar reporte PDF",
            data=pdf_buffer,
            file_name=f"liquidacion_{fecha_egreso.strftime('%d%m%Y')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

        # ── DISCLAIMER ──
        st.divider()
        st.caption(
            "⚠️ Este liquidador tiene fines informativos y de portfolio. "
            "No constituye asesoramiento jurídico. "
            "La Ley 27.802 está sujeta a reglamentación complementaria e interpretación judicial. "
            "Verificá siempre los valores de CCT con los datos INDEC vigentes."
        )