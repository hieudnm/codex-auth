# cli — Python tools

## `codex_login.py`
OAuth PKCE login chính thức cho Codex CLI. Mở browser → đăng nhập ChatGPT Plus → ghi `./auth.json` dùng được thật.

```powershell
python codex_login.py
```

## `convert_session.py`
Convert session JSON từ `chatgpt.com/api/auth/session` sang shape `auth.json`.

```powershell
python convert_session.py path/to/session.json
# → tạo codex-<email>-<plan>.json cùng folder
```

⚠️ Output từ `convert_session.py` **không login được Codex CLI** vì token thuộc client_id khác. Chỉ dùng để demo / nghiên cứu cấu trúc.
