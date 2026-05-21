import base64
import json
import asyncio
from typing import Tuple, Dict, Any

import httpx
from Crypto.Cipher import AES
from google.protobuf import json_format, message

from ff_proto import freefire_pb2

MAIN_KEY_B64 = "WWcmdGMlREV1aDYlWmNeOA=="
MAIN_IV_B64 = "Nm95WkRyMjJFM3ljaGpNJQ=="
RELEASE_VERSION = "OB51"
USER_AGENT = "GarenaMSDK/4.0.19P10(I2404 ;Android 15;en;US;)"
OAUTH_URL = "https://ffmconnect.live.gop.garenanow.com/api/v2/oauth/guest/token:grant"
MAJOR_LOGIN_URL = "https://loginbp.ggwhitehawk.com/MajorLogin"
CLIENT_SECRET_PAYLOAD = "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3&client_id=100067"
X_UNITY_VERSION = "2018.4.11f1"
TIMEOUT = 10.0

MAIN_KEY = base64.b64decode(MAIN_KEY_B64)
MAIN_IV = base64.b64decode(MAIN_IV_B64)


def pkcs7_pad(b: bytes, block_size: int = 16) -> bytes:
    pad_len = block_size - (len(b) % block_size)
    return b + bytes([pad_len]) * pad_len


def aes_cbc_encrypt(key: bytes, iv: bytes, plaintext: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return cipher.encrypt(pkcs7_pad(plaintext, 16))


def json_to_proto(json_data: Dict[str, Any], proto_message: message.Message) -> bytes:
    json_format.ParseDict(json_data, proto_message)
    return proto_message.SerializeToString()


async def get_access_token(client: httpx.AsyncClient, uid: str, password: str) -> Tuple[str, str]:
    parts = CLIENT_SECRET_PAYLOAD.split('&client_id=')
    client_secret = parts[0]
    client_id = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 100067

    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "client_type": 2,
        "password": password,
        "response_type": "token",
        "uid": int(uid),
    }

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
    }

    response = await client.post(OAUTH_URL, json=payload, headers=headers, timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json().get("data", {})

    if "error" in data:
        raise RuntimeError(f"Garena API Error: {data.get('error_description', data['error'])}")

    return data.get("access_token", "0"), data.get("open_id", "0")


async def create_jwt_async(uid: str, password: str) -> Dict[str, str]:
    async with httpx.AsyncClient(http2=False) as client:
        access_token, open_id = await get_access_token(client, uid, password)
        if access_token == "0":
            raise RuntimeError("Failed to obtain access token.")

        login_req = {
            "open_id": open_id,
            "open_id_type": "4",
            "login_token": access_token,
            "orign_platform_type": "4",
        }

        req_msg = freefire_pb2.LoginReq()
        encoded = json_to_proto(login_req, req_msg)
        encrypted_payload = aes_cbc_encrypt(MAIN_KEY, MAIN_IV, encoded)

        headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 15; I2404 Build/AP3A.240905.015.A2_V000L1)",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip",
            "Content-Type": "application/octet-stream",
            "Expect": "100-continue",
            "X-Unity-Version": X_UNITY_VERSION,
            "X-GA": "v1 1",
            "ReleaseVersion": RELEASE_VERSION,
        }

        response = await client.post(MAJOR_LOGIN_URL, content=encrypted_payload, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()

        res_msg = freefire_pb2.LoginRes()
        res_msg.ParseFromString(response.content)

        token = res_msg.token or "0"
        if token == "0":
            res_dict = json.loads(json_format.MessageToJson(res_msg))
            raise RuntimeError(f"Failed to obtain JWT. Response details: {res_dict}")

        return {
            "token": token,
            "lockRegion": res_msg.lock_region or "",
            "serverUrl": res_msg.server_url or "",
        }


def create_jwt(uid: str, password: str) -> Dict[str, str]:
    return asyncio.run(create_jwt_async(uid, password))
