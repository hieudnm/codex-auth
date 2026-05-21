from grabber.convert import build_filename, convert, decode_jwt_payload


def test_decode_jwt_extracts_payload():
    token = "eyJhbGciOiJSUzI1NiJ9.eyJleHAiOjk5OTk5OTk5OTksImNsaWVudF9pZCI6ImFwcF9YOHpZNnZXMnBROXRSM2RFN25LMWpMNWdIIiwiaHR0cHM6Ly9hcGkub3BlbmFpLmNvbS9wcm9maWxlIjp7ImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSJ9fQ.sig"
    payload = decode_jwt_payload(token)
    assert payload["exp"] == 9999999999
    assert payload["client_id"] == "app_X8zY6vW2pQ9tR3dE7nK1jL5gH"


def test_convert_returns_9_field_auth_json(sample_session):
    auth = convert(sample_session)
    assert set(auth.keys()) == {
        "access_token", "account_id", "disabled", "email",
        "expired", "id_token", "last_refresh", "refresh_token", "type"
    }


def test_convert_populates_known_fields(sample_session):
    auth = convert(sample_session)
    assert auth["access_token"] == sample_session["accessToken"]
    assert auth["account_id"] == "11111111-2222-3333-4444-555555555555"
    assert auth["email"] == "test@example.com"
    assert auth["disabled"] is False
    assert auth["type"] == "codex"
    assert auth["id_token"] == ""
    assert auth["refresh_token"] == ""


def test_convert_expired_is_iso8601(sample_session):
    auth = convert(sample_session)
    assert auth["expired"].startswith("2286-")  # exp=9999999999 → year 2286


def test_convert_last_refresh_is_iso8601(sample_session):
    auth = convert(sample_session)
    from datetime import datetime
    datetime.fromisoformat(auth["last_refresh"])


def test_build_filename_format():
    assert build_filename("test@example.com", "plus") == "codex-test@example.com-plus.json"


def test_build_filename_sanitizes_windows_chars():
    assert build_filename("a:b@c.com", "plus") == "codex-a_b@c.com-plus.json"
    assert build_filename("a*b@c.com", "free") == "codex-a_b@c.com-free.json"


def test_build_filename_empty_email_fallback():
    assert build_filename("", "free") == "codex-unknown-free.json"
