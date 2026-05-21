import os
import asyncio
import logging
import requests
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)
telegram_bp = Blueprint("telegram_bp", __name__)

_SERVERS = {}
_token_cache = None
_like_module = None


def _telegram_token():
    return os.getenv("TELEGRAM_TOKEN", "").strip()


def _allowed_chat_id():
    return str(os.getenv("TELEGRAM_CHAT_ID", os.getenv("CHAT_ID", ""))).strip()


def send_message(chat_id, text):
    token = _telegram_token()
    if not token:
        logger.warning("TELEGRAM_TOKEN não configurado")
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=10,
        )
        if resp.status_code >= 400:
            logger.warning("Erro Telegram: %s %s", resp.status_code, resp.text)
        return resp.ok
    except Exception as exc:
        logger.exception("Falha ao enviar mensagem Telegram: %s", exc)
        return False


async def _do_like(uid: str):
    region, player_info = await _like_module.detect_player_region(uid)
    if not player_info:
        return None

    before_likes = player_info.AccountInfo.Likes
    player_name = player_info.AccountInfo.PlayerNickname
    await _like_module.send_likes(uid, region)

    tokens = _token_cache.get_tokens(region)
    after_likes = before_likes
    if tokens:
        info_url = f"{_SERVERS[region]}/GetPlayerPersonalShow"
        new_info = _like_module.make_request(_like_module.encode_uid(uid), info_url, tokens[0])
        after_likes = new_info.AccountInfo.Likes if new_info else before_likes

    return {
        "player": player_name,
        "uid": uid,
        "region": region,
        "before": before_likes,
        "after": after_likes,
        "added": after_likes - before_likes,
    }


@telegram_bp.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    update = request.get_json(silent=True) or {}
    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}
    chat_id = str(chat.get("id", ""))
    text = (message.get("text") or "").strip()

    allowed = _allowed_chat_id()
    if allowed and chat_id != allowed:
        send_message(chat_id, "Acesso não autorizado para este bot.")
        return jsonify({"ok": True})

    if not text or text in ("/start", "/help"):
        send_message(chat_id, "✅ Bot online.\n\nComandos:\n/like UID\n/status")
        return jsonify({"ok": True})

    if text.startswith("/status"):
        status = []
        for server in _SERVERS:
            tokens = _token_cache.get_tokens(server)
            status.append(f"{server}: {len(tokens)} token(s)")
        send_message(chat_id, "📊 Status dos tokens:\n" + "\n".join(status))
        return jsonify({"ok": True})

    if text.startswith("/like"):
        parts = text.split()
        if len(parts) < 2 or not parts[1].isdigit():
            send_message(chat_id, "Use assim: /like 123456789")
            return jsonify({"ok": True})
        uid = parts[1]
        try:
            result = asyncio.run(_do_like(uid))
            if not result:
                send_message(chat_id, "❌ Jogador não encontrado em nenhum servidor.")
            else:
                send_message(
                    chat_id,
                    "✅ Like finalizado\n"
                    f"Jogador: {result['player']}\n"
                    f"UID: {result['uid']}\n"
                    f"Região: {result['region']}\n"
                    f"Antes: {result['before']}\n"
                    f"Depois: {result['after']}\n"
                    f"Adicionados: {result['added']}",
                )
        except Exception as exc:
            logger.exception("Erro no /like")
            send_message(chat_id, f"❌ Erro: {exc}")
        return jsonify({"ok": True})

    send_message(chat_id, "Comando não reconhecido. Use /help")
    return jsonify({"ok": True})


def initialize_telegram(app_instance, servers_config, token_cache_instance, like_module):
    global _SERVERS, _token_cache, _like_module
    _SERVERS = servers_config
    _token_cache = token_cache_instance
    _like_module = like_module
    app_instance.register_blueprint(telegram_bp)
