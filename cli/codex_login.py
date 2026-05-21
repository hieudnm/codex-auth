"""
Codex CLI OAuth PKCE login - tạo file auth.json hợp lệ.

Cách dùng:
    python codex_login.py

Sẽ mở trình duyệt để đăng nhập ChatGPT (Google/Email/...),
sau đó tự động ghi file ./auth.json đúng chuẩn của Codex CLI.
"""

from __future__ import annotations

import base64
import hashlib
import http.server
import json
import os
import secrets
import socketserver
import threading
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

# ----- OAuth config (giống y hệt Codex CLI chính thức) -----
CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
ISSUER = "https://auth.openai.com"
REDIRECT_PORT = 1455
REDIRECT_PATH = "/auth/callback"
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}{REDIRECT_PATH}"
SCOPES = "openid profile email offline_access"
OUTPUT_FILE = Path(__file__).resolve().parent / "auth.json"


# ----- PKCE helpers -----
def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def make_pkce() -> tuple[str, str]:
    verifier = _b64url(secrets.token_bytes(64))
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


# ----- JWT decode (không verify, chỉ đọc payload để lấy account_id/email) -----
def decode_jwt_payload(token: str) -> dict:
    try:
        _, payload, _ = token.split(".")
        padded = payload + "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(padded))
    except Exception:
        return {}


# ----- Local callback server -----
class _CallbackHolder:
    code: str | None = None
    state: str | None = None
    error: str | None = None


class _Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args, **kwargs):  # tắt log mặc định
        pass

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != REDIRECT_PATH:
            self.send_response(404)
            self.end_headers()
            return

        params = urllib.parse.parse_qs(parsed.query)
        _CallbackHolder.code = (params.get("code") or [None])[0]
        _CallbackHolder.state = (params.get("state") or [None])[0]
        _CallbackHolder.error = (params.get("error") or [None])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        msg = (
            "<h2>Login thành công! Bạn có thể đóng tab này.</h2>"
            if _CallbackHolder.code
            else f"<h2>Login thất bại: {_CallbackHolder.error}</h2>"
        )
        self.wfile.write(msg.encode("utf-8"))


def wait_for_callback() -> None:
    with socketserver.TCPServer(("127.0.0.1", REDIRECT_PORT), _Handler) as httpd:
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        while _CallbackHolder.code is None and _CallbackHolder.error is None:
            pass
        httpd.shutdown()


# ----- Token exchange -----
def exchange_code(code: str, verifier: str) -> dict:
    body = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "code_verifier": verifier,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        f"{ISSUER}/oauth/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


# ----- Build auth.json -----
def build_auth_json(tokens: dict) -> dict:
    access_token = tokens["access_token"]
    id_token = tokens.get("id_token", "")
    refresh_token = tokens.get("refresh_token", "")

    at_payload = decode_jwt_payload(access_token)
    it_payload = decode_jwt_payload(id_token)

    chatgpt_auth = at_payload.get("https://api.openai.com/auth", {})
    account_id = chatgpt_auth.get("chatgpt_account_id") or it_payload.get(
        "https://api.openai.com/auth", {}
    ).get("chatgpt_account_id", "")

    email = it_payload.get("email") or at_payload.get(
        "https://api.openai.com/profile", {}
    ).get("email", "")

    exp = at_payload.get("exp")
    expired = (
        datetime.fromtimestamp(exp, tz=timezone.utc).astimezone().isoformat()
        if exp
        else ""
    )
    last_refresh = datetime.now(tz=timezone.utc).astimezone().isoformat()

    return {
        "access_token": access_token,
        "account_id": account_id,
        "disabled": False,
        "email": email,
        "expired": expired,
        "id_token": id_token,
        "last_refresh": last_refresh,
        "refresh_token": refresh_token,
        "type": "codex",
    }


# ----- Main flow -----
def main() -> None:
    verifier, challenge = make_pkce()
    state = secrets.token_urlsafe(32)

    auth_url = (
        f"{ISSUER}/oauth/authorize?"
        + urllib.parse.urlencode(
            {
                "response_type": "code",
                "client_id": CLIENT_ID,
                "redirect_uri": REDIRECT_URI,
                "scope": SCOPES,
                "code_challenge": challenge,
                "code_challenge_method": "S256",
                "state": state,
            }
        )
    )

    print(f"Mở trình duyệt: {auth_url}\n")
    webbrowser.open(auth_url)
    print(f"Đang chờ callback trên http://localhost:{REDIRECT_PORT} ...")
    wait_for_callback()

    if _CallbackHolder.error or not _CallbackHolder.code:
        raise SystemExit(f"OAuth lỗi: {_CallbackHolder.error}")
    if _CallbackHolder.state != state:
        raise SystemExit("State mismatch - có thể bị CSRF, hủy.")

    print("Nhận được code, đang đổi lấy token...")
    tokens = exchange_code(_CallbackHolder.code, verifier)

    auth_json = build_auth_json(tokens)
    OUTPUT_FILE.write_text(json.dumps(auth_json, indent=2), encoding="utf-8")
    print(f"\nĐã ghi {OUTPUT_FILE}")
    print(f"  email      : {auth_json['email']}")
    print(f"  account_id : {auth_json['account_id']}")
    print(f"  expired    : {auth_json['expired']}")


if __name__ == "__main__":
    main()
