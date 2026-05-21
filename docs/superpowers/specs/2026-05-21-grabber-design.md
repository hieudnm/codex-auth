# Grabber Module Design

**Date:** 2026-05-21
**Status:** Draft — pending user approval

## Goal

Tự động đọc danh sách account (email | password | TOTP secret) từ file, đăng nhập ChatGPT bằng CloakBrowser (stealth Chromium), lấy `/api/auth/session`, ghi ra file `codex-<email>-<plan>.json` cùng format với module `web/` và `cli/convert_session.py`.

Hoạt động độc lập với 2 module hiện có (`web/`, `cli/`). Có thể xóa `grabber/` mà 2 module kia vẫn chạy.

## Project structure

```
auth/
├── README.md                           # tổng quan + link 3 module
├── .gitignore                          # ignore secrets, profiles, output, venv
├── web/                                # module 1: convert UI
│   ├── index.html
│   └── README.md
├── cli/                                # module 2: CLI tools
│   ├── codex_login.py                  # OAuth PKCE login Codex CLI thật
│   ├── convert_session.py              # session JSON → auth.json
│   └── README.md
├── grabber/                            # module 3 (NEW)
│   ├── grab.py                         # entry point + CLI
│   ├── chatgpt_flow.py                 # login + fetch logic
│   ├── accounts.example.txt            # template
│   ├── accounts.txt                    # GITIGNORED - user's secrets
│   ├── profiles/                       # GITIGNORED - 1 folder per account
│   ├── output/                         # GITIGNORED - kết quả
│   │   ├── codex-<email>-<plan>.json   # auth.json format (9 fields)
│   │   └── grab.log                    # append-mode log
│   ├── requirements.txt                # cloakbrowser>=0.3.30, pyotp>=2.9
│   └── README.md
└── docs/superpowers/specs/             # design docs
```

Files cũ ở root (`codex_login.py`, `convert_session.py`, `index.html`) sẽ di chuyển vào folder tương ứng. CloakBrowser cloned repo gitignored — không thuộc sản phẩm.

## accounts.txt format

```
# Format: email | password | totp_secret
# - totp_secret optional (omit nếu account không bật 2FA)
# - khoảng trắng quanh `|` được trim
# - dòng bắt đầu # là comment, dòng trống bị skip
# - email duy nhất trong file (làm key cho profiles/<email>/)
# - password chứa `|` thì escape thành \|

hieu.daonhuminh@gmail.com | mypassword | UMKRI7F6YYQJIR44MR2CZXLHFFQJMYFC
work@company.com | another_pass | XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
no_mfa@example.com | simple_pass
```

## CLI

```
python grab.py                          # process all in accounts.txt, sequential, headed
python grab.py --only EMAIL             # chỉ chạy 1 account (test/debug)
python grab.py --headless               # ẩn browser - chạy nhanh hơn
python grab.py --parallel N             # N worker đồng thời (default 1, recommend 3)
python grab.py --skip-valid             # bỏ qua account đã có output token chưa hết hạn
python grab.py --accounts PATH          # dùng file accounts khác
```

**Default behavior:** sequential + headed. Ưu tiên debug-friendly cho lần chạy đầu. Khi đã ổn định thì user pass `--headless --parallel 3`.

## Login flow (per account)

```
1. Launch CloakBrowser persistent context tại profiles/<email>/
   ├─ humanize=True
   ├─ headless theo --headless flag
   └─ Nếu profile đã có cookie valid → BỎ QUA bước 2-7
2. Fast path: GET https://chatgpt.com/api/auth/session
   └─ Nếu response có "user" + "accessToken" → đã login, sang bước 9
3. Shortcut entry: navigate tới https://chatgpt.com/auth/login
   (skip homepage, tiết kiệm ~1.5s)
4. Fill email vào input[type='email']
   Click button name="Continue" exact=True  (TRÁNH "Continue with Google")
5. Sau redirect tới auth.openai.com/log-in/password:
   Fill password vào input[type='password']
   Click button[type='submit']
6. Nếu redirect tới auth.openai.com/mfa-challenge/<id>:
   Generate code = pyotp.TOTP(totp_secret).now()
   Fill vào input[autocomplete*='one-time']
   Click button name="Continue" exact=True
7. Đợi redirect về chatgpt.com/
8. GET /api/auth/session → parse JSON
9. Convert sang auth.json format (cùng logic web UI: 9 fields)
10. Ghi output/codex-<safe-email>-<plan>.json
11. Close browser → profile saved cho lần sau
```

### Confirmed selectors (validated qua test thật 2026-05-21)

| Step | Selector | Notes |
|---|---|---|
| Email input | `input[type='email']` | Trên trang chatgpt.com login dialog |
| Continue (after email) | `get_by_role("button", name="Continue", exact=True)` | EXACT để tránh match "Continue with Google" |
| Password input | `input[type='password']` | Trên auth.openai.com/log-in/password |
| Password submit | `button[type='submit']` | Hoặc cùng pattern Continue exact |
| MFA code input | `input[autocomplete*='one-time']` | Trên auth.openai.com/mfa-challenge/ |
| MFA submit | `get_by_role("button", name="Continue", exact=True)` | |

### Confirmed URL patterns

| Stage | URL pattern |
|---|---|
| Login entry shortcut | `https://chatgpt.com/auth/login` |
| Password page | `https://auth.openai.com/log-in/password` |
| MFA page | `https://auth.openai.com/mfa-challenge/<id>` |
| Success redirect | `https://chatgpt.com/` |
| Session endpoint | `https://chatgpt.com/api/auth/session` |
| Cloudflare error | `https://chatgpt.com/api/auth/error` + title "Just a moment..." |

## Output JSON format

Cùng 9 field như module `web/` và `cli/convert_session.py`:

```json
{
  "access_token": "<from session.accessToken>",
  "account_id": "<from session.account.id>",
  "disabled": false,
  "email": "<from session.user.email>",
  "expired": "<ISO from JWT exp claim>",
  "id_token": "",
  "last_refresh": "<ISO now()>",
  "refresh_token": "",
  "type": "codex"
}
```

Filename: `codex-<safe-email>-<plan>.json` (sanitize Windows-illegal chars `\ / : * ? " < > |` thành `_`, giữ nguyên `@` và `.`).

## Error handling — "Skip & log"

**Mọi lỗi đều skip account đó, log rồi tiếp tục account khác. Không retry, không crash batch.**

| Lỗi | Detect | Status code |
|---|---|---|
| `CAPTCHA_DETECTED` | iframe `challenges.cloudflare.com` hoặc `turnstile` hoặc `hcaptcha`; hoặc URL chứa `/challenge/`, hoặc title "Just a moment" | skip + log |
| `LOGIN_FAILED` | Server hiển thị error message sau password (sai pass, account locked) | skip + log |
| `MFA_FAILED` | URL vẫn ở `/mfa-challenge/` sau khi submit code | skip + log |
| `MFA_REQUIRED_NO_SECRET` | Hit `/mfa-challenge/` nhưng accounts.txt không cho TOTP secret | skip + log |
| `NETWORK_ERROR` | Playwright timeout/exception trên goto/fetch | skip + log |
| `DOM_CHANGED` | Selector không match sau N giây (OpenAI đổi UI) | skip + log |
| `TIMEOUT` | Account vượt hard limit 90s | skip + log |
| `UNKNOWN` | Exception khác | skip + log với stacktrace |

### Detection của Cloudflare (chạy trước mỗi step quan trọng)

```python
def has_cloudflare_challenge(page) -> bool:
    if "Just a moment" in page.title():
        return True
    if "/challenge/" in page.url or "/api/auth/error" in page.url:
        return True
    iframes = page.evaluate("() => Array.from(document.querySelectorAll('iframe')).map(f => f.src)")
    return any("cloudflare.com" in src or "turnstile" in src or "hcaptcha" in src for src in iframes)
```

## Concurrency design

Async + Semaphore, default sequential.

```python
async def main(accounts, concurrency):
    sem = asyncio.Semaphore(concurrency)
    async def worker(acc):
        async with sem:
            await asyncio.sleep(random.uniform(0, 1.5))  # stagger
            return await grab_one(acc)
    return await asyncio.gather(*[worker(a) for a in accounts], return_exceptions=True)
```

| Setting | Value |
|---|---|
| Default `--parallel` | 1 |
| Recommended | 3 |
| Max safe | 5-8 |
| Stagger | random 0-1.5s mỗi worker start |
| Per-account timeout | 90s hard limit |

Mỗi account 1 `user_data_dir` riêng → cookie isolated, không race condition.

## Logging

- **Console:** progress real-time, prefix `[i/N]` và email
- **File:** `output/grab.log` append-mode, có timestamp, thread-safe qua `logging.FileHandler`
- **Format console:**
  ```
  [1/8] ▶ start  hieu@gmail.com
  [2/8] ▶ start  work@company.com
  [1/8] ✓ done   hieu@gmail.com         plus  (12.4s)
  [2/8] ✗ fail   work@company.com       CAPTCHA  (8.1s)
  ...
  Summary: 6 ok, 2 failed (45.3s total)
  ```

## Dependencies

`grabber/requirements.txt`:
```
cloakbrowser>=0.3.30
pyotp>=2.9.0
```

Setup:
```powershell
cd grabber
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m cloakbrowser install   # pre-download stealth Chromium ~200MB
```

## Out of scope (YAGNI cho v1)

- Proxy support per account (CloakBrowser hỗ trợ nhưng v1 không expose flag)
- Retry mechanism (skip & log đủ cho v1)
- Web UI cho grabber (giữ CLI thuần)
- Raw session JSON archive (chỉ lưu auth.json convert sẵn)
- Account labels/tags/groups
- Schedule cron built-in (dùng Windows Task Scheduler / cron OS)

## Testing strategy

Có module `tests/` đơn giản với:
1. **Unit test `convert.py`** (logic JSON → auth.json) — vì pure function, dễ test với fixture
2. **Integration test smoke** — chạy `grab.py --only <test-account>` trên 1 account thật, check file output xuất hiện và có đúng 9 field
3. **Parse accounts.txt unit test** — test edge case: comment, dòng trống, password có ký tự đặc biệt, thiếu TOTP

Không test full login automation tự động (phụ thuộc OpenAI API, fragile). Manual run trên test account khi cập nhật selector.

## Migration path

Bước 1 — Restructure (không ảnh hưởng functionality):
```
mv index.html              → web/index.html
mv codex_login.py          → cli/codex_login.py
mv convert_session.py      → cli/convert_session.py
mv test_input.json         → samples/test_input.json
mv codex-*-*.json          → samples/ (hoặc xóa)
xóa explore_login.py       (đã hoàn thành mục đích)
```

Bước 2 — Tạo `grabber/`:
```
mkdir grabber/{profiles,output}
viết grabber/grab.py + grabber/chatgpt_flow.py
viết grabber/accounts.example.txt + grabber/README.md
viết grabber/requirements.txt
```

Bước 3 — Update `.gitignore`:
```
.venv/
CloakBrowser/
grabber/accounts.txt
grabber/profiles/
grabber/output/
docs/debug/
*.pyc
__pycache__/
```

Bước 4 — Update root `README.md` để link 3 module.
