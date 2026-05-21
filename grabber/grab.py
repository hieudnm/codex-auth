"""CLI entry point: orchestrate đăng nhập + ghi auth.json cho từng account."""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from grabber.accounts import Account, parse_accounts, ParseError
from grabber.chatgpt_flow import grab_session
from grabber.convert import build_filename, convert
from grabber.errors import GrabError

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
DEFAULT_ACCOUNTS = ROOT / "accounts.txt"
PROFILES_DIR = ROOT / "profiles"
OUTPUT_DIR = ROOT / "output"
LOG_FILE = OUTPUT_DIR / "grab.log"


def setup_logging() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )


def process_one(account: Account, headless: bool) -> tuple[bool, str, float]:
    """Returns (success, message, elapsed_seconds)."""
    start = time.monotonic()
    profile = PROFILES_DIR / account.email
    try:
        session = grab_session(account, profile, headless=headless)
        auth = convert(session)
        plan = session.get("account", {}).get("planType", "unknown")
        filename = build_filename(auth["email"] or account.email, plan)
        out_path = OUTPUT_DIR / filename
        out_path.write_text(json.dumps(auth, indent=2), encoding="utf-8")
        elapsed = time.monotonic() - start
        return True, f"{filename}", elapsed
    except GrabError as e:
        elapsed = time.monotonic() - start
        return False, f"{e.code}: {e}", elapsed
    except Exception as e:
        elapsed = time.monotonic() - start
        logging.exception("[%s] unexpected error", account.email)
        return False, f"UNKNOWN: {e}", elapsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Auto-grab ChatGPT sessions → auth.json")
    parser.add_argument("--accounts", default=str(DEFAULT_ACCOUNTS), help="Path to accounts.txt")
    parser.add_argument("--only", help="Process only this email")
    parser.add_argument("--headless", action="store_true", help="Hide browser")
    args = parser.parse_args(argv)

    setup_logging()

    try:
        accounts = parse_accounts(args.accounts)
    except FileNotFoundError:
        print(f"ERROR: accounts file not found: {args.accounts}", file=sys.stderr)
        print(f"Copy {DEFAULT_ACCOUNTS.parent}/accounts.example.txt to accounts.txt and edit.", file=sys.stderr)
        return 1
    except ParseError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if args.only:
        accounts = [a for a in accounts if a.email == args.only]
        if not accounts:
            print(f"ERROR: no account with email '{args.only}'", file=sys.stderr)
            return 1

    print(f"\nProcessing {len(accounts)} account(s)...\n")
    total_start = time.monotonic()
    results: list[tuple[Account, bool, str, float]] = []

    for i, acc in enumerate(accounts, 1):
        prefix = f"[{i}/{len(accounts)}]"
        print(f"{prefix} ▶ {acc.email}", flush=True)
        ok, msg, dt = process_one(acc, headless=args.headless)
        mark = "✓" if ok else "✗"
        print(f"{prefix} {mark} {acc.email:<40} {msg}  ({dt:.1f}s)\n", flush=True)
        results.append((acc, ok, msg, dt))

    ok_count = sum(1 for _, o, _, _ in results if o)
    fail_count = len(results) - ok_count
    total = time.monotonic() - total_start
    print(f"\nSummary: {ok_count} ok, {fail_count} failed ({total:.1f}s total)")

    if fail_count:
        print("\nFailed details:")
        for acc, ok, msg, _ in results:
            if not ok:
                print(f"  {acc.email:<40} {msg}")

    return 0 if fail_count == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
