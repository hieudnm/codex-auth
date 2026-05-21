# grabber — Auto session grabber (planning)

🚧 **Trạng thái:** Design done, chưa implement.

Xem thiết kế chi tiết: [`../docs/superpowers/specs/2026-05-21-grabber-design.md`](../docs/superpowers/specs/2026-05-21-grabber-design.md)

## Tóm tắt

Đọc `accounts.txt` (định dạng `email | password | totp_secret`), tự động:
1. Login ChatGPT bằng CloakBrowser stealth (pass Cloudflare Turnstile)
2. Generate TOTP code qua `pyotp` nếu MFA bật
3. Fetch `/api/auth/session`
4. Convert sang `auth.json` format
5. Ghi `output/codex-<email>-<plan>.json`

## CLI (kế hoạch)

```powershell
python grab.py                          # all accounts, sequential, headed
python grab.py --only EMAIL             # 1 account
python grab.py --headless               # ẩn browser
python grab.py --parallel N             # N worker song song
python grab.py --skip-valid             # bỏ qua account đã có token chưa hết hạn
```

## Dependencies (kế hoạch)

```
cloakbrowser>=0.3.30
pyotp>=2.9.0
```
