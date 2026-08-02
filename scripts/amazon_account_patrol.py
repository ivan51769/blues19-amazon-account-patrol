#!/usr/bin/env python3
"""Multi-market Amazon Seller Central patrol through the Ziniao CLI bridge.

The runner never enters an email or account identifier. Each store must supply
its own saved account through the browser's autofill/session state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from pathlib import Path


MARKETS = {
    "us": {"tld": "com", "mkid": "ATVPDKIKX0DER", "name_zh": "美国", "labels": ("美国", "美國", "United States", "US")},
    "ca": {"tld": "ca", "mkid": "A2EUQ1WTGCTBG2", "name_zh": "加拿大", "labels": ("加拿大", "Canada")},
    "mx": {"tld": "com.mx", "mkid": "A1AM78C64UM0Y8", "name_zh": "墨西哥", "labels": ("墨西哥", "México", "Mexico")},
    "uk": {"tld": "co.uk", "mkid": "A1F83G8C2ARO7P", "name_zh": "英国", "labels": ("\u82f1\u570b", "\u82f1\u56fd", "United Kingdom", "UK")},
    "de": {"tld": "de", "mkid": "A1PA6795UKMFR9", "name_zh": "德国", "labels": ("\u5fb7\u570b", "\u5fb7\u56fd", "Germany")},
    "fr": {"tld": "fr", "mkid": "A13V1IB3VIYZZH", "name_zh": "法国", "labels": ("\u6cd5\u570b", "\u6cd5\u56fd", "France")},
    "it": {"tld": "it", "mkid": "APJ6JRA9NG5V4", "name_zh": "意大利", "labels": ("\u7fa9\u5927\u5229", "\u610f\u5927\u5229", "Italy")},
    "es": {"tld": "es", "mkid": "A1RKKUPIHCS9HS", "name_zh": "西班牙", "labels": ("\u897f\u73ed\u7259", "Spain")},
    "nl": {"tld": "nl", "mkid": "A1805IZSGTT6HS", "name_zh": "荷兰", "labels": ("\u8377\u862d", "\u8377\u5170", "Netherlands")},
}


class PatrolError(RuntimeError):
    pass


RUN_LOG_PATH: Path | None = None
LAST_OPERATION = "not started"


def patrol_time_basis(timezone_name: str | None, working_hours: str | None) -> str:
    if bool(timezone_name) != bool(working_hours):
        raise PatrolError("--timezone and --working-hours must be supplied together")
    if not timezone_name:
        local_now = datetime.now().astimezone()
        basis = str(local_now.tzinfo)
        log_event(f"No schedule gate requested; clock={basis}; local_time={local_now.isoformat(timespec='minutes')}")
        return basis

    try:
        zone = ZoneInfo(timezone_name)
    except Exception as exc:
        raise PatrolError(f"invalid IANA timezone: {timezone_name}") from exc
    match = re.fullmatch(r"([01]\d|2[0-3]):([0-5]\d)-([01]\d|2[0-3]):([0-5]\d)", working_hours or "")
    if not match:
        raise PatrolError("--working-hours must use HH:MM-HH:MM")
    start = int(match.group(1)) * 60 + int(match.group(2))
    end = int(match.group(3)) * 60 + int(match.group(4))
    if start >= end:
        raise PatrolError("--working-hours start must be earlier than end")
    local_now = datetime.now(timezone.utc).astimezone(zone)
    current = local_now.hour * 60 + local_now.minute
    if not start <= current < end:
        raise PatrolError(
            f"patrol blocked by requested schedule gate; clock={timezone_name}; "
            f"local_time={local_now.isoformat(timespec='minutes')}; allowed_window={working_hours}"
        )
    log_event(f"Schedule gate passed: clock={timezone_name}; local_time={local_now.isoformat(timespec='minutes')}")
    return timezone_name

def log_event(message: str) -> None:
    global LAST_OPERATION
    LAST_OPERATION = message
    line = f"{datetime.now().astimezone().isoformat(timespec='seconds')} | {message}"
    print(line, flush=True)
    if RUN_LOG_PATH:
        RUN_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with RUN_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


CRASH_MARKERS = (
    "Aw, Snap!",
    "This page isn't working",
    "Something went wrong",
    "ERR_CONNECTION",
    "ERR_NETWORK",
    "ERR_FAILED",
    "ERR_TIMED_OUT",
    "页面崩溃",
    "网页崩溃",
    "连接已关闭",
    "出现问题",
)


def cli_path() -> str:
    configured = os.environ.get("ZINIAO_CLI")
    discovered = shutil.which("ziniao-cli.cmd") or shutil.which("ziniao-cli")
    path = configured or discovered
    if not path:
        raise PatrolError("ziniao-cli was not found; set ZINIAO_CLI or add it to PATH")
    return path


def run_cli(
    *args: str,
    timeout: int = 60,
    allow_non_json: bool = False,
    retry_safe: bool = True,
) -> dict:
    log_event(f"CLI start: {' '.join(args[:4])}")
    transient_markers = ("无法连接紫鸟浏览器", "connect ETIMEDOUT", "ECONNREFUSED", "ERR_CONNECTION_CLOSED")
    proc = None
    raw = ""
    attempts = 2 if retry_safe else 1
    for attempt in range(attempts):
        try:
            proc = subprocess.run(
                [cli_path(), *args], capture_output=True, text=True, encoding="utf-8", timeout=timeout
            )
        except subprocess.TimeoutExpired as exc:
            if attempt + 1 < attempts:
                time.sleep(1)
                continue
            retry_note = " after retry" if attempts > 1 else "; not retried because the operation may have side effects"
            raise PatrolError(f"ziniao-cli timeout{retry_note}: {args[:3]}") from exc
        raw = proc.stdout.strip() or proc.stderr.strip()
        if not proc.returncode:
            log_event(f"CLI success: {args[0]} {args[1] if len(args) > 1 else ''}")
            break
        if attempt + 1 < attempts and any(marker in raw for marker in transient_markers):
            time.sleep(1)
            continue
        raise PatrolError(raw or f"ziniao-cli exit {proc.returncode}")
    if proc is None or proc.returncode:
        raise PatrolError(raw or "ziniao-cli failed")
    if allow_non_json and not raw.startswith("{"):
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        # Some CLI commands append a human-readable marker after JSON.
        start = raw.find("{")
        if start >= 0:
            try:
                value, _ = json.JSONDecoder().raw_decode(raw[start:])
                return value
            except json.JSONDecodeError:
                pass
        raise PatrolError(f"invalid ziniao-cli JSON: {raw[:300]}") from exc


def nested(data: dict, *keys: str):
    for key in keys:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


def safe_store_filename(store_id: str) -> str:
    """Keep the runtime store ID intact while making output filenames path-safe."""
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", store_id).strip(" .")
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
    changed = cleaned != store_id or len(cleaned) > 100 or cleaned.upper() in reserved
    if not cleaned:
        cleaned = "store"
        changed = True
    if changed:
        digest = hashlib.sha256(store_id.encode("utf-8")).hexdigest()[:8]
        cleaned = f"{cleaned[:80]}-{digest}"
    return cleaned


def page_content(store_id: str) -> str:
    log_event(f"Read page text: store={store_id}")
    result = run_cli("page", "content", "--store-id", store_id, "--content-format", "text", "--timeout", "30000")
    return nested(result, "data", "data", "content") or ""


def page_state(store_id: str) -> dict:
    try:
        url = str(page_exec(store_id, "location.href") or "")
    except PatrolError:
        url = ""
    return {"url": url, "text": page_content(store_id)}


def is_crash_page(state: dict) -> bool:
    url = str(state.get("url", ""))
    text = str(state.get("text", ""))
    if "chrome-extension://" in url and "/error.html" in url:
        return True
    if url in ("", "about:blank") and not text.strip():
        return True
    return any(marker.lower() in f"{url}\n{text}".lower() for marker in CRASH_MARKERS)


def page_exec(store_id: str, script: str) -> object:
    result = run_cli(
        "page", "exec", "--store-id", store_id, "--script", script, "--timeout", "20000",
        allow_non_json=True, retry_safe=False
    )
    return nested(result, "data", "data", "result")


def refresh_page(store_id: str) -> None:
    log_event(f"Refresh current page: store={store_id}")
    page_exec(store_id, "location.reload(); 'reloading'")
    time.sleep(2)


def recover_page(store_id: str, url: str) -> None:
    """Refresh crash pages first, then revisit the original URL once more."""
    for attempt in range(3):
        try:
            state = page_state(store_id)
        except PatrolError:
            state = {"url": "", "text": ""}
        if not is_crash_page(state):
            return
        log_event(f"Crash page detected: url={url}; refresh_attempt={attempt + 1}")
        if attempt < 2:
            try:
                refresh_page(store_id)
            except PatrolError:
                time.sleep(1)
            continue
        raise PatrolError(f"page remained crashed after refresh/revisit: {url}")


def page_screenshot(store_id: str) -> str:
    log_event(f"Capture full-page screenshot: store={store_id}")
    result = run_cli("page", "screenshot", "--store-id", store_id, "--full-page", "--timeout", "30000")
    raw_path = str(nested(result, "data", "data", "filePath") or "").strip()
    if not raw_path:
        raise PatrolError("ziniao-cli returned an empty screenshot path")
    screenshot = Path(raw_path).expanduser()
    if not screenshot.is_file():
        raise PatrolError(f"screenshot file does not exist: {raw_path}")
    return str(screenshot.resolve())


def query_exists(store_id: str, selector: str) -> bool:
    try:
        result = run_cli("page", "query", "--store-id", store_id, "--selector", selector, "--timeout", "5000")
        return bool(nested(result, "data", "data", "items"))
    except PatrolError:
        return False


def query_value(store_id: str, selector: str) -> str:
    result = run_cli("page", "query", "--store-id", store_id, "--selector", selector, "--timeout", "5000")
    items = nested(result, "data", "data", "items") or []
    return str(items[0].get("value", "")) if items else ""


def wait_for_selector(store_id: str, selector: str, seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if query_exists(store_id, selector):
            return
        time.sleep(0.25)
    raise PatrolError(f"selector did not appear within {seconds:.1f}s: {selector}")


def click_selector(store_id: str, selector: str, timeout: int = 10000) -> None:
    log_event(f"Click selector: {selector}")
    encoded = json.dumps(selector)
    result = page_exec(store_id, f"(()=>{{const es=[...document.querySelectorAll({encoded})]; const e=es[es.length-1]; if(!e) throw new Error('selector not found'); e.click(); return 'clicked';}})()")
    if result not in (None, "clicked"):
        raise PatrolError(f"click did not execute: {selector}")


def visit(store_id: str, url: str) -> None:
    log_event(f"Navigate: {url}")
    args = ("page", "visit", "--store-id", store_id, "--url", url, "--wait-until", "load", "--timeout", "60000")
    try:
        run_cli(*args, allow_non_json=True, retry_safe=False)
    except PatrolError:
        try:
            state = page_state(store_id)
        except PatrolError:
            state = {"url": "", "text": ""}
        if state.get("url") and str(state.get("text", "")).strip() and not is_crash_page(state):
            log_event(f"Navigation timed out but current page is readable; continue without duplicate visit: {state['url']}")
        else:
            time.sleep(1.5)
            run_cli(*args, allow_non_json=True, retry_safe=False)
    recover_page(store_id, url)


def ensure_store_login(store_id: str, base: str) -> None:
    """Use only the store's own browser autofill/session; never type an email."""
    content = page_content(store_id)
    if not any(token in content for token in ("Log in", "Sign in", "登入", "登录")):
        log_event(f"Already authenticated: base={base}")
        return

    log_event(f"Login page detected; use saved store account only: base={base}")
    visit(store_id, f"{base}/signin")
    if not query_value(store_id, "#ap_email"):
        raise PatrolError("store account was not autofilled; refusing manual account input")

    # First submit: the store's saved account and password flow.
    wait_for_selector(store_id, "#continue", 8)
    click_selector(store_id, "#continue")
    wait_for_selector(store_id, "#signInSubmit", 10)
    if query_exists(store_id, "#ap_password") and not query_value(store_id, "#ap_password"):
        raise PatrolError("store password was not autofilled; refusing manual password input")
    click_selector(store_id, "#signInSubmit")

    # Some stores do not require MFA. If it appears, submit only a current autofilled OTP.
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline and not query_exists(store_id, "#auth-mfa-otpcode"):
        state = page_state(store_id)
        if not any(token in state.get("text", "") for token in ("Log in", "Sign in", "登入", "登录")):
            log_event("Authentication completed without an MFA prompt")
            return
        time.sleep(0.4)
    if not query_exists(store_id, "#auth-mfa-otpcode"):
        raise PatrolError("authentication did not complete and no MFA field appeared")
    if not query_value(store_id, "#auth-mfa-otpcode"):
        raise PatrolError("OTP was not autofilled; refusing manual code input")
    wait_for_selector(store_id, "#auth-signin-button", 2)
    click_selector(store_id, "#auth-signin-button")
    log_event("MFA submitted once with the autofilled OTP")


def select_marketplace(store_id: str, labels: tuple[str, ...]) -> None:
    log_event(f"Select marketplace row: labels={labels}")
    encoded = json.dumps(list(labels), ensure_ascii=True)
    page_exec(
        store_id,
        "(()=>{const labels=%s; const b=[...document.querySelectorAll('.full-page-account-switcher-account button')].find(x=>labels.includes((x.innerText||x.textContent||'').trim())); if(!b) throw new Error('marketplace button not found'); b.click(); return 'selected';})()" % encoded,
    )
    log_event("Click lower-right Select account confirmation")
    time.sleep(0.4)
    if not any(label in page_content(store_id) for label in labels):
        raise PatrolError(f"marketplace selection did not register; labels={labels}")
    confirmation_js = """(()=>{
        const re=/^(select\\s+account|選取帳戶|選取账户|选择账户)$/i;
        const visible=e=>{const r=e.getBoundingClientRect(); return r.width>0 && r.height>0 && getComputedStyle(e).visibility!=='hidden'};
        const candidates=[...document.querySelectorAll('button,kat-button,[role="button"]')]
            .filter(e=>visible(e) && re.test((e.innerText||e.textContent||'').trim()));
        const b=candidates[candidates.length-1];
        if(!b) throw new Error('select-account confirmation button not found');
        b.click();
        return 'confirmed';
    })()"""
    for attempt in range(2):
        page_exec(store_id, confirmation_js)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            current_url = page_state(store_id).get("url", "")
            if "account-switcher" not in current_url.lower():
                return
            time.sleep(0.5)
        if attempt == 0:
            log_event("Marketplace confirmation still on account-switcher; retry confirmation once")
            time.sleep(0.5)
    raise PatrolError("marketplace confirmation did not leave account-switcher")


def verify_marketplace(store_id: str, marketplace: str) -> str:
    log_event(f"Verify marketplace: {marketplace}")
    market = MARKETS[marketplace]
    state = page_state(store_id)
    url = state.get("url", "")
    content = state.get("text", "")
    labels = market["labels"]
    expected_host = f"sellercentral.amazon.{market['tld']}"
    parsed = urllib.parse.urlparse(url)
    # Amazon may wrap the marketplace ID as amzn1.mp.o.<mkid> in mons_sel_mkid.
    query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
    selected_market_ids = [
        value
        for key, values in query.items()
        if key.lower() == "mons_sel_mkid"
        for value in values
    ]
    has_market_id_parameter = any(key.lower() == "mons_sel_mkid" for key in query)
    has_market_id = any(market["mkid"].lower() in value.lower() for value in selected_market_ids)
    has_market_label = any(label in content for label in labels)
    host_is_target = (parsed.hostname or "").lower() == expected_host
    valid_home = parsed.path == "/home" or parsed.path.startswith("/home/") or parsed.path.startswith("/amazonsell/business")
    market_proof_matches = has_market_id if has_market_id_parameter else host_is_target
    if not valid_home or not has_market_label or not market_proof_matches:
        raise PatrolError(
            f"marketplace verification failed; expected_host={expected_host}; expected_mkid={market['mkid']}; "
            f"url={url!r}; labels={labels}; mons_sel_mkid_present={has_market_id_parameter}"
        )
    return ""


def extract_count(text: str) -> str:
    match = re.search(r"(?:通知总数|總通知數|total notifications)\D{0,20}(\d+)", text, re.I)
    return match.group(1) if match else "unknown"


def extract_account(text: str, marketplace: str) -> str:
    labels = MARKETS[marketplace]["labels"]
    for label in labels:
        match = re.search(rf"([A-Za-z][A-Za-z .'-]{{1,60}})\s+{re.escape(label)}\b", text)
        if match:
            prefix = re.sub(r"\s+", " ", match.group(1)).strip()
            # New Seller Central pages prepend navigation text before the store name.
            prefix = re.split(r"manage account health", prefix, flags=re.I)[-1].strip()
            return prefix or "未识别账号"
    return "未识别账号"


def recent_notices(text: str, limit: int = 5) -> list[dict]:
    marker = "Subject Date Actions"
    start = text.find(marker)
    if start < 0:
        return []
    text = text[start + len(marker):]
    months = (
        "January|February|March|April|May|June|July|August|September|October|November|December|"
        "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
    )
    date_re = re.compile(
        rf"(?:\b\d{{1,2}}\s+(?:{months})\s+\d{{4}}\b|\b(?:{months})\s+\d{{1,2}}(?:,)?\s+\d{{4}}\b|\b\d{{1,2}}[./]\d{{1,2}}[./]\d{{4}}\b)",
        re.I,
    )
    matches = list(date_re.finditer(text))
    rows = []
    cursor = 0
    for match in matches:
        subject = re.sub(r"\s+", " ", text[cursor:match.start()]).strip(" -|:")
        date = match.group(0)
        cursor = match.end()
        if not subject or len(subject) > 500:
            continue
        rows.append({"date": date, "subject": subject, "meaning": translate_notice(subject)})
        if len(rows) >= limit:
            break
    return rows


def translate_notice(subject: str) -> str:
    lower = subject.lower()
    if "reactiva tus listings" in lower and ("seguridad" in lower or "gpsr" in lower):
        return "\u91cd\u65b0\u6fc0\u6d3b\u5546\u54c1\u5236\u5b9a\uff1a\u9700\u6ee1\u8db3\u6b27\u76df\u4ea7\u54c1\u5b89\u5168\u8981\u6c42"
    if "no cumples los requisitos" in lower and "prime" in lower:
        return "\u4e0d\u6ee1\u8db3\u8be5\u56fd\u4e9a\u9a6c\u9001\u8fbe\u4f18\u5148\u8ba1\u5212\u7684\u8d44\u683c\u8981\u6c42"
    if "toma medidas" in lower or "take action" in lower:
        return "\u8bf7\u91c7\u53d6\u63aa\u65bd\uff1a\u9700\u8865\u5145\u8d44\u6599\u6216\u5728\u9650\u671f\u5185\u5904\u7406"
    if "vat" in lower or "fiscal" in lower or "tax" in lower:
        return "\u6d89\u53ca VAT \u6216\u7a0e\u52a1\u767b\u8bb0\uff0c\u9700\u6838\u5bf9\u7533\u62a5\u4e0e\u6ce8\u518c\u72b6\u6001"
    return "\u539f\u6587\u4e3b\u9898\uff0c\u9700\u6839\u636e\u8bed\u8a00\u4eba\u5de5\u590d\u6838\u4e2d\u6587\u542b\u4e49"


def json_request(url: str, payload: dict, token: str = "", retry_safe: bool = True) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    last_error = None
    attempts = 2 if retry_safe else 1
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(1)
    if not retry_safe:
        raise PatrolError(f"Feishu request outcome is unknown and was not retried: {last_error}")
    return curl_json_request(url, payload, token, last_error)


def curl_json_request(url: str, payload: dict, token: str, previous_error: Exception | None = None) -> dict:
    headers = [("Content-Type", "application/json; charset=utf-8")]
    if token:
        headers.append(("Authorization", f"Bearer {token}"))
    command = ["curl.exe", "-sS", "--max-time", "30", "-X", "POST", url]
    for name, value in headers:
        command.extend(["-H", f"{name}: {value}"])
    payload_file = None
    try:
        with tempfile.NamedTemporaryFile(prefix="ziniao-feishu-", suffix=".json", delete=False) as handle:
            payload_file = handle.name
            handle.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        command.extend(["--data-binary", f"@{payload_file}"])
        try:
            proc = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=35)
            if proc.returncode:
                raise PatrolError(proc.stderr.strip() or f"curl exit {proc.returncode}")
            return json.loads(proc.stdout)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, PatrolError) as exc:
            raise PatrolError(f"Feishu request failed after HTTPS and curl retries: {previous_error or exc}") from exc
    finally:
        if payload_file:
            try:
                Path(payload_file).unlink()
            except OSError:
                pass


def feishu_token() -> str:
    app_id = os.environ.get("FEISHU_APP_ID") or os.environ.get("LARK_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET") or os.environ.get("LARK_APP_SECRET")
    if not app_id or not app_secret:
        raise PatrolError("FEISHU_APP_ID/FEISHU_APP_SECRET are not configured")
    result = json_request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        {"app_id": app_id, "app_secret": app_secret},
    )
    token = result.get("tenant_access_token")
    if not token:
        raise PatrolError(f"Feishu token rejected: code={result.get('code')}")
    return token


def feishu_upload_image(token: str, path: str) -> str:
    boundary = f"----ziniaoPatrol{int(time.time() * 1000)}".encode("ascii")
    image = Path(path).read_bytes()
    chunks = [
        b"--" + boundary + b"\r\nContent-Disposition: form-data; name=\"image_type\"\r\n\r\nmessage\r\n",
        b"--" + boundary + b"\r\nContent-Disposition: form-data; name=\"image\"; filename=\"screenshot.png\"\r\nContent-Type: image/png\r\n\r\n",
        image,
        b"\r\n--" + boundary + b"--\r\n",
    ]
    request = urllib.request.Request(
        "https://open.feishu.cn/open-apis/im/v1/images",
        data=b"".join(chunks),
        headers={"Authorization": f"Bearer {token}", "Content-Type": f"multipart/form-data; boundary={boundary.decode('ascii')}"},
        method="POST",
    )
    last_error = None
    result = None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                result = json.loads(response.read().decode("utf-8"))
                break
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt < 1:
                time.sleep(1)
    if result is None:
        command = [
            "curl.exe", "-sS", "--max-time", "30", "-X", "POST",
            "-H", f"Authorization: Bearer {token}",
            "-F", "image_type=message",
            "-F", f"image=@{path};type=image/png",
            "https://open.feishu.cn/open-apis/im/v1/images",
        ]
        try:
            proc = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=35)
            if proc.returncode:
                raise PatrolError(proc.stderr.strip() or f"curl exit {proc.returncode}")
            result = json.loads(proc.stdout)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, PatrolError) as exc:
            raise PatrolError(f"Feishu image upload failed after HTTPS and curl retries: {last_error or exc}") from exc
    key = nested(result, "data", "image_key")
    if result.get("code") != 0 or not key:
        raise PatrolError(f"Feishu image upload rejected: code={result.get('code')}")
    return key


def feishu_send_message(token: str, chat_id: str, msg_type: str, content: dict) -> str:
    result = json_request(
        "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id",
        {"receive_id": chat_id, "msg_type": msg_type, "content": json.dumps(content, ensure_ascii=False)},
        token,
        retry_safe=False,
    )
    message_id = nested(result, "data", "message_id")
    if result.get("code") != 0 or not message_id:
        raise PatrolError(f"Feishu message rejected: code={result.get('code')}")
    return str(message_id)


def send_feishu_report(results: list[dict], chat_id: str, log_path: Path) -> list[str]:
    token = feishu_token()
    message_ids = []
    for result in results:
        if not result.get("ok"):
            message_ids.append(feishu_send_message(
                token,
                chat_id,
                "text",
                {"text": f"亚马逊巡检失败\n账号：{result.get('account', '未识别账号')}\n国家：{MARKETS[result['marketplace']]['name_zh']}\n失败位置：{result.get('failed_at')}\n错误：{result.get('error')}\n操作日志：{log_path}"},
            ))
            continue
        market_name = MARKETS[result["marketplace"]]["name_zh"]
        caption = (
            f"截图说明：{result.get('account', '未识别账号')} | {market_name} | "
            f"账户健康+业绩通知 | {result.get('checked_at', datetime.now().strftime('%Y%m%d-%H%M'))}"
        )
        screenshots = list(result.get("screenshots", []))[:2]
        if len(screenshots) != 2 or any(not path or not Path(path).is_file() for path in screenshots):
            raise PatrolError(f"two screenshot files are required before Feishu delivery: {screenshots!r}")
        # One compact caption per market, followed immediately by its two images.
        message_ids.append(feishu_send_message(token, chat_id, "text", {"text": caption}))
        for path in screenshots:
            key = feishu_upload_image(token, path)
            message_ids.append(feishu_send_message(token, chat_id, "image", {"image_key": key}))
    return message_ids


def build_summary(marketplace: str, health: str, notices: str, now: str, record: Path) -> str:
    score = re.search(r"(?:健康分|账户状况评级|帳戶狀況|政策规范|政策合规性)\D{0,40}(\d{2,4})", health)
    healthy = any(word in health for word in ("健康", "健全", "Good", "Healthy"))
    rows = recent_notices(notices)
    recent = "\n".join(f"- {row['date']}: {row['subject']} | {row['meaning']}" for row in rows)
    return (
        f"亚马逊店铺巡检\n国家：{MARKETS[marketplace]['name_zh']}（{marketplace.upper()}）\n"
        f"检查时间：{now}\n"
        f"账户健康：{'健康' if healthy else '需要人工复核'}；健康分：{score.group(1) if score else '未识别'}\n"
        f"业绩通知数量：{extract_count(notices)}\n最近5条通知：\n{recent or '- 未识别'}\n"
        f"本地记录：{record}\n"
    )


def action_plan(marketplace: str, health: str, notices: str) -> tuple[str, str, list[str]]:
    text = f"{health}\n{notices}".lower()
    actions = []
    high = any(token in text for token in ("deactivated", "停售", "missing batteries", "电池注册", "account is at risk"))
    if "vat" in text or "增值税" in text or "税" in text:
        actions.append("保留并处理账户健康页面的欧洲增值税登记要求原文项")
    if "gpsr" in text or "product safety" in text or "产品安全" in text:
        actions.append("补齐 GPSR / 产品安全资料")
    if "prime eligibility" in text or "prime 资格" in text:
        actions.append("核查 FBA Prime 资格变化")
    if marketplace == "nl" and ("battery" in text or "电池" in text):
        actions.append("补齐荷兰电池注册号并复核停售商品")
    if "紧急联系" in health or "emergency contact" in text:
        actions.append("完成紧急联系人验证")
    if not actions:
        actions.append("进入账户健康详情逐项确认未关闭问题")
    risk = "高" if high else ("中" if len(actions) > 1 else "低")
    status = "待处理" if actions else "已完成"
    return risk, status, actions


def patrol_market(
    store_id: str,
    marketplace: str,
    timezone_name: str | None,
    working_hours: str | None,
    output_dir: Path,
) -> dict:
    time_basis = patrol_time_basis(timezone_name, working_hours)
    log_event(f"START marketplace patrol: {marketplace}; time_basis={time_basis}")
    market = MARKETS[marketplace]
    base = f"https://sellercentral.amazon.{market['tld']}"
    labels = market["labels"]
    # Enter the requested marketplace directly. Only authenticate if this
    # marketplace presents its sign-in page; never carry an account from another store.
    visit(store_id, f"{base}/home")
    ensure_store_login(store_id, base)
    visit(store_id, f"{base}/account-switcher/default/merchantMarketplace?returnTo=%2Fhome")
    select_marketplace(store_id, labels)
    verify_marketplace(store_id, marketplace)

    pages = []
    for name, path in (("account-health", "/performance/dashboard"), ("performance-notifications", "/performance/notifications")):
        log_event(f"Inspect {name}: {base + path}")
        visit(store_id, base + path)
        state = page_state(store_id)
        actual_url = str(state.get("url", ""))
        content = str(state.get("text", ""))
        if urllib.parse.urlparse(actual_url).path.rstrip("/") != path:
            raise PatrolError(f"unexpected page after navigation; expected_path={path}; actual_url={actual_url!r}")
        if not content.strip():
            raise PatrolError(f"page content was empty after navigation: {actual_url}")
        image = page_screenshot(store_id)
        pages.append({"name": name, "url": actual_url, "content": content, "screenshot": image})

    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    file_store_id = safe_store_filename(store_id)
    out = output_dir / f"{file_store_id}-{marketplace.upper()}-{datetime.now():%Y-%m-%d}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    account = extract_account(pages[0]["content"], marketplace)
    risk, status, actions = action_plan(marketplace, pages[0]["content"], pages[1]["content"])
    summary = f"账号：{account}\n时间基准：{time_basis}\n风险等级：{risk}\n处理状态：{status}\n下一步动作：{'；'.join(actions)}\n" + build_summary(marketplace, pages[0]["content"], pages[1]["content"], now, out)
    body = [f"# Amazon patrol: {marketplace}", "", summary, "## Source pages", ""]
    body.extend(f"- {p['name']}: `{p['url']}`" for p in pages)
    body.extend(["", "## Screenshots", ""])
    body.extend(f"- {p['name']}: `{p['screenshot']}`" for p in pages)
    body.extend(["", "## Raw account health text", "", pages[0]["content"]])
    body.extend(["", "## Recent five performance notifications", ""])
    rows = recent_notices(pages[1]["content"])
    body.extend(
        f"{index}. **{row['date']}** - {row['subject']}\n   Chinese meaning: {row['meaning']}"
        for index, row in enumerate(rows, 1)
    )
    body.extend(["", "## Raw performance notification text", "", pages[1]["content"]])
    body.extend(["", "## Risk and action plan", "", f"- Risk level: {risk}", f"- Status: {status}", f"- Next actions: {'; '.join(actions)}"])
    out.write_text("\n".join(body), encoding="utf-8")
    log_event(f"Record written: {out}")
    return {
        "marketplace": marketplace,
        "account": account,
        "checked_at": datetime.now().strftime("%Y%m%d-%H%M"),
        "risk": risk,
        "status": status,
        "actions": actions,
        "record": str(out),
        "screenshots": [p["screenshot"] for p in pages],
        "summary": summary,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store-id", required=True)
    parser.add_argument("--timezone", help="Optional IANA timezone for a user-requested schedule gate.")
    parser.add_argument("--working-hours", help="Optional HH:MM-HH:MM window; requires --timezone.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--marketplace", choices=MARKETS)
    group.add_argument("--all-marketplaces", action="store_true")
    parser.add_argument("--output-dir", default="amazon-patrol-output")
    parser.add_argument("--send-feishu", action="store_true", help="Explicitly opt in to Feishu delivery.")
    parser.add_argument("--feishu-chat-id")
    args = parser.parse_args()
    global RUN_LOG_PATH
    run_stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    output_dir = Path(args.output_dir).expanduser().resolve()
    file_store_id = safe_store_filename(args.store_id)
    RUN_LOG_PATH = output_dir / "logs" / f"{file_store_id}-{run_stamp}.log"
    log_event(f"RUN START store={args.store_id}; markets={','.join(MARKETS if args.all_marketplaces else [args.marketplace])}")
    markets = list(MARKETS) if args.all_marketplaces else [args.marketplace]
    results = []
    for marketplace in markets:
        try:
            result = {
                "ok": True,
                **patrol_market(args.store_id, marketplace, args.timezone, args.working_hours, output_dir),
            }
            result["log"] = str(RUN_LOG_PATH)
            results.append(result)
            log_event(f"OK {marketplace}: record={result['record']}")
        except Exception as exc:  # Continue batch patrol, but preserve the exact failure.
            failed_at = LAST_OPERATION
            result = {"ok": False, "marketplace": marketplace, "error": str(exc), "failed_at": failed_at, "log": str(RUN_LOG_PATH)}
            results.append(result)
            log_event(f"FAIL {marketplace}: failed_at={failed_at}; error={result['error']}")
    feishu_result = None
    if args.send_feishu:
        log_event("FEISHU START: send run result, failures, and successful screenshots")
        chat_id = args.feishu_chat_id or os.environ.get("FEISHU_CHAT_ID") or os.environ.get("LARK_CHAT_ID")
        if not chat_id:
            feishu_result = {"ok": False, "error": "FEISHU_CHAT_ID or --feishu-chat-id is required"}
        else:
            try:
                message_ids = send_feishu_report(results, chat_id, RUN_LOG_PATH)
                feishu_result = {"ok": True, "status": "api_accepted", "message_ids": message_ids}
                log_event("FEISHU OK")
            except Exception as exc:
                feishu_result = {"ok": False, "error": str(exc)}
                log_event(f"FEISHU FAIL: {feishu_result['error']}")
    output = {"ok": all(r["ok"] for r in results), "results": results}
    if feishu_result is not None:
        output["feishu"] = feishu_result
        output["ok"] = output["ok"] and feishu_result["ok"]
    log_event(f"RUN END ok={output['ok']}; log={RUN_LOG_PATH}")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
