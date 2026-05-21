from flask import Flask, request, jsonify
import os
import logging

from .token_manager import TokenCache
from .like_routes import like_bp, initialize_routes
from .telegram_bot import initialize_telegram
from .jwt_service import create_jwt
from . import like_routes

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SERVERS = {
    "EUROPE": os.getenv("EUROPE_SERVER", "https://clientbp.ggblueshark.com"),
    "IND": os.getenv("IND_SERVER", "https://client.ind.freefiremobile.com"),
    "BR": os.getenv("BR_SERVER", "https://client.us.freefiremobile.com"),
}

token_cache = TokenCache(servers_config=SERVERS)

@app.before_request
def handle_chunking():
    transfer_encoding = request.headers.get("Transfer-Encoding", "")
    if "chunked" in transfer_encoding.lower():
        request.environ["wsgi.input_terminated"] = True

@app.route("/api/token", methods=["GET", "POST"])
def api_token():
    try:
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            uid = str(data.get("uid", "")).strip()
            password = str(data.get("password", "")).strip()
        else:
            uid = str(request.args.get("uid", "")).strip()
            password = str(request.args.get("password", "")).strip()

        if not uid or not password:
            return jsonify({"error": "uid e password são obrigatórios"}), 400
        if not uid.isdigit():
            return jsonify({"error": "uid precisa ser numérico"}), 400

        return jsonify(create_jwt(uid, password))
    except Exception as exc:
        logger.exception("Erro ao gerar JWT")
        return jsonify({"error": str(exc)}), 500

@app.route("/render-info", methods=["GET"])
def render_info():
    public_url = os.getenv("PUBLIC_URL") or os.getenv("RENDER_EXTERNAL_URL") or ""
    return jsonify({
        "ok": True,
        "service": "freefire-integrado-render",
        "endpoints": {
            "home": "/",
            "like": "/like?uid=UID",
            "jwt_get": "/api/token?uid=UID&password=PASSWORD",
            "jwt_post": "/api/token",
            "health": "/health-check",
            "telegram_webhook": "/telegram-webhook",
            "set_telegram_webhook": f"https://api.telegram.org/botSEU_TOKEN/setWebhook?url={public_url}/telegram-webhook" if public_url else "configure PUBLIC_URL primeiro",
        }
    })

initialize_routes(app, SERVERS, token_cache)
initialize_telegram(app, SERVERS, token_cache, like_routes)
