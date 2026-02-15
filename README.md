# Revemar · Preenchimento Automático de Documentos

Sistema para preencher automaticamente o Termo de Compromisso/Contrato de Adesão da Revemar/Honda com dados do cliente.

---

## Estrutura do Projeto

```
revemar-app/
├── backend/
│   ├── app.py              # Servidor Python (Flask)
│   └── requirements.txt    # Dependências Python
├── frontend/
│   └── index.html          # Interface web
├── render.yaml             # Configuração do Render (backend)
└── README.md
```

---

## Deploy Passo a Passo

### 1. Subir no GitHub

1. Acesse [github.com](https://github.com) e crie um repositório novo (ex: `revemar-app`)
2. No seu computador, abra o terminal na pasta do projeto e rode:

```bash
git init
git add .
git commit -m "primeiro commit"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/revemar-app.git
git push -u origin main
```

---

### 2. Deploy do Backend no Render (gratuito)

1. Acesse [render.com](https://render.com) e crie uma conta (pode entrar com GitHub)
2. Clique em **New → Web Service**
3. Conecte seu repositório GitHub (`revemar-app`)
4. Configure assim:
   - **Name:** `revemar-backend`
   - **Root Directory:** `backend`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
5. Clique em **Create Web Service**
6. Aguarde o deploy (2-3 minutos)
7. Copie a URL gerada (ex: `https://revemar-backend.onrender.com`)

> ⚠️ No plano gratuito do Render, o servidor "dorme" após 15 min sem uso.
> A primeira requisição pode demorar ~30 segundos para acordar. Isso é normal.

---

### 3. Deploy do Frontend no Vercel (gratuito)

**Opção A — Via GitHub (recomendado):**
1. Acesse [vercel.com](https://vercel.com) e crie uma conta com GitHub
2. Clique em **Add New → Project**
3. Importe o repositório `revemar-app`
4. Configure:
   - **Root Directory:** `frontend`
   - Deixe todo o resto como padrão
5. Clique em **Deploy**
6. Pronto! Você receberá uma URL como `https://revemar-app.vercel.app`

**Opção B — Simples (sem Vercel):**
- Você também pode hospedar o `index.html` no **GitHub Pages**:
  1. Vá em Settings do repositório → Pages
  2. Source: `main` branch, pasta `/frontend`
  3. URL gerada: `https://SEU_USUARIO.github.io/revemar-app`

---

### 4. Configurar o Site

1. Abra o site no navegador
2. No campo **URL do Backend**, cole a URL do Render:
   ```
   https://revemar-backend.onrender.com
   ```
3. Pronto! O site está funcionando.

---

## Como Usar

1. **Cole os dados do cliente** no campo de texto (copie direto do seu sistema)
2. **Faça upload do PDF** da empresa (ex: `COTAS_-_MOTOS.pdf`)
3. Clique em **Gerar e Baixar PDF**
4. O PDF preenchido será baixado automaticamente

---

## Adicionar Novos Templates

O sistema detecta automaticamente os campos fillable do PDF enviado.
Para funcionar corretamente com outros templates, os campos do PDF devem ter os mesmos IDs.

Se precisar suporte para outros templates, os campos são configurados no arquivo `backend/app.py` na função `parse_client_data`.

---

## Problemas Comuns

**"Failed to fetch" ou CORS error:**
- Verifique se a URL do backend está correta no campo de configuração
- Certifique-se que o serviço no Render está ativo (pode demorar ~30s para acordar)

**PDF gerado com campos em branco:**
- Verifique se os dados colados seguem o formato `Campo:\nVALOR`
- O sistema é case-insensitive para os nomes dos campos

**Erro no Render durante deploy:**
- Verifique se o `Root Directory` está configurado como `backend`
- Confira se o `requirements.txt` está dentro da pasta `backend`
