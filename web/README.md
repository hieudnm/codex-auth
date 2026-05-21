# web — Convert UI

Single-page web app để paste session JSON từ ChatGPT và tải về file `auth.json`.

## Dùng

Mở `index.html` trong browser (Chrome/Edge/Firefox). Paste JSON vào textarea → preview + download.

## Features

- Live preview thông tin account (email, plan badge, hết hạn, MFA, IdP, JTI)
- 5 check tự động: client_id, plan, refresh_token, id_token, access_token còn hạn
- Drag & drop file `.json`
- Phím tắt: `Ctrl+S` tải, `Ctrl+K` clear
- Dark theme, glass-morphism, fully responsive
- 100% client-side: token KHÔNG rời khỏi browser

## Limitation

Vì input là session ChatGPT Web (`client_id=app_X8zY...`), output JSON sẽ có `client_id` SAI cho Codex CLI và thiếu `refresh_token` + `id_token`. Codex CLI sẽ reject file này. Để có file login được thật → chạy `../cli/codex_login.py`.
