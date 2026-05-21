"""
Convert session JSON (chatgpt.com) -> file kiểu codex-<id>-<plan>.json.

CẢNH BÁO: output KHÔNG dùng được để login Codex CLI thật vì:
  - accessToken thuộc client_id ChatGPT Web (app_X8zY...), không phải Codex.
  - Không có id_token và refresh_token.
Script chỉ làm shape mapping để demo / nghiên cứu cấu trúc.

Cách dùng:
    python convert_session.py test_input.json
"""

from __future__ import annotations

import base64
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def decode_jwt_payload(token: str) -> dict:
    try:
        _, payload, _ = token.split(".")
        padded = payload + "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(padded))
    except Exception:
        return {}


def convert(session: dict) -> tuple[dict, str]:
    access_token = session.get("accessToken", "")
    payload = decode_jwt_payload(access_token)

    account = session.get("account") or {}
    user = session.get("user") or {}

    account_id = account.get("id", "")
    plan = account.get("planType", "unknown")
    email = user.get("email") or payload.get(
        "https://api.openai.com/profile", {}
    ).get("email", "")

    exp = payload.get("exp")
    expired = (
        datetime.fromtimestamp(exp, tz=timezone.utc).astimezone().isoformat()
        if exp
        else ""
    )
    last_refresh = datetime.now(tz=timezone.utc).astimezone().isoformat()

    out = {
        "access_token": access_token,
        "account_id": account_id,
        "disabled": False,
        "email": email,
        "expired": expired,
        "id_token": "",          # KHÔNG CÓ trong input -> để rỗng
        "last_refresh": last_refresh,
        "refresh_token": "",     # KHÔNG CÓ trong input -> để rỗng
        "type": "codex",
    }

    import re
    safe_email = re.sub(r'[\\/:*?"<>|]', "_", email) if email else "unknown"
    filename = f"codex-{safe_email}-{plan}.json"
    return out, filename


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        print("Usage: python convert_session.py <input.json>")
        sys.exit(1)

    src = Path(argv[1])
    session = json.loads(src.read_text(encoding="utf-8"))
    out, filename = convert(session)

    out_path = src.parent / filename
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(f"Đã ghi: {out_path}")
    print(f"  email      : {out['email']}")
    print(f"  account_id : {out['account_id']}")
    print(f"  expired    : {out['expired']}")
    print()
    print("Kiểm tra hợp lệ cho Codex CLI:")

    payload = decode_jwt_payload(out["access_token"])
    client_id = payload.get("client_id", "")
    scopes = payload.get("scp", [])

    codex_client = "app_EMoamEEZ73f0CkXaXp7hrann"
    ok_client = client_id == codex_client
    ok_refresh = bool(out["refresh_token"])
    ok_id = bool(out["id_token"])

    print(f"  client_id  : {client_id}")
    print(f"             -> {'OK' if ok_client else f'SAI (cần {codex_client})'}")
    print(f"  scopes     : {scopes}")
    print(f"  refresh_token: {'CÓ' if ok_refresh else 'THIẾU'}")
    print(f"  id_token   : {'CÓ' if ok_id else 'THIẾU'}")
    print()
    if not (ok_client and ok_refresh and ok_id):
        print("=> File KHÔNG dùng được để login Codex CLI thật.")
        print("   Phải chạy codex_login.py để OAuth chuẩn.")


if __name__ == "__main__":
    main(sys.argv)
