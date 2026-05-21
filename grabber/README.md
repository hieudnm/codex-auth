# grabber — Auto session grabber

Đọc `accounts.txt`, login ChatGPT tự động bằng CloakBrowser (stealth Chromium), fetch `/api/auth/session`, ghi ra `output/codex-<email>-<plan>.json`.

## Setup

```powershell
# Từ project root
.\.venv\Scripts\Activate.ps1
pip install -r grabber/requirements.txt
python -m cloakbrowser install   # pre-download stealth Chromium ~200MB (1 lần)
```

## Cấu hình accounts

```powershell
cp grabber/accounts.example.txt grabber/accounts.txt
# Edit grabber/accounts.txt - mỗi dòng: email | password | totp_secret
```

`accounts.txt` đã được gitignored.

## Dùng

```powershell
# Tất cả account, sequential, có browser hiện ra (debug-friendly)
python -m grabber.grab

# Chỉ 1 account
python -m grabber.grab --only email@example.com

# Ẩn browser, 3 worker song song
python -m grabber.grab --headless --parallel 3

# Bỏ qua account đã có token chưa hết hạn
python -m grabber.grab --skip-valid

# Dùng accounts file khác
python -m grabber.grab --accounts /path/to/other.txt
```

## Output

```
grabber/output/
├── codex-<email>-<plan>.json     # 9-field auth.json
└── grab.log                       # timestamped log
```

## Error codes

| Code | Khi nào |
|---|---|
| `CAPTCHA_DETECTED` | Cloudflare/Turnstile/hCaptcha iframe xuất hiện |
| `CHALLENGE_PAGE` | URL chứa `/challenge/` hoặc `/cdn-cgi/challenge-platform` |
| `LOGIN_FAILED` | Sai password, hoặc redirect bất thường sau login |
| `MFA_FAILED` | TOTP code bị reject |
| `MFA_REQUIRED_NO_SECRET` | Có prompt MFA nhưng accounts.txt không cho secret |
| `NETWORK_ERROR` | Timeout, browser launch fail |
| `DOM_CHANGED` | Selector không match (OpenAI đổi UI) |
| `TIMEOUT` | Vượt 90s/account |

Mọi lỗi → skip account đó, log, tiếp tục account khác. Không retry.

## Limits

- Tối đa khuyến nghị `--parallel 5` (RAM ~280MB/instance, OpenAI rate limit).
- Profile cache trong `grabber/profiles/<email>/` — lần sau skip login nếu cookie còn hạn.
