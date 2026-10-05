from datetime import datetime


def build_create_page_result(
    status,
    account_id,
    page_name,
    category,
    page_url="",
    page_id="",
    reason="",
    technical_error="",
    retry_count=0,
    account_index=None,
    proxy="",
    flow_state="",
    structural_failure="",
):
    return {
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "account_index": account_index,
        "account": account_id,
        "account_id": account_id,
        "page_name": page_name,
        "category": category,
        "page_url": page_url,
        "page_id": page_id,
        "proxy": proxy,
        "status": str(status).upper(),
        "reason": reason,
        "technical_error": technical_error,
        "retry_count": int(retry_count),
        "flow_state": str(flow_state or status).upper(),
        "structural_failure": structural_failure,
    }

def is_transient_create_page_error(exc):
    text = f"{type(exc).__name__}: {exc}".casefold()
    return isinstance(exc, (TimeoutError, OSError, ConnectionError)) or any(
        marker in text for marker in (
            "timeout", "timed out", "connection", "network", "navigation",
            "net::err_", "temporarily unavailable",
        )
    )
