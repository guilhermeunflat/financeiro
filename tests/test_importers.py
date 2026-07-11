import pandas as pd
import pytest

from finance import importers


def test_to_float_formato_br():
    assert importers.to_float("1.234,56") == pytest.approx(1234.56)
    assert importers.to_float("-50,00") == pytest.approx(-50.0)
    assert importers.to_float("R$ 2.000,00") == pytest.approx(2000.0)
    assert importers.to_float("(75,50)") == pytest.approx(-75.50)


def test_to_float_formato_us():
    assert importers.to_float("1234.56") == pytest.approx(1234.56)
    assert importers.to_float(-12.5) == pytest.approx(-12.5)


def test_to_float_vazio():
    assert importers.to_float("") is None
    assert importers.to_float(None) is None


def test_parse_tabular_colunas_basicas():
    raw = pd.DataFrame({
        "Data": ["01/03/2026", "05/03/2026"],
        "Descrição": ["iFood", "Salario"],
        "Valor": ["-50,00", "3.000,00"],
    })
    out = importers.parse_tabular(raw)
    assert list(out.columns) == ["date", "description", "amount", "account"]
    assert out.loc[0, "amount"] == pytest.approx(-50.0)
    assert out.loc[1, "amount"] == pytest.approx(3000.0)


def test_parse_tabular_debito_credito():
    raw = pd.DataFrame({
        "data": ["01/03/2026"],
        "historico": ["compra"],
        "debito": ["100,00"],
        "credito": [""],
    })
    out = importers.parse_tabular(raw)
    assert out.loc[0, "amount"] == pytest.approx(-100.0)


def test_parse_tabular_invert():
    raw = pd.DataFrame({
        "Data": ["01/03/2026"], "Descrição": ["cartao"], "Valor": ["50,00"],
    })
    out = importers.parse_tabular(raw, invert=True)
    assert out.loc[0, "amount"] == pytest.approx(-50.0)


def test_parse_ofx():
    ofx = """
    <OFX><BANKACCTFROM><ACCTID>12345</ACCTID></BANKACCTFROM>
    <STMTTRN><TRNTYPE>DEBIT<DTPOSTED>20260315120000<TRNAMT>-42.50
    <NAME>UBER<MEMO>viagem</STMTTRN>
    <STMTTRN><TRNTYPE>CREDIT<DTPOSTED>20260301<TRNAMT>3000.00
    <NAME>SALARIO</STMTTRN></OFX>
    """
    out = importers.parse_ofx(ofx)
    assert len(out) == 2
    assert out.loc[0, "amount"] == pytest.approx(-42.5)
    assert "UBER" in out.loc[0, "description"]
    assert out.loc[0, "account"] == "12345"


def test_parse_tabular_sem_data_erro():
    raw = pd.DataFrame({"x": [1], "Valor": ["10,00"]})
    with pytest.raises(ValueError):
        importers.parse_tabular(raw)


def test_parse_pdf_line_debito_credito():
    # marcador D/C define o sinal
    rec = importers._parse_pdf_line("15/03/2026 PAGAMENTO UBER 42,50 D")
    assert rec is not None
    assert rec["amount"] == pytest.approx(-42.50)
    assert "UBER" in rec["description"]

    rec2 = importers._parse_pdf_line("01/03/2026 SALARIO EMPRESA 3.000,00 C")
    assert rec2["amount"] == pytest.approx(3000.0)


def test_parse_pdf_line_valor_negativo():
    rec = importers._parse_pdf_line("10/02/2026 COMPRA MERCADO -150,00")
    assert rec["amount"] == pytest.approx(-150.0)


def test_parse_pdf_line_sem_data_ou_valor():
    assert importers._parse_pdf_line("linha qualquer sem nada") is None
    assert importers._parse_pdf_line("15/03/2026 sem valor aqui") is None


def test_table_looks_like_extrato():
    assert importers._table_looks_like_extrato(["Data", "Histórico", "Valor"])
    assert not importers._table_looks_like_extrato(["Coluna A", "Coluna B"])
