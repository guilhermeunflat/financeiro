"""Categorização de transações.

Duas camadas:

1. **Regras** — palavras-chave de estabelecimentos comuns no Brasil. Rápido e
   sem precisar de dados prévios.
2. **Aprendizado (ML)** — treina um classificador com as transações que você
   corrigiu à mão e passa a sugerir categorias sozinho. Quanto mais você
   corrige, melhor ele fica.
"""

from __future__ import annotations

import re
import unicodedata

import pandas as pd

# Categorias padrão
CATEGORIES = [
    "Alimentação", "Mercado", "Transporte", "Moradia", "Contas & Serviços",
    "Saúde", "Lazer", "Assinaturas", "Compras", "Educação", "Viagem",
    "Renda", "Investimentos", "Transferências", "Impostos & Tarifas", "Outros",
]

# Regras: categoria -> lista de palavras-chave (sem acento, minúsculas)
RULES: dict[str, list[str]] = {
    "Alimentação": ["ifood", "rappi", "restaurante", "lanchonete", "padaria",
                     "burger", "mcdonald", "bk ", "subway", "pizza", "cafe",
                     "bar ", "boteco", "food", "resto"],
    "Mercado": ["supermercado", "mercado", "atacadao", "assai", "carrefour",
                "pao de acucar", "extra", "hortifruti", "sacolao", "big ",
                "mercadinho", "zona sul", "guanabara"],
    "Transporte": ["uber", "99", "99app", "cabify", "posto", "shell", "ipiranga",
                   "petrobras", "combustivel", "estacionamento", "pedagio",
                   "metro", "onibus", "bilhete unico", "gasolina"],
    "Moradia": ["aluguel", "condominio", "imobiliaria", "financiamento imovel"],
    "Contas & Serviços": ["energia", "enel", "light", "cemig", "copel", "sabesp",
                          "agua", "gas ", "vivo", "claro", "tim", "oi ", "internet",
                          "telefonia", "conta de luz"],
    "Saúde": ["farmacia", "drogaria", "droga raia", "drogasil", "pacheco",
              "hospital", "clinica", "laboratorio", "dentista", "medico",
              "unimed", "amil", "plano de saude"],
    "Lazer": ["cinema", "ingresso", "show", "teatro", "parque", "bar",
              "balada", "game", "steam", "playstation", "xbox"],
    "Assinaturas": ["netflix", "spotify", "amazon prime", "disney", "hbo", "max ",
                    "youtube premium", "google one", "icloud", "apple.com",
                    "globoplay", "deezer", "chatgpt", "openai"],
    "Compras": ["amazon", "mercado livre", "mercadolivre", "shopee", "aliexpress",
                "magalu", "magazine luiza", "americanas", "casas bahia", "shein",
                "renner", "riachuelo", "zara", "loja"],
    "Educação": ["escola", "faculdade", "universidade", "curso", "udemy", "alura",
                 "colegio", "mensalidade", "livraria"],
    "Viagem": ["latam", "gol ", "azul", "hotel", "airbnb", "booking", "decolar",
               "passagem", "cvc", "hostel"],
    "Renda": ["salario", "pagamento", "provento", "pro-labore", "rendimento",
              "credito em conta", "deposito"],
    "Investimentos": ["aplicacao", "tesouro", "cdb", "fundo", "corretora", "xp ",
                      "rico", "nuinvest", "b3 ", "acoes", "resgate"],
    "Transferências": ["pix", "ted", "doc", "transferencia", "transf "],
    "Impostos & Tarifas": ["tarifa", "iof", "juros", "imposto", "das ", "darf",
                          "anuidade", "multa", "encargo"],
}


def _norm(text: str) -> str:
    """Minúsculas, sem acento — pra casar palavras-chave de forma robusta."""
    text = (text or "").lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text)


def categorize_by_rules(description: str) -> str | None:
    """Retorna a categoria por palavra-chave, ou None se nada casar."""
    desc = _norm(description)
    for category, keywords in RULES.items():
        for kw in keywords:
            if kw in desc:
                return category
    return None


def apply_rules(df: pd.DataFrame) -> pd.Series:
    """Aplica as regras à coluna ``description`` e devolve as categorias."""
    return df["description"].map(categorize_by_rules)


# ---------------------------------------------------------------------------
# Aprendizado: classificador treinado nas correções do usuário
# ---------------------------------------------------------------------------

class MLCategorizer:
    """Classificador de texto (TF-IDF + Naive Bayes) treinado no histórico."""

    def __init__(self) -> None:
        self.model = None
        self.trained = False

    def train(self, df: pd.DataFrame) -> int:
        """Treina com transações já categorizadas. Retorna nº de exemplos usados."""
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.naive_bayes import MultinomialNB
        from sklearn.pipeline import Pipeline

        labeled = df[df["category"].notna() & (df["category"] != "")]
        # precisa de pelo menos 2 categorias distintas e alguns exemplos
        if labeled["category"].nunique() < 2 or len(labeled) < 6:
            self.trained = False
            return len(labeled)

        X = labeled["description"].fillna("").map(_norm)
        y = labeled["category"]
        self.model = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
            ("clf", MultinomialNB()),
        ])
        self.model.fit(X, y)
        self.trained = True
        return len(labeled)

    def predict(self, descriptions: pd.Series) -> list[str] | None:
        if not self.trained or self.model is None:
            return None
        return list(self.model.predict(descriptions.fillna("").map(_norm)))


def auto_categorize(df: pd.DataFrame) -> pd.DataFrame:
    """Preenche categorias vazias: primeiro por regras, depois por ML.

    Não sobrescreve categorias definidas manualmente (coluna ``manual`` == 1).
    Retorna o DataFrame com a coluna ``category`` atualizada.
    """
    df = df.copy()
    if "manual" not in df.columns:
        df["manual"] = 0

    # 1) regras nas que estão sem categoria
    mask_empty = df["category"].isna() | (df["category"] == "")
    df.loc[mask_empty, "category"] = df.loc[mask_empty, "description"].map(
        categorize_by_rules
    )

    # 2) ML nas que sobraram sem categoria
    ml = MLCategorizer()
    ml.train(df)
    if ml.trained:
        still_empty = df["category"].isna() | (df["category"] == "")
        if still_empty.any():
            preds = ml.predict(df.loc[still_empty, "description"])
            if preds is not None:
                df.loc[still_empty, "category"] = preds

    # 3) o que sobrar vira "Outros"
    df["category"] = df["category"].fillna("Outros").replace("", "Outros")
    return df
