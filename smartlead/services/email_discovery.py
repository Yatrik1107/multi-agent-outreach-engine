from __future__ import annotations

import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

# Reasonable email pattern; avoids matching "foo@bar" in code tokens too aggressively.
_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9][a-zA-Z0-9._%+\-]*@[a-zA-Z0-9][a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
)

_DENY_SUBSTR = (
    "example.com",
    "test.com",
    "w3.org",
    "schema.org",
    "sentry.io",
    "google.com",
    "gstatic.com",
    "facebook.com",
    "twitter.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "pinterest.com",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
)


def _normalize_url(website: str) -> str | None:
    w = (website or "").strip()
    if not w:
        return None
    if not w.startswith(("http://", "https://")):
        w = "https://" + w
    return w


def _root_domain(hostname: str | None) -> str:
    if not hostname:
        return ""
    h = hostname.lower().removeprefix("www.")
    parts = h.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return h


def discover_email_from_website(website: str, *, max_bytes: int = 500_000) -> str | None:
    """
    Fetch homepage HTML and return a best-effort contact email, or None.
    POC-only: no JS rendering; many sites will yield nothing.
    """
    url = _normalize_url(website)
    if not url:
        return None
    parsed = urlparse(url)
    host = parsed.hostname or ""
    root = _root_domain(host)

    req = Request(
        url,
        headers={
            "User-Agent": "SmartLeadPOC/1.0 (+contact discovery)",
            "Accept": "text/html,application/xhtml+xml",
        },
        method="GET",
    )
    try:
        with urlopen(req, timeout=15) as resp:  # noqa: S310 — intentional for POC
            raw = resp.read(max_bytes + 1)
    except (HTTPError, URLError, OSError, ValueError):
        return None

    if len(raw) > max_bytes:
        raw = raw[:max_bytes]

    try:
        html = raw.decode("utf-8", errors="ignore")
    except Exception:
        return None

    candidates: list[str] = []
    for m in _EMAIL_RE.finditer(html):
        em = m.group(0).lower().strip()
        if any(bad in em for bad in _DENY_SUBSTR):
            continue
        if em not in candidates:
            candidates.append(em)

    if not candidates:
        return None

    # Prefer same registrable domain as website host.
    if root:
        for em in candidates:
            if em.split("@")[-1].endswith(root) or root in em.split("@")[-1]:
                return em

    # Otherwise first plausible mailbox-style address.
    for em in candidates:
        local = em.split("@")[0]
        if local in {"email", "mail", "image", "sprite"}:
            continue
        return em

    return candidates[0]