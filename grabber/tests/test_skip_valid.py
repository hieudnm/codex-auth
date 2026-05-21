import base64
import json
import time
from pathlib import Path

from grabber.grab import has_valid_existing_output


def _make_token(exp_unix: int) -> str:
    payload = {"exp": exp_unix}
    payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return f"header.{payload_b64}.sig"


def _write_auth(path: Path, exp_unix: int):
    path.write_text(json.dumps({"access_token": _make_token(exp_unix)}), encoding="utf-8")


def test_returns_true_when_token_not_expired(tmp_path):
    out = tmp_path / "codex-x.json"
    _write_auth(out, int(time.time()) + 3600)   # +1h
    assert has_valid_existing_output(out) is True


def test_returns_false_when_token_expired(tmp_path):
    out = tmp_path / "codex-x.json"
    _write_auth(out, int(time.time()) - 100)
    assert has_valid_existing_output(out) is False


def test_returns_false_when_file_missing(tmp_path):
    assert has_valid_existing_output(tmp_path / "nope.json") is False


def test_returns_false_when_no_exp_claim(tmp_path):
    out = tmp_path / "codex-x.json"
    out.write_text(json.dumps({"access_token": "garbage"}), encoding="utf-8")
    assert has_valid_existing_output(out) is False
