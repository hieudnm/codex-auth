"""Exception types cho grabber. Mỗi loại có code để log nhất quán."""
from __future__ import annotations


class GrabError(Exception):
    """Base — mọi lỗi grab account đều subclass."""
    code: str = "UNKNOWN"

    def __init__(self, message: str = "", *, detail: str = ""):
        super().__init__(message or self.code)
        self.detail = detail


class CaptchaDetected(GrabError):
    code = "CAPTCHA_DETECTED"


class ChallengePage(GrabError):
    code = "CHALLENGE_PAGE"


class LoginFailed(GrabError):
    code = "LOGIN_FAILED"


class MfaFailed(GrabError):
    code = "MFA_FAILED"


class MfaRequiredNoSecret(GrabError):
    code = "MFA_REQUIRED_NO_SECRET"


class NetworkError(GrabError):
    code = "NETWORK_ERROR"


class DomChanged(GrabError):
    code = "DOM_CHANGED"


class Timeout(GrabError):
    code = "TIMEOUT"
