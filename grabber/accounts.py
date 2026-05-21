"""Parse accounts.txt → list[Account]."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Account:
    email: str
    password: str
    totp_secret: str | None = None


class ParseError(ValueError):
    """Invalid accounts.txt content."""


def _split_unescaped_pipes(line: str) -> list[str]:
    """Split by `|` but treat `\\|` as literal pipe."""
    parts: list[str] = []
    buf: list[str] = []
    i = 0
    while i < len(line):
        c = line[i]
        if c == "\\" and i + 1 < len(line) and line[i + 1] == "|":
            buf.append("|")
            i += 2
            continue
        if c == "|":
            parts.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(c)
        i += 1
    parts.append("".join(buf))
    return parts


def parse_accounts(path: str | Path) -> list[Account]:
    path = Path(path)
    text = path.read_text(encoding="utf-8")  # raises FileNotFoundError

    accounts: list[Account] = []
    seen_emails: set[str] = set()

    for lineno, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue

        parts = [p.strip() for p in _split_unescaped_pipes(raw)]
        if len(parts) < 2 or len(parts) > 3:
            raise ParseError(f"line {lineno}: expected 2 or 3 pipe-separated fields, got {len(parts)}")

        email = parts[0]
        password = parts[1]
        totp = parts[2] if len(parts) == 3 and parts[2] else None

        if not email:
            raise ParseError(f"line {lineno}: missing email")
        if not password:
            raise ParseError(f"line {lineno}: missing password")
        if email in seen_emails:
            raise ParseError(f"line {lineno}: duplicate email '{email}'")
        seen_emails.add(email)

        accounts.append(Account(email=email, password=password, totp_secret=totp))

    return accounts
