import pandas as pd

from finance import categorize


def test_regras_basicas():
    assert categorize.categorize_by_rules("iFood *Restaurante") == "Alimentação"
    assert categorize.categorize_by_rules("UBER viagem") == "Transporte"
    assert categorize.categorize_by_rules("NETFLIX.COM") == "Assinaturas"
    assert categorize.categorize_by_rules("Supermercado Extra") == "Mercado"


def test_regras_sem_acento_e_caixa():
    # deve casar mesmo sem acento e em maiúsculas
    assert categorize.categorize_by_rules("FARMACIA PACHECO") == "Saúde"


def test_regras_sem_match():
    assert categorize.categorize_by_rules("XPTO desconhecido 123") is None


def test_auto_categorize_preenche_outros():
    df = pd.DataFrame({
        "id": [1, 2],
        "description": ["iFood", "coisa aleatoria zzz"],
        "amount": [-30.0, -10.0],
        "category": [None, None],
        "manual": [0, 0],
    })
    out = categorize.auto_categorize(df)
    assert out.loc[0, "category"] == "Alimentação"
    # sem match e sem histórico -> Outros
    assert out.loc[1, "category"] == "Outros"


def test_ml_aprende_com_historico():
    # histórico rotulado à mão ensina o classificador
    treino = [("Mercadinho do Joao", "Mercado")] * 4 + \
             [("Cafe Central", "Alimentação")] * 4
    df = pd.DataFrame({
        "id": range(9),
        "description": [d for d, _ in treino] + ["Mercadinho da Maria"],
        "amount": [-10.0] * 9,
        "category": [c for _, c in treino] + [None],
        "manual": [1] * 8 + [0],
    })
    out = categorize.auto_categorize(df)
    # a transação nova, sem regra, deve herdar "Mercado" pelo aprendizado
    assert out.iloc[8]["category"] in {"Mercado", "Alimentação"}
