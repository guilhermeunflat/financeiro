"""Controle Financeiro Pessoal — app local (Streamlit).

Rode com:  streamlit run app.py

Tudo roda na sua máquina. Os dados ficam em ./data/financeiro.db e nunca são
enviados pra lugar nenhum.
"""

from __future__ import annotations

import hmac
import os

import pandas as pd
import plotly.express as px
import streamlit as st

from finance import analytics, categorize, forecast, storage

st.set_page_config(page_title="Controle Financeiro", page_icon="💰",
                   layout="wide")


def moeda(v: float) -> str:
    return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _senha_configurada() -> str | None:
    """Senha de acesso, vinda de st.secrets ou da env APP_PASSWORD."""
    try:
        if "app_password" in st.secrets:
            return st.secrets["app_password"]
    except Exception:  # noqa: BLE001 - sem arquivo de secrets (uso local)
        pass
    return os.environ.get("APP_PASSWORD")


def require_login() -> None:
    """Bloqueia o app atrás de uma senha quando ela estiver configurada.

    Sem senha configurada (uso local), o acesso é livre.
    """
    senha = _senha_configurada()
    if not senha:
        return
    if st.session_state.get("_auth_ok"):
        return

    st.title("🔒 Acesso restrito")
    entered = st.text_input("Senha", type="password")
    if st.button("Entrar", type="primary"):
        if hmac.compare_digest(entered, senha):
            st.session_state["_auth_ok"] = True
            st.rerun()
        else:
            st.error("Senha incorreta.")
    st.stop()


require_login()
storage.init_db()

st.sidebar.title("💰 Financeiro")
pagina = st.sidebar.radio(
    "Navegação",
    ["Importar extratos", "Transações", "Dashboard", "Previsões"],
)

df_all = storage.get_transactions()
if not df_all.empty:
    st.sidebar.caption(
        f"{len(df_all)} transações · "
        f"{df_all['date'].min():%b/%Y} → {df_all['date'].max():%b/%Y}"
    )


# ---------------------------------------------------------------------------
# 1. Importar
# ---------------------------------------------------------------------------
if pagina == "Importar extratos":
    st.header("Importar extratos")
    st.write("Envie os extratos dos últimos meses (OFX, CSV, Excel ou PDF). "
             "Transações repetidas são ignoradas automaticamente.")
    st.caption("💡 OFX e CSV são os mais confiáveis. O PDF funciona por melhor "
               "esforço (o layout varia por banco) — confira a prévia antes de salvar.")

    invert = st.checkbox(
        "Inverter sinal dos valores",
        help="Marque se o seu banco exporta despesas como valores positivos "
             "(comum em faturas de cartão).",
    )
    files = st.file_uploader(
        "Arquivos de extrato", type=["ofx", "csv", "xlsx", "xls", "pdf"],
        accept_multiple_files=True,
    )

    if files and st.button(f"Processar e salvar {len(files)} arquivo(s)",
                           type="primary"):
        import gc

        from finance import importers

        prog = st.progress(0.0, text="Processando...")
        total_novos = 0
        resumo = []
        # um arquivo por vez: lê, categoriza, salva e libera a memória.
        # Evita estourar a RAM ao importar vários PDFs de uma vez.
        for i, f in enumerate(files, start=1):
            try:
                df = importers.load_file(f.name, f.getvalue(), invert=invert)
                df["category"] = categorize.apply_rules(df)
                inseridos = storage.insert_transactions(df)
                total_novos += inseridos
                resumo.append({"arquivo": f.name, "lidas": len(df),
                               "novas": inseridos, "status": "ok"})
            except Exception as e:  # noqa: BLE001
                resumo.append({"arquivo": f.name, "lidas": 0, "novas": 0,
                               "status": f"erro: {e}"})
            finally:
                df = None
                gc.collect()
                prog.progress(i / len(files),
                              text=f"Processando... ({i}/{len(files)})")

        prog.empty()
        st.success(f"Concluído: {total_novos} transações novas salvas.")
        st.dataframe(pd.DataFrame(resumo), use_container_width=True,
                     hide_index=True)
        st.info("Abra a aba **Transações** para categorizar e revisar, "
                "ou o **Dashboard** para ver os gráficos.")

    if files:
        st.caption(f"{len(files)} arquivo(s) selecionado(s). "
                   "Dica: se o app travar com muitos PDFs de uma vez, "
                   "importe em lotes menores (3–4 por vez).")


# ---------------------------------------------------------------------------
# 2. Transações
# ---------------------------------------------------------------------------
elif pagina == "Transações":
    st.header("Transações")
    if df_all.empty:
        st.info("Nenhuma transação ainda. Importe seus extratos primeiro.")
    else:
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("🤖 Categorizar automaticamente (regras + aprendizado)"):
                cat = categorize.auto_categorize(df_all)
                updates = {int(r.id): r.category for r in cat.itertuples()}
                storage.bulk_update_categories(updates, manual=False)
                st.success("Categorias atualizadas.")
                st.rerun()
        with col2:
            st.caption("Edite a categoria na tabela e clique em salvar — o app "
                       "aprende com suas correções.")

        edit_df = df_all[["id", "date", "description", "amount", "category"]].copy()
        edited = st.data_editor(
            edit_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": st.column_config.NumberColumn("id", disabled=True),
                "date": st.column_config.DateColumn("Data", disabled=True),
                "description": st.column_config.TextColumn("Descrição",
                                                           disabled=True),
                "amount": st.column_config.NumberColumn("Valor", format="R$ %.2f",
                                                        disabled=True),
                "category": st.column_config.SelectboxColumn(
                    "Categoria", options=categorize.CATEGORIES),
            },
            key="editor",
        )
        if st.button("💾 Salvar correções", type="primary"):
            merged = edit_df.merge(edited[["id", "category"]], on="id",
                                   suffixes=("_old", ""))
            changed = merged[merged["category"] != merged["category_old"]]
            updates = {int(r.id): r.category for r in changed.itertuples()
                       if pd.notna(r.category)}
            storage.bulk_update_categories(updates, manual=True)
            st.success(f"{len(updates)} correções salvas. O aprendizado usará "
                       "elas na próxima categorização automática.")
            st.rerun()


# ---------------------------------------------------------------------------
# 3. Dashboard
# ---------------------------------------------------------------------------
elif pagina == "Dashboard":
    st.header("Dashboard")
    if df_all.empty:
        st.info("Importe e categorize seus extratos para ver os gráficos.")
    else:
        k = analytics.kpis(df_all)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Receitas", moeda(k["receitas"]))
        c2.metric("Despesas", moeda(k["despesas"]))
        c3.metric("Saldo", moeda(k["saldo"]))
        c4.metric("Média de despesa/mês", moeda(k["media_despesa_mensal"]))

        cf = analytics.monthly_cashflow(df_all)
        fig = px.bar(cf, x="month", y=["receitas", "despesas"], barmode="group",
                     title="Receitas x Despesas por mês",
                     labels={"value": "R$", "month": "Mês", "variable": ""},
                     color_discrete_map={"receitas": "#2e9e5b",
                                         "despesas": "#d64545"})
        st.plotly_chart(fig, use_container_width=True)

        col_a, col_b = st.columns(2)
        with col_a:
            cat = analytics.expenses_by_category(df_all)
            fig2 = px.pie(cat, values="total", names="category", hole=0.45,
                          title="Despesas por categoria")
            st.plotly_chart(fig2, use_container_width=True)
        with col_b:
            bal = analytics.balance_series(df_all)
            fig3 = px.area(bal, x="date", y="saldo_acumulado",
                           title="Saldo acumulado no tempo",
                           labels={"saldo_acumulado": "R$", "date": ""})
            st.plotly_chart(fig3, use_container_width=True)

        cbm = analytics.category_by_month(df_all)
        fig4 = px.bar(cbm, x="month", y="total", color="category",
                      title="Composição das despesas por mês",
                      labels={"total": "R$", "month": "Mês"})
        st.plotly_chart(fig4, use_container_width=True)

        st.subheader("Maiores despesas")
        st.dataframe(analytics.top_expenses(df_all, 10), use_container_width=True,
                     hide_index=True)


# ---------------------------------------------------------------------------
# 4. Previsões
# ---------------------------------------------------------------------------
elif pagina == "Previsões":
    st.header("Previsões")
    if df_all.empty or df_all["date"].dt.to_period("M").nunique() < 2:
        st.info("Preciso de pelo menos 2 meses de histórico para prever. "
                "Importe mais extratos.")
    else:
        meses = st.slider("Meses a prever", 1, 6, 3)
        fc = forecast.forecast_cashflow(df_all, meses)

        fig = px.line(fc, x="month", y="despesas", color="tipo", markers=True,
                      title="Despesas: histórico e previsão",
                      labels={"despesas": "R$", "month": "Mês", "tipo": ""})
        st.plotly_chart(fig, use_container_width=True)

        pb = forecast.projected_balance(df_all, meses)
        prox = fc[fc["tipo"] == "previsto"]

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Fluxo previsto")
            tab = prox[["month", "receitas", "despesas", "saldo"]].copy()
            tab["month"] = tab["month"].dt.strftime("%b/%Y")
            for col in ["receitas", "despesas", "saldo"]:
                tab[col] = tab[col].map(moeda)
            st.dataframe(tab, use_container_width=True, hide_index=True)
        with c2:
            st.subheader("Saldo projetado")
            pb_show = pb.copy()
            pb_show["month"] = pb_show["month"].dt.strftime("%b/%Y")
            pb_show["saldo_projetado"] = pb_show["saldo_projetado"].map(moeda)
            st.dataframe(pb_show, use_container_width=True, hide_index=True)

        st.subheader("Previsão de gasto por categoria (próximo mês)")
        fcat = forecast.forecast_by_category(df_all)
        fig2 = px.bar(fcat, x="previsto_mensal", y="category", orientation="h",
                      title="Gasto mensal previsto por categoria",
                      labels={"previsto_mensal": "R$", "category": ""})
        fig2.update_yaxes(categoryorder="total ascending")
        st.plotly_chart(fig2, use_container_width=True)
