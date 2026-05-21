# codex-auth

Bộ công cụ tạo file `auth.json` chuẩn Codex CLI từ session ChatGPT. Gồm 3 module **độc lập**:

| Module | Mô tả | Trạng thái |
|---|---|---|
| [`web/`](web/) | Web UI paste session JSON → tải về `auth.json` (client-side, 100% browser) | ✅ Done |
| [`cli/`](cli/) | Python scripts: OAuth PKCE login Codex CLI thật + convert session JSON | ✅ Done |
| [`grabber/`](grabber/) | Auto-grabber: đọc `accounts.txt` → login tự động → ghi `auth.json` | ✅ Done |

Thiết kế chi tiết module `grabber/` ở [docs/superpowers/specs/2026-05-21-grabber-design.md](docs/superpowers/specs/2026-05-21-grabber-design.md).

## ⚠️ Cảnh báo: token ChatGPT Web ≠ token Codex CLI

Token từ `chatgpt.com/api/auth/session` (`client_id=app_X8zY...`) **KHÁC** token Codex CLI cần (`client_id=app_EMoamEEZ...`). Web UI và grabber chỉ map shape JSON, **KHÔNG tạo ra Codex auth.json dùng được thật**. Muốn token Codex thật → chạy `cli/codex_login.py` (OAuth PKCE chính thức).

## Quick start

### Module 1 — Web UI
Mở [`web/index.html`](web/index.html) trong browser. Paste session JSON → preview + download `codex-<email>-<plan>.json`.

### Module 2 — Codex login chuẩn
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python cli/codex_login.py
```
Mở browser, đăng nhập, script tự ghi `./auth.json` dùng được cho Codex CLI.

### Module 3 — Auto-grabber (sắp có)
```powershell
cd grabber
pip install -r requirements.txt
python grab.py                          # process all accounts in accounts.txt
python grab.py --parallel 3 --headless  # song song 3 worker, ẩn browser
```

## Cấu trúc

```
.
├── web/index.html                     # convert UI
├── cli/
│   ├── codex_login.py                 # OAuth PKCE login Codex CLI
│   └── convert_session.py             # session JSON → auth.json
├── grabber/                           # 🚧 auto-grabber (planned)
├── samples/                           # test inputs (gitignored)
└── docs/superpowers/specs/            # design docs
```

## Format output (auth.json)

9 field theo chuẩn Codex CLI:
```json
{
  "access_token": "eyJ...",
  "account_id": "...",
  "disabled": false,
  "email": "user@example.com",
  "expired": "2026-05-27T13:12:05+08:00",
  "id_token": "eyJ...",
  "last_refresh": "2026-05-17T13:12:05+08:00",
  "refresh_token": "rt_...",
  "type": "codex"
}
```
