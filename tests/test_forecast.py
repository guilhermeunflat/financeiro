import numpy as np
import pandas as pd

from finance import analytics, forecast


def _historico():
    # 6 meses de dados: salário + despesas
    linhas = []
    for mes in range(1, 7):
        linhas.append({"date": pd.Timestamp(2026, mes, 1),
                       "description": "Salario", "amount": 5000.0,
                       "category": "Renda"})
        linhas.append({"date": pd.Timestamp(2026, mes, 10),
                       "description": "Mercado", "amount": -800.0 - mes * 20,
                       "category": "Mercado"})
        linhas.append({"date": pd.Timestamp(2026, mes, 15),
                       "description": "iFood", "amount": -300.0,
                       "category": "Alimentação"})
    return pd.DataFrame(linhas)


def test_monthly_cashflow():
    cf = analytics.monthly_cashflow(_historico())
    assert len(cf) == 6
    assert (cf["receitas"] == 5000.0).all()
    assert (cf["saldo"] > 0).all()


def test_forecast_cashflow_gera_previsao():
    fc = forecast.forecast_cashflow(_historico(), months=3)
    previsto = fc[fc["tipo"] == "previsto"]
    assert len(previsto) == 3
    assert (previsto["despesas"] >= 0).all()
    assert (previsto["receitas"] >= 0).all()


def test_projected_balance_cresce_com_saldo_positivo():
    pb = forecast.projected_balance(_historico(), months=3)
    assert len(pb) == 3
    # saldo mensal positivo -> saldo projetado crescente
    assert pb["saldo_projetado"].is_monotonic_increasing


def test_forecast_by_category():
    fcat = forecast.forecast_by_category(_historico())
    assert set(["category", "previsto_mensal"]).issubset(fcat.columns)
    assert (fcat["previsto_mensal"] >= 0).all()


def test_linear_forecast_poucos_pontos():
    # menos de 3 pontos -> usa a média
    out = forecast._linear_forecast(np.array([100.0, 200.0]), 3)
    assert np.allclose(out, 150.0)
