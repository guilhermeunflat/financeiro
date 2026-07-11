"""Gera um extrato de exemplo (sintético) com ~6 meses de transações.

Uso: python sample_data/gerar_exemplo.py
Cria sample_data/exemplo_extrato.csv — dados fictícios, só para testar o app.
Usa apenas a biblioteca padrão do Python.
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

RECORRENTES = [
    ("Salario Empresa XYZ", 7500.00, 1),
    ("Aluguel Imobiliaria Alfa", -2200.00, 5),
    ("Condominio Ed. Central", -650.00, 10),
    ("Enel Energia", -180.00, 12),
    ("Sabesp Agua", -95.00, 12),
    ("Vivo Internet", -120.00, 15),
    ("Netflix", -55.90, 8),
    ("Spotify", -21.90, 8),
    ("Plano de Saude Unimed", -480.00, 20),
]

VARIAVEIS = [
    ("iFood *Restaurante", -25, -90),
    ("Uber viagem", -12, -45),
    ("Supermercado Pao de Acucar", -80, -450),
    ("Posto Shell combustivel", -100, -320),
    ("Drogaria Drogasil", -20, -180),
    ("Amazon compra", -30, -400),
    ("Mercado Livre", -25, -350),
    ("Cinema Ingresso", -30, -120),
    ("Padaria da Esquina", -8, -40),
    ("Bar do Ze", -40, -160),
    ("Farmacia Pacheco", -15, -120),
    ("Estacionamento Shopping", -10, -35),
]


def gerar():
    hoje = date.today().replace(day=1)
    linhas = []
    for m in range(6, 0, -1):
        ano = hoje.year
        mes = hoje.month - m
        while mes <= 0:
            mes += 12
            ano -= 1
        # recorrentes
        for desc, valor, dia in RECORRENTES:
            try:
                d = date(ano, mes, dia)
            except ValueError:
                continue
            v = valor * random.uniform(0.98, 1.02) if valor < 0 else valor
            linhas.append((d, desc, round(v, 2)))
        # variáveis (10 a 25 por mês)
        for _ in range(random.randint(10, 25)):
            desc, lo, hi = random.choice(VARIAVEIS)
            dia = random.randint(1, 28)
            d = date(ano, mes, dia)
            v = round(random.uniform(lo, hi), 2)
            linhas.append((d, desc, v))

    linhas.sort(key=lambda x: x[0])
    out = Path(__file__).resolve().parent / "exemplo_extrato.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Data", "Descrição", "Valor"])
        for d, desc, v in linhas:
            w.writerow([d.strftime("%d/%m/%Y"), desc, f"{v:.2f}".replace(".", ",")])
    print(f"Gerado: {out} ({len(linhas)} transações)")


if __name__ == "__main__":
    gerar()
