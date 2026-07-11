"""Importação de extratos bancários.

Suporta OFX (padrão bancário) e planilhas CSV/Excel de bancos brasileiros
(Nubank, Inter, Itaú, Bradesco, etc.), com detecção automática de colunas e
formato de número brasileiro (1.234,56).

Convenção de sinal: valores negativos = saída (despesa); positivos = entrada
(receita). Alguns bancos exportam despesas como positivas — nesse caso use o
parâmetro ``invert`` para inverter o sinal na importação.
"""

from __future__ import annotations

import io
import re

import pandas as pd

# ---------------------------------------------------------------------------
# Normalização de valores e datas
# ---------------------------------------------------------------------------

def to_float(value) -> float | None:
    """Converte texto monetário para float, entendendo formato BR e US."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if s == "" or s.lower() in {"nan", "none"}:
        return None
    s = s.replace("R$", "").replace(" ", "").replace("\xa0", "")
    neg = s.startswith("-") or s.startswith("(")
    s = s.replace("(", "").replace(")", "").lstrip("+-")
    if "," in s and "." in s:
        # 1.234,56 -> ponto é milhar, vírgula é decimal
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        f = float(s)
    except ValueError:
        return None
    return -f if neg else f


def _parse_dates(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, dayfirst=True, errors="coerce")


# ---------------------------------------------------------------------------
# OFX
# ---------------------------------------------------------------------------

def _ofx_tag(block: str, tag: str) -> str | None:
    m = re.search(rf"<{tag}>([^<\r\n]*)", block, re.IGNORECASE)
    return m.group(1).strip() if m else None


def parse_ofx(text: str) -> pd.DataFrame:
    """Extrai transações de um extrato OFX."""
    account = _ofx_tag(text, "ACCTID") or ""
    blocks = re.findall(r"<STMTTRN>(.*?)</STMTTRN>", text, re.DOTALL | re.IGNORECASE)
    if not blocks:
        blocks = re.split(r"<STMTTRN>", text, flags=re.IGNORECASE)[1:]

    rows = []
    for b in blocks:
        raw_date = _ofx_tag(b, "DTPOSTED")
        amount = to_float(_ofx_tag(b, "TRNAMT"))
        name = _ofx_tag(b, "NAME") or ""
        memo = _ofx_tag(b, "MEMO") or ""
        if raw_date is None or amount is None:
            continue
        date = pd.to_datetime(raw_date[:8], format="%Y%m%d", errors="coerce")
        if pd.isna(date):
            continue
        desc = (name + " " + memo).strip() or name or memo
        rows.append({"date": date, "description": desc, "amount": amount,
                     "account": account})
    return pd.DataFrame(rows, columns=["date", "description", "amount", "account"])


# ---------------------------------------------------------------------------
# CSV / Excel
# ---------------------------------------------------------------------------

_DATE_NAMES = ["data", "date", "data lançamento", "data lancamento",
               "data da compra", "data do lançamento", "dt"]
_DESC_NAMES = ["descrição", "descricao", "histórico", "historico", "lançamento",
               "lancamento", "estabelecimento", "memo", "description", "title",
               "detalhe", "detalhes", "movimentação", "movimentacao"]
_AMOUNT_NAMES = ["valor", "amount", "value", "valor (r$)", "montante", "valor r$"]
_DEBIT_NAMES = ["débito", "debito", "saída", "saida", "debit"]
_CREDIT_NAMES = ["crédito", "credito", "entrada", "credit"]


def _find_col(cols: dict[str, str], candidates: list[str]) -> str | None:
    # match exato primeiro
    for cand in candidates:
        if cand in cols:
            return cols[cand]
    # match por conteúdo (coluna que contém o termo)
    for cand in candidates:
        for low, orig in cols.items():
            if cand in low:
                return orig
    return None


def parse_tabular(df_raw: pd.DataFrame, invert: bool = False) -> pd.DataFrame:
    """Normaliza uma planilha genérica de extrato em colunas padrão."""
    if df_raw.empty:
        return pd.DataFrame(columns=["date", "description", "amount", "account"])

    cols = {str(c).lower().strip(): c for c in df_raw.columns}
    date_col = _find_col(cols, _DATE_NAMES)
    desc_col = _find_col(cols, _DESC_NAMES)
    amount_col = _find_col(cols, _AMOUNT_NAMES)
    debit_col = _find_col(cols, _DEBIT_NAMES)
    credit_col = _find_col(cols, _CREDIT_NAMES)

    if date_col is None:
        raise ValueError(
            "Não encontrei uma coluna de data. Colunas disponíveis: "
            + ", ".join(str(c) for c in df_raw.columns)
        )

    out = pd.DataFrame()
    out["date"] = _parse_dates(df_raw[date_col])
    out["description"] = (df_raw[desc_col].astype(str) if desc_col else "").fillna("")

    if amount_col is not None:
        out["amount"] = df_raw[amount_col].map(to_float)
    elif debit_col is not None or credit_col is not None:
        debit = df_raw[debit_col].map(to_float).fillna(0) if debit_col else 0
        credit = df_raw[credit_col].map(to_float).fillna(0) if credit_col else 0
        # débito é saída (negativo), crédito é entrada (positivo)
        out["amount"] = credit.abs() - debit.abs()
    else:
        raise ValueError(
            "Não encontrei coluna(s) de valor. Colunas: "
            + ", ".join(str(c) for c in df_raw.columns)
        )

    out["account"] = ""
    out = out.dropna(subset=["date", "amount"])
    if invert:
        out["amount"] = -out["amount"]
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Dispatch por tipo de arquivo
# ---------------------------------------------------------------------------

def load_file(filename: str, data: bytes, invert: bool = False) -> pd.DataFrame:
    """Lê um arquivo de extrato (bytes) e devolve o DataFrame normalizado.

    ``filename`` é usado só para descobrir a extensão e registrar a origem.
    """
    name = filename.lower()
    if name.endswith(".ofx"):
        text = data.decode("latin-1", errors="ignore")
        df = parse_ofx(text)
        if invert:
            df["amount"] = -df["amount"]
    elif name.endswith((".xlsx", ".xls")):
        df = parse_tabular(pd.read_excel(io.BytesIO(data)), invert=invert)
    elif name.endswith(".csv"):
        df = _read_csv_flexible(data)
        df = parse_tabular(df, invert=invert)
    else:
        raise ValueError(f"Formato não suportado: {filename} (use OFX, CSV ou Excel)")

    df["source_file"] = filename
    df["category"] = None
    return df


def _read_csv_flexible(data: bytes) -> pd.DataFrame:
    """Lê CSV tentando separadores e encodings comuns em bancos BR."""
    text = None
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        text = data.decode("latin-1", errors="ignore")

    # detecta separador pela primeira linha
    first = text.splitlines()[0] if text.splitlines() else ""
    sep = ";" if first.count(";") >= first.count(",") else ","
    return pd.read_csv(io.StringIO(text), sep=sep)
