"""ChatGPT login flow qua CloakBrowser. Sync API."""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import pyotp
from cloakbrowser import launch_persistent_context

from grabber.accounts import Account
from grabber.errors import (
    CaptchaDetected, ChallengePage, DomChanged, LoginFailed,
    MfaFailed, MfaRequiredNoSecret, NetworkError, Timeout,
)

log = logging.getLogger(__name__)

LOGIN_SHORTCUT_URL = "https://chatgpt.com/auth/login"
SESSION_URL = "https://chatgpt.com/api/auth/session"
HARD_TIMEOUT_SEC = 90


def _check_cloudflare(page) -> None:
    """Raise CaptchaDetected/ChallengePage nếu thấy CF challenge."""
    try:
        title = page.title()
    except Exception:
        title = ""
    if "Just a moment" in title:
        raise CaptchaDetected("Cloudflare 'Just a moment' page", detail=page.url)
    url = page.url
    if "/api/auth/error" in url or "/challenge/" in url or "/cdn-cgi/challenge-platform" in url:
        raise ChallengePage(f"challenge URL: {url}")
    try:
        iframe_srcs = page.evaluate(
            "() => Array.from(document.querySelectorAll('iframe')).map(f => f.src || '')"
        )
    except Exception:
        iframe_srcs = []
    for src in iframe_srcs:
        if "cloudflare.com" in src or "turnstile" in src or "hcaptcha" in src:
            raise CaptchaDetected("CF/Turnstile/hCaptcha iframe detected", detail=src)


def _fetch_session(page) -> dict | None:
    """Navigate /api/auth/session và parse JSON. Trả None nếu không phải session JSON."""
    page.goto(SESSION_URL, wait_until="domcontentloaded")
    time.sleep(1.0)
    body = page.evaluate("() => document.body.innerText")
    if '"user"' in body and '"accessToken"' in body:
        try:
            return json.loads(body)
        except Exception:
            return None
    return None


def grab_session(
    account: Account,
    profile_dir: Path,
    *,
    headless: bool = False,
) -> dict:
    """Login + fetch session. Raises GrabError subclasses on failure.

    Returns: parsed session dict (raw từ /api/auth/session).
    """
    start = time.monotonic()

    profile_dir.mkdir(parents=True, exist_ok=True)

    try:
        ctx = launch_persistent_context(
            str(profile_dir),
            headless=headless,
            humanize=True,
        )
    except Exception as e:
        raise NetworkError(f"failed to launch browser: {e}") from e

    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    def _elapsed() -> float:
        return time.monotonic() - start

    def _check_timeout():
        if _elapsed() > HARD_TIMEOUT_SEC:
            raise Timeout(f"exceeded {HARD_TIMEOUT_SEC}s")

    try:
        # Fast path: đã login sẵn từ profile cũ?
        log.info("[%s] fast path: check existing session", account.email)
        existing = _fetch_session(page)
        if existing:
            log.info("[%s] already logged in via cached cookie", account.email)
            return existing

        _check_timeout()

        # Shortcut entry
        log.info("[%s] shortcut: %s", account.email, LOGIN_SHORTCUT_URL)
        try:
            page.goto(LOGIN_SHORTCUT_URL, wait_until="domcontentloaded", timeout=20000)
        except Exception as e:
            raise NetworkError(f"goto login: {e}") from e
        time.sleep(1.5)
        _check_cloudflare(page)

        # Email step
        log.info("[%s] fill email", account.email)
        try:
            page.fill("input[type='email']", account.email, timeout=10000)
        except Exception as e:
            raise DomChanged(f"email input not found: {e}") from e
        page.get_by_role("button", name="Continue", exact=True).click(timeout=5000)
        time.sleep(4)
        _check_timeout()
        _check_cloudflare(page)

        # Wait for password page (DOM-based; page.url unreliable on React SPA)
        log.info("[%s] wait for password field", account.email)
        try:
            page.wait_for_selector("input[type='password']", timeout=15000)
        except Exception as e:
            _check_cloudflare(page)  # raise CAPTCHA first if applicable
            raise LoginFailed(f"password input not appearing: {e}") from e
        log.info("[%s] fill password", account.email)
        try:
            page.fill("input[type='password']", account.password, timeout=10000)
        except Exception as e:
            raise DomChanged(f"password input not found: {e}") from e
        time.sleep(0.5)  # let React register input
        page.click("button[type='submit']", timeout=5000)
        # Wait for either MFA prompt or successful redirect (DOM-based)
        log.info("[%s] wait for MFA prompt or success", account.email)
        try:
            page.wait_for_selector(
                "input[autocomplete*='one-time'], body",  # MFA input or fallback
                timeout=15000,
            )
        except Exception:
            pass
        time.sleep(2)
        _check_timeout()
        _check_cloudflare(page)

        # MFA step — detect by presence of one-time code input
        mfa_visible = False
        try:
            mfa_visible = page.locator("input[autocomplete*='one-time']").count() > 0
        except Exception:
            mfa_visible = False

        if mfa_visible:
            if not account.totp_secret:
                raise MfaRequiredNoSecret(f"MFA prompt but no totp_secret for {account.email}")
            log.info("[%s] submit MFA code", account.email)
            try:
                code = pyotp.TOTP(account.totp_secret).now()
                page.fill("input[autocomplete*='one-time']", code, timeout=10000)
                time.sleep(0.5)  # let React register the input value before submit
                page.get_by_role("button", name="Continue", exact=True).click(timeout=5000)
            except Exception as e:
                raise DomChanged(f"MFA input not found: {e}") from e

            # Wait for MFA input to disappear (success) or stay visible (rejected)
            mfa_success = False
            for _ in range(15):  # ~15s max
                time.sleep(1)
                _check_timeout()
                try:
                    still_visible = page.locator("input[autocomplete*='one-time']").count() > 0
                except Exception:
                    still_visible = False
                if not still_visible:
                    mfa_success = True
                    break
            if not mfa_success:
                raise MfaFailed("MFA code rejected (input still visible after 15s)")

        # Final: fetch session
        log.info("[%s] fetch /api/auth/session", account.email)
        session = _fetch_session(page)
        if not session:
            raise LoginFailed(f"session fetch returned no user data; url={page.url}")
        return session

    finally:
        try:
            ctx.close()
        except Exception:
            pass


# ===== Async version =====

import asyncio
from cloakbrowser import launch_persistent_context_async


async def _check_cloudflare_async(page) -> None:
    try:
        title = await page.title()
    except Exception:
        title = ""
    if "Just a moment" in title:
        raise CaptchaDetected("Cloudflare 'Just a moment' page", detail=page.url)
    url = page.url
    if "/api/auth/error" in url or "/challenge/" in url or "/cdn-cgi/challenge-platform" in url:
        raise ChallengePage(f"challenge URL: {url}")
    try:
        iframe_srcs = await page.evaluate(
            "() => Array.from(document.querySelectorAll('iframe')).map(f => f.src || '')"
        )
    except Exception:
        iframe_srcs = []
    for src in iframe_srcs:
        if "cloudflare.com" in src or "turnstile" in src or "hcaptcha" in src:
            raise CaptchaDetected("CF/Turnstile/hCaptcha iframe detected", detail=src)


async def _fetch_session_async(page) -> dict | None:
    await page.goto(SESSION_URL, wait_until="domcontentloaded")
    await asyncio.sleep(1.0)
    body = await page.evaluate("() => document.body.innerText")
    if '"user"' in body and '"accessToken"' in body:
        try:
            return json.loads(body)
        except Exception:
            return None
    return None


async def grab_session_async(
    account: Account,
    profile_dir: Path,
    *,
    headless: bool = False,
) -> dict:
    """Async version of grab_session using DOM-based detection."""
    start = time.monotonic()
    profile_dir.mkdir(parents=True, exist_ok=True)

    try:
        ctx = await launch_persistent_context_async(
            str(profile_dir), headless=headless, humanize=True,
        )
    except Exception as e:
        raise NetworkError(f"failed to launch browser: {e}") from e

    page = ctx.pages[0] if ctx.pages else await ctx.new_page()

    def _check_timeout():
        if time.monotonic() - start > HARD_TIMEOUT_SEC:
            raise Timeout(f"exceeded {HARD_TIMEOUT_SEC}s")

    try:
        # Fast path
        existing = await _fetch_session_async(page)
        if existing:
            log.info("[%s] already logged in via cached cookie", account.email)
            return existing
        _check_timeout()

        # Shortcut entry
        log.info("[%s] shortcut: %s", account.email, LOGIN_SHORTCUT_URL)
        try:
            await page.goto(LOGIN_SHORTCUT_URL, wait_until="domcontentloaded", timeout=20000)
        except Exception as e:
            raise NetworkError(f"goto login: {e}") from e
        await asyncio.sleep(1.5)
        await _check_cloudflare_async(page)

        # Email step
        log.info("[%s] fill email", account.email)
        try:
            await page.fill("input[type='email']", account.email, timeout=10000)
        except Exception as e:
            raise DomChanged(f"email input not found: {e}") from e
        await page.get_by_role("button", name="Continue", exact=True).click(timeout=5000)

        # Wait for password page (DOM-based)
        try:
            await page.wait_for_selector("input[type='password']", timeout=15000)
        except Exception as e:
            await _check_cloudflare_async(page)
            raise LoginFailed(f"password input not appearing: {e}") from e

        log.info("[%s] fill password", account.email)
        try:
            await page.fill("input[type='password']", account.password, timeout=10000)
        except Exception as e:
            raise DomChanged(f"password input not found: {e}") from e
        await asyncio.sleep(0.5)
        await page.click("button[type='submit']", timeout=5000)
        log.info("[%s] wait for MFA prompt or success", account.email)
        try:
            await page.wait_for_selector("input[autocomplete*='one-time'], body", timeout=15000)
        except Exception:
            pass
        await asyncio.sleep(2)
        _check_timeout()
        await _check_cloudflare_async(page)

        # MFA detection by DOM
        mfa_visible = False
        try:
            mfa_visible = await page.locator("input[autocomplete*='one-time']").count() > 0
        except Exception:
            mfa_visible = False

        if mfa_visible:
            if not account.totp_secret:
                raise MfaRequiredNoSecret(f"MFA prompt but no totp_secret for {account.email}")
            log.info("[%s] submit MFA code", account.email)
            try:
                code = pyotp.TOTP(account.totp_secret).now()
                await page.fill("input[autocomplete*='one-time']", code, timeout=10000)
                await asyncio.sleep(0.5)
                await page.get_by_role("button", name="Continue", exact=True).click(timeout=5000)
            except Exception as e:
                raise DomChanged(f"MFA input not found: {e}") from e

            mfa_success = False
            for _ in range(15):
                await asyncio.sleep(1)
                _check_timeout()
                try:
                    still_visible = await page.locator("input[autocomplete*='one-time']").count() > 0
                except Exception:
                    still_visible = False
                if not still_visible:
                    mfa_success = True
                    break
            if not mfa_success:
                raise MfaFailed("MFA code rejected (input still visible after 15s)")

        # Final fetch
        log.info("[%s] fetch /api/auth/session", account.email)
        session = await _fetch_session_async(page)
        if not session:
            raise LoginFailed(f"session fetch returned no user data; url={page.url}")
        return session

    finally:
        try:
            await ctx.close()
        except Exception:
            pass
