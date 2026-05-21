"""Convert ChatGPT session JSON → Codex auth.json shape (9 fields)."""
from __future__ import annotations

import base64
import json
import re
from datetime import datetime, timezone


def decode_jwt_payload(token: str) -> dict:
    """Decode JWT middle segment. Returns {} on failure."""
    try:
        _, payload_b64, _ = token.split(".")
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        return json.loads(base64.urlsafe_b64decode(padded))
    except Exception:
        return {}


def _iso_from_unix(ts: int | float | None) -> str:
    if not ts:
        return ""
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone().isoformat()


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).astimezone().isoformat()


def convert(session: dict) -> dict:
    """Map session JSON → 9-field auth.json dict."""
    access_token = session.get("accessToken", "")
    payload = decode_jwt_payload(access_token)
    account = session.get("account") or {}
    user = session.get("user") or {}
    profile = payload.get("https://api.openai.com/profile") or {}

    return {
        "access_token": access_token,
        "account_id": account.get("id", ""),
        "disabled": False,
        "email": user.get("email") or profile.get("email", ""),
        "expired": _iso_from_unix(payload.get("exp")),
        "id_token": session.get("id_token", ""),
        "last_refresh": _now_iso(),
        "refresh_token": session.get("refresh_token", ""),
        "type": "codex",
    }


_WINDOWS_ILLEGAL = re.compile(r'[\\/:*?"<>|]')


def build_filename(email: str, plan: str) -> str:
    safe = _WINDOWS_ILLEGAL.sub("_", email) if email else "unknown"
    return f"codex-{safe}-{plan}.json"
