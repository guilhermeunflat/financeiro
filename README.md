# 💰 Controle Financeiro Pessoal

App local para importar extratos, categorizar gastos, visualizar em gráficos e
**prever** os próximos meses com base no histórico. Tudo roda na sua máquina —
nenhum dado financeiro sai do seu computador.

## O que ele faz

- **Importa extratos** dos últimos meses em **OFX, CSV ou Excel** (Nubank, Inter,
  Itaú, Bradesco, etc.), com detecção automática de colunas e formato de número
  brasileiro (`1.234,56`). Transações repetidas são ignoradas em reimports.
- **Categoriza automaticamente** por regras (estabelecimentos comuns no Brasil) e
  **aprende com as suas correções** — quanto mais você ajusta, melhor ele acerta.
- **Dashboard** com receitas × despesas por mês, gastos por categoria, saldo
  acumulado e maiores despesas.
- **Previsões**: projeta despesas, receitas e saldo dos próximos meses, e o gasto
  previsto por categoria.

## Como rodar

```bash
cd financeiro
python3 -m venv .venv && source .venv/bin/activate   # opcional, recomendado
pip install -r requirements.txt
streamlit run app.py
```

O app abre no navegador (geralmente em http://localhost:8501).

### Usar no celular / hospedar na nuvem

Para acessar do celular de qualquer lugar (24h, com senha e banco persistente),
veja o passo a passo em **[DEPLOY.md](DEPLOY.md)** — Streamlit Cloud + Postgres,
tudo grátis.

### Testar com dados de exemplo

Já existe um extrato fictício em `sample_data/exemplo_extrato.csv` (6 meses).
Na aba **Importar extratos**, envie esse arquivo para ver tudo funcionando.
Para gerar um novo: `python sample_data/gerar_exemplo.py`.

## Fluxo de uso

1. **Importar extratos** → envie os arquivos dos últimos ~6 meses e salve.
2. **Transações** → clique em *Categorizar automaticamente*; corrija o que
   estiver errado e salve (o app aprende com isso).
3. **Dashboard** → interprete os gráficos.
4. **Previsões** → veja a projeção dos próximos meses.

## Privacidade

- Os dados ficam só em `data/financeiro.db`, na sua máquina.
- A pasta `data/` e qualquer `.ofx/.csv/.xlsx` são **ignorados pelo git** (ver
  `.gitignore`) — seus extratos nunca vão parar no repositório.

## Estrutura

```
financeiro/
├── app.py                 # interface (Streamlit)
├── finance/
│   ├── importers.py       # leitura de OFX/CSV/Excel
│   ├── categorize.py      # regras + aprendizado (ML)
│   ├── analytics.py       # agregações dos gráficos
│   ├── forecast.py        # previsões
│   └── storage.py         # banco local (SQLite)
├── sample_data/           # extrato de exemplo (fictício)
├── tests/                 # testes automatizados (pytest)
└── requirements.txt
```

## Testes

```bash
python -m pytest tests/ -q
```

## Formato dos extratos

- **OFX**: funciona direto (padrão bancário).
- **CSV/Excel**: o app detecta as colunas de *data*, *descrição* e *valor*
  (ou *débito/crédito*). Se o seu banco exporta despesas como valores
  **positivos** (comum em faturas de cartão), marque *"Inverter sinal"* na
  importação.
