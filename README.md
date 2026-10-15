# Severance Pay Calculator — Argentine Labor Law

A Streamlit app that compares severance pay for a dismissal without cause under three regimes of Argentine labor law, side by side:

1. **Previous LCT regime** (Ley de Contrato de Trabajo, art. 245, before Law 27.802)
2. **Law 27.802** (labor reform: SAC and non-monthly bonuses are expressly excluded from the calculation base)
3. **Law 27.802 + FAL** (*Fondo de Asistencia Laboral*, an employer-funded severance fund that covers part or all of the severance)

It outputs a comparison table, a stacked chart, and a downloadable PDF report.

Built as part of a legal engineering portfolio.

> The interface is in Spanish, since it is meant for Argentine labor-law practitioners. The code and this README are in English.

---

## Background (for non-Argentine readers)

In Argentina, a worker dismissed without cause is entitled to a **severance payment** of one month's salary per year of service (art. 245 LCT), with a **cap** of three times the average salary of the applicable collective agreement (CCT). On top of that come the **notice period** (art. 231), the **month-integration** pay (art. 233), **proportional vacation** (arts. 150, 156) and **proportional 13th salary** (SAC).

Law 27.802 changes the calculation base and introduces the FAL, so the same dismissal can produce different amounts depending on the regime. This tool makes that difference visible.

---

## What it computes

| Concept | Rule implemented |
|---|---|
| Severance | Best monthly salary (capped at 3 × CCT average) × years of service; a fraction **greater than** 3 months counts as a full year; minimum 1 year |
| Law 27.802 base | Salary minus monthly-equivalent SAC and non-monthly bonuses |
| Notice period | 1 month up to 5 years of service, 2 months if it **exceeds** 5 years (real seniority, not the rounded severance years) |
| Month integration | Remaining days of the month × salary/30 — only if there was no notice |
| Vacation | 14 / 21 / 28 / 35 days by seniority (>5, >10, >20 years), proportional to time worked in the year, day value = salary/25 |
| FAL | Monthly contribution (1% large employers, 2.5% SMEs) on the adjusted salary, compounded monthly at an estimated yield |

The app warns when the dismissal date falls outside the validity period of a regime (Law 27.802 from 6/3/2026, FAL from 1/6/2026).

---

## Modeling assumptions and limitations

This is a **demonstration tool, not legal advice.** Known simplifications:

- **FAL waiting period:** modeled as a condition of use — the fund can be used only once at least 6 months of contributions exist, and then the full accumulated balance is used. The exact mechanism depends on the regulations and is not settled in the model.
- **FAL yield** is an adjustable assumption (default 5% per year).
- **The cap does not include the "Vizzoti" floor** (Argentine Supreme Court case limiting the cap's reduction of the base to 33%).
- **Vacation** assumes none was taken during the year; seniority is measured at the dismissal date.
- **Collective-agreement average (CCT):** entered by the user. The default in the form is only an example.
- The legal constants (FAL rates, effective dates) are kept in `calculos.py` and should be verified against the current legal text.
- The SAC on notice and integration amounts is not computed.

---

## Stack

- **Python 3.10+**
- **Streamlit** — web interface
- **matplotlib** — comparison chart
- **reportlab** — PDF report
- **python-dateutil** — seniority arithmetic
- **pytest** — unit tests

---

## Project structure

```
├── calculos.py          # Pure calculation logic (no UI)
├── main.py              # Streamlit app (inputs, tables, chart, PDF)
├── test_calculos.py     # Unit tests for the calculation logic
└── requirements.txt
```

---

## Run it

```bash
pip install -r requirements.txt
streamlit run main.py
```

Run the tests:

```bash
pip install pytest
pytest
```

---

## Author

**José Luis Lucero**  
Lawyer (UBA) | Legal Engineer  
Buenos Aires, Argentina  
[LinkedIn](https://www.linkedin.com/in/jose-luis-l-b452a873)

---

*This tool was built for portfolio and demonstration purposes. It does not replace professional legal advice.*
