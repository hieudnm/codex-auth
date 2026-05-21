from pathlib import Path

import pytest

from grabber.accounts import Account, ParseError, parse_accounts


def write(tmp_path: Path, content: str) -> Path:
    f = tmp_path / "accounts.txt"
    f.write_text(content, encoding="utf-8")
    return f


def test_parses_basic_three_field(tmp_path):
    f = write(tmp_path, "a@b.com | pass1 | TOTPSECRET\n")
    accounts = parse_accounts(f)
    assert accounts == [Account(email="a@b.com", password="pass1", totp_secret="TOTPSECRET")]


def test_parses_two_field_no_totp(tmp_path):
    f = write(tmp_path, "nomfa@x.com | simple\n")
    accounts = parse_accounts(f)
    assert accounts == [Account(email="nomfa@x.com", password="simple", totp_secret=None)]


def test_trims_whitespace_around_pipes(tmp_path):
    f = write(tmp_path, "  a@b.com  |  pass  |  SECRET  \n")
    accounts = parse_accounts(f)
    assert accounts[0] == Account("a@b.com", "pass", "SECRET")


def test_skips_comments_and_blank_lines(tmp_path):
    f = write(tmp_path, "# header\n\na@b.com | p\n\n# tail\n")
    accounts = parse_accounts(f)
    assert len(accounts) == 1
    assert accounts[0].email == "a@b.com"


def test_escaped_pipe_in_password(tmp_path):
    f = write(tmp_path, r"a@b.com | pa\|ss | SEC" + "\n")
    accounts = parse_accounts(f)
    assert accounts[0].password == "pa|ss"


def test_duplicate_email_raises(tmp_path):
    f = write(tmp_path, "a@b.com | p1\na@b.com | p2\n")
    with pytest.raises(ParseError, match="duplicate"):
        parse_accounts(f)


def test_invalid_line_raises_with_line_number(tmp_path):
    f = write(tmp_path, "a@b.com | p\nbroken-line-no-pipe\n")
    with pytest.raises(ParseError, match="line 2"):
        parse_accounts(f)


def test_missing_email_raises(tmp_path):
    f = write(tmp_path, " | pass | SEC\n")
    with pytest.raises(ParseError, match="email"):
        parse_accounts(f)


def test_missing_password_raises(tmp_path):
    f = write(tmp_path, "a@b.com |  | SEC\n")
    with pytest.raises(ParseError, match="password"):
        parse_accounts(f)


def test_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        parse_accounts(tmp_path / "nonexistent.txt")
