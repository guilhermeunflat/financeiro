"""Persistência das transações.

Funciona em dois modos, sem mudar o resto do app:

- **Local** (padrão): SQLite em ``data/financeiro.db``, na sua máquina.
- **Nuvem**: qualquer banco via ``DATABASE_URL`` (ex: Postgres do Neon/Supabase),
  lido de variável de ambiente ou de ``st.secrets``. Necessário quando o app roda
  hospedado, para os dados não se perderem a cada reinício.

A API pública (init_db, insert_transactions, get_transactions, ...) é a mesma
nos dois modos.
"""

from __future__ import annotations

import hashlib
import os
from functools import lru_cache
from pathlib import Path

import pandas as pd
from sqlalchemy import (Column, Float, Integer, MetaData, String, Table, Text,
                        create_engine, delete, select, update)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "financeiro.db"

metadata = MetaData()
transactions = Table(
    "transactions", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("hash", String(64), unique=True),
    Column("date", String(32), nullable=False),
    Column("description", Text),
    Column("amount", Float, nullable=False),
    Column("category", String(64)),
    Column("account", String(128)),
    Column("source_file", String(256)),
    Column("manual", Integer, default=0),
)


def _normalize_url(url: str) -> str:
    # provedores às vezes entregam "postgres://" — SQLAlchemy quer "postgresql://"
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        try:
            import streamlit as st
            if "DATABASE_URL" in st.secrets:
                url = st.secrets["DATABASE_URL"]
        except Exception:  # noqa: BLE001 - streamlit ausente ou sem secrets
            url = None
    if url:
        return _normalize_url(url)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DB_PATH}"


@lru_cache(maxsize=1)
def get_engine():
    return create_engine(_database_url(), pool_pre_ping=True)


def init_db() -> None:
    """Cria a tabela de transações se ainda não existir."""
    metadata.create_all(get_engine())


def row_hash(date: str, description: str, amount: float, account: str) -> str:
    """Chave única de uma transação (evita duplicatas em reimports)."""
    key = f"{date}|{(description or '').strip().lower()}|{amount:.2f}|{account or ''}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def insert_transactions(df: pd.DataFrame) -> int:
    """Insere transações novas, ignorando duplicatas. Retorna quantas entraram."""
    if df is None or df.empty:
        return 0

    init_db()
    engine = get_engine()

    # descobre o que já existe (escala pessoal: carregar os hashes é barato)
    with engine.connect() as conn:
        existentes = {r[0] for r in conn.execute(select(transactions.c.hash))}

    novos = []
    vistos = set()
    for _, r in df.iterrows():
        date = str(r["date"])
        desc = str(r.get("description", "") or "")
        amount = float(r["amount"])
        account = str(r.get("account", "") or "")
        h = row_hash(date, desc, amount, account)
        if h in existentes or h in vistos:
            continue
        vistos.add(h)
        category = r.get("category")
        category = None if pd.isna(category) else category
        novos.append({
            "hash": h, "date": date, "description": desc, "amount": amount,
            "category": category, "account": account,
            "source_file": str(r.get("source_file", "") or ""), "manual": 0,
        })

    if novos:
        with engine.begin() as conn:
            conn.execute(transactions.insert(), novos)
    return len(novos)


def get_transactions() -> pd.DataFrame:
    """Retorna todas as transações como DataFrame (date convertida)."""
    init_db()
    df = pd.read_sql(select(transactions).order_by(transactions.c.date),
                     get_engine())
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
        df = df.dropna(subset=["date", "amount"])
    return df


def update_category(txn_id: int, category: str, manual: bool = True) -> None:
    with get_engine().begin() as conn:
        conn.execute(
            update(transactions)
            .where(transactions.c.id == int(txn_id))
            .values(category=category, manual=1 if manual else 0)
        )


def bulk_update_categories(updates: dict[int, str], manual: bool = False) -> None:
    """Aplica várias categorizações de uma vez. ``updates`` = {id: categoria}."""
    if not updates:
        return
    with get_engine().begin() as conn:
        for tid, cat in updates.items():
            conn.execute(
                update(transactions)
                .where(transactions.c.id == int(tid))
                .values(category=cat, manual=1 if manual else 0)
            )


def delete_all() -> None:
    """Apaga todas as transações (usar com cuidado)."""
    with get_engine().begin() as conn:
        conn.execute(delete(transactions))
