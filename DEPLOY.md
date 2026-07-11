# 🚀 Hospedar na nuvem (acessar do celular, 24h)

Este guia deixa o app no ar de graça, acessível do celular de qualquer lugar,
protegido por **senha** e com **banco persistente** (os dados não se perdem).

> Stack: **Streamlit Community Cloud** (hospedagem grátis) + **Neon** (Postgres
> grátis). Leva ~15 minutos.

---

## 1. Criar o banco de dados (Neon — grátis)

1. Acesse **https://neon.tech** e crie uma conta (pode usar o GitHub).
2. Crie um projeto (região mais perto de você, ex: *AWS São Paulo*).
3. Em **Connection string**, copie a URL. Ela se parece com:
   ```
   postgresql://usuario:senha@ep-xxxx.sa-east-1.aws.neon.tech/neondb?sslmode=require
   ```
   Guarde essa string — é o seu `DATABASE_URL`.

## 2. Publicar o app (Streamlit Community Cloud — grátis)

1. Acesse **https://share.streamlit.io** e entre com o GitHub.
2. **New app** → **From existing repo**.
3. Preencha:
   - **Repository:** `guilhermeunflat/Kilombo-` (ou o repo `financeiro`, se já tiver migrado)
   - **Branch:** `claude/private-financial-repo-78zukq` (ou `main`, se já mesclado)
   - **Main file path:** `financeiro/app.py`
4. Abra **Advanced settings → Secrets** e cole (troque os valores):
   ```toml
   app_password = "uma-senha-forte-que-so-voces-sabem"
   DATABASE_URL = "postgresql://usuario:senha@ep-xxxx.sa-east-1.aws.neon.tech/neondb?sslmode=require"
   ```
5. **Deploy**. Em 1-2 min o app sobe numa URL tipo
   `https://seu-app.streamlit.app`.

## 3. Usar no celular

1. Abra a URL no navegador do celular e digite a **senha**.
2. **Adicione à tela de início** para virar um ícone (vira quase um app nativo):
   - **iPhone (Safari):** botão Compartilhar → *Adicionar à Tela de Início*.
   - **Android (Chrome):** menu ⋮ → *Adicionar à tela inicial*.

Pronto. Importe seus extratos pela aba **Importar** e tudo fica salvo no Postgres.

---

## Observações importantes

- **Privacidade:** neste modo os dados ficam num servidor (Streamlit + Neon), por
  isso o acesso é protegido por senha. Use uma senha forte e não a compartilhe.
  Mantenha o repositório **privado**.
- **Segredos nunca vão pro git:** o `secrets.toml` está no `.gitignore`. No
  Streamlit Cloud os segredos ficam no painel, não no código.
- **Dependências:** o Streamlit Cloud instala a partir de `financeiro/requirements.txt`.
  Se ele reclamar que não achou o arquivo, copie-o também para a raiz do repositório.
- **Rodar local continua funcionando:** sem `DATABASE_URL`, o app usa SQLite em
  `data/`; sem `app_password`, não pede senha. Ou seja, em casa é só
  `streamlit run app.py`.

## Alternativas de hospedagem

- **Render.com** / **Railway.app**: sobem o app com um volume persistente. Úteis
  se preferir SQLite em disco em vez de Postgres. Comando de start:
  `streamlit run financeiro/app.py --server.port $PORT --server.address 0.0.0.0`.
- **Fly.io**: parecido, com volume persistente para o `data/`.
