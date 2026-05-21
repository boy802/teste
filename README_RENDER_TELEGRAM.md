# Free Fire integrado para Render + Telegram

Este pacote junta:
- API de JWT: `/api/token`
- API de likes: `/like?uid=UID`
- Health check: `/health-check`
- Bot Telegram por webhook: `/telegram-webhook`

## Variáveis no Render

Configure em **Environment**:

```env
PUBLIC_URL=https://SEU-SERVICO.onrender.com
TELEGRAM_TOKEN=TOKEN_DO_BOTFATHER
TELEGRAM_CHAT_ID=SEU_CHAT_ID
BR_CONFIG=[{"uid":"SEU_UID","password":"SUA_SENHA"}]
IND_CONFIG=[{"uid":"SEU_UID","password":"SUA_SENHA"}]
EUROPE_CONFIG=[{"uid":"SEU_UID","password":"SUA_SENHA"}]
RELEASE_VERSION=OB51
```

Você pode deixar IND_CONFIG/EUROPE_CONFIG sem contas se for usar só BR, mas o `/health-check` pode aparecer como `degraded`.

## Deploy no Render

1. Envie estes arquivos para um repositório GitHub.
2. No Render: **New +** → **Web Service** → escolha o repo.
3. Build command:

```bash
pip install -r requirements.txt
```

4. Start command:

```bash
gunicorn wsgi:application --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 120
```

## Ativar webhook do Telegram

Depois que o Render estiver online, abra no navegador:

```text
https://api.telegram.org/botSEU_TOKEN/setWebhook?url=https://SEU-SERVICO.onrender.com/telegram-webhook
```

Teste:

```text
https://api.telegram.org/botSEU_TOKEN/getWebhookInfo
```

## Comandos do bot

```text
/start
/help
/status
/like 123456789
```

## Endpoints

```text
GET  /
GET  /render-info
GET  /health-check
GET  /like?uid=123456789
GET  /api/token?uid=UID&password=PASSWORD
POST /api/token  JSON: {"uid":"UID", "password":"PASSWORD"}
POST /telegram-webhook
```
