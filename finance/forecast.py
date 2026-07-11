"""Previsões: aprende com o histórico e projeta os próximos meses.

Método (simples e robusto para poucos meses de dados):
- Agrega despesas/receitas por mês.
- Ajusta uma tendência linear (regressão) sobre o índice do mês e combina com a
  média recente, evitando projeções absurdas quando há poucos pontos.
- Projeta o saldo acumulado somando a previsão de receitas menos despesas.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import analytics


def _linear_forecast(values: np.ndarray, steps: int) -> np.ndarray:
    """Previsão por tendência linear, misturada com a média para estabilizar."""
    n = len(values)
    if n == 0:
        return np.zeros(steps)
    if n < 3:
        return np.repeat(values.mean(), steps)

    x = np.arange(n)
    slope, intercept = np.polyfit(x, values, 1)
    future_x = np.arange(n, n + steps)
    trend = slope * future_x + intercept

    recent_mean = values[-3:].mean()
    # 60% tendência + 40% média recente; nunca negativo
    blended = 0.6 * trend + 0.4 * recent_mean
    return np.clip(blended, 0, None)


def forecast_cashflow(df: pd.DataFrame, months: int = 3) -> pd.DataFrame:
    """Projeta receitas, despesas e saldo para os próximos ``months`` meses."""
    cf = analytics.monthly_cashflow(df)
    if cf.empty:
        return pd.DataFrame(columns=["month", "receitas", "despesas", "saldo",
                                     "tipo"])

    receitas_prev = _linear_forecast(cf["receitas"].to_numpy(float), months)
    despesas_prev = _linear_forecast(cf["despesas"].to_numpy(float), months)

    last_month = cf["month"].max()
    future_months = pd.date_range(
        last_month + pd.offsets.MonthBegin(1), periods=months, freq="MS"
    )
    prev = pd.DataFrame({
        "month": future_months,
        "receitas": receitas_prev,
        "despesas": despesas_prev,
    })
    prev["saldo"] = prev["receitas"] - prev["despesas"]
    prev["tipo"] = "previsto"

    hist = cf.copy()
    hist["tipo"] = "real"
    return pd.concat([hist, prev], ignore_index=True)


def forecast_by_category(df: pd.DataFrame, months: int = 3) -> pd.DataFrame:
    """Projeta a despesa do próximo período por categoria."""
    cbm = analytics.category_by_month(df)
    if cbm.empty:
        return pd.DataFrame(columns=["category", "previsto_mensal"])

    rows = []
    for cat, g in cbm.groupby("category"):
        serie = g.sort_values("month")["total"].to_numpy(float)
        pred = _linear_forecast(serie, 1)[0]
        rows.append({"category": cat, "previsto_mensal": round(float(pred), 2)})
    out = pd.DataFrame(rows).sort_values("previsto_mensal", ascending=False)
    return out.reset_index(drop=True)


def projected_balance(df: pd.DataFrame, months: int = 3) -> pd.DataFrame:
    """Projeta o saldo acumulado a partir do saldo atual + fluxo previsto."""
    bal = analytics.balance_series(df)
    current = float(bal["saldo_acumulado"].iloc[-1]) if not bal.empty else 0.0

    fc = forecast_cashflow(df, months)
    prev = fc[fc["tipo"] == "previsto"].copy()
    if prev.empty:
        return pd.DataFrame(columns=["month", "saldo_projetado"])

    prev = prev.sort_values("month")
    prev["saldo_projetado"] = current + prev["saldo"].cumsum()
    return prev[["month", "saldo_projetado"]].reset_index(drop=True)
