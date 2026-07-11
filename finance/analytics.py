"""Agregações para os gráficos e indicadores do dashboard."""

from __future__ import annotations

import pandas as pd


def _prep(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "amount"])
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    return df


def monthly_cashflow(df: pd.DataFrame) -> pd.DataFrame:
    """Receitas, despesas e saldo por mês."""
    if df.empty:
        return pd.DataFrame(columns=["month", "receitas", "despesas", "saldo"])
    d = _prep(df)
    receitas = d[d["amount"] > 0].groupby("month")["amount"].sum()
    despesas = d[d["amount"] < 0].groupby("month")["amount"].sum().abs()
    out = pd.DataFrame({"receitas": receitas, "despesas": despesas}).fillna(0)
    out["saldo"] = out["receitas"] - out["despesas"]
    return out.reset_index().sort_values("month")


def expenses_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """Total de despesas por categoria (valores positivos)."""
    if df.empty:
        return pd.DataFrame(columns=["category", "total"])
    d = _prep(df)
    d = d[d["amount"] < 0].copy()
    d["total"] = d["amount"].abs()
    out = d.groupby("category", dropna=False)["total"].sum().reset_index()
    out["category"] = out["category"].fillna("Outros")
    return out.sort_values("total", ascending=False)


def category_by_month(df: pd.DataFrame) -> pd.DataFrame:
    """Despesa por categoria e por mês (formato longo, pra gráfico empilhado)."""
    if df.empty:
        return pd.DataFrame(columns=["month", "category", "total"])
    d = _prep(df)
    d = d[d["amount"] < 0].copy()
    d["total"] = d["amount"].abs()
    d["category"] = d["category"].fillna("Outros")
    out = d.groupby(["month", "category"])["total"].sum().reset_index()
    return out.sort_values("month")


def balance_series(df: pd.DataFrame) -> pd.DataFrame:
    """Saldo acumulado ao longo do tempo (soma corrente de todos os lançamentos)."""
    if df.empty:
        return pd.DataFrame(columns=["date", "saldo_acumulado"])
    d = _prep(df).sort_values("date")
    d["saldo_acumulado"] = d["amount"].cumsum()
    return d[["date", "saldo_acumulado"]]


def top_expenses(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """As maiores despesas individuais."""
    if df.empty:
        return df
    d = _prep(df)
    d = d[d["amount"] < 0].copy()
    d["valor"] = d["amount"].abs()
    cols = ["date", "description", "category", "valor"]
    return d.sort_values("valor", ascending=False).head(n)[cols]


def kpis(df: pd.DataFrame) -> dict:
    """Indicadores-resumo pra exibir no topo do dashboard."""
    if df.empty:
        return {"receitas": 0.0, "despesas": 0.0, "saldo": 0.0,
                "media_despesa_mensal": 0.0, "meses": 0}
    cf = monthly_cashflow(df)
    return {
        "receitas": float(cf["receitas"].sum()),
        "despesas": float(cf["despesas"].sum()),
        "saldo": float(cf["saldo"].sum()),
        "media_despesa_mensal": float(cf["despesas"].mean()) if len(cf) else 0.0,
        "meses": int(len(cf)),
    }
