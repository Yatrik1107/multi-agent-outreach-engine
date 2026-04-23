from __future__ import annotations

from dataclasses import dataclass
import random
import re
import time
from urllib.parse import urlparse, urlunparse

from smartlead.api.v1.schemas.leads import LeadInput
from smartlead.core.settings import Settings
from smartlead.services.email_discovery import discover_email_from_website

try:
    from exa_py import Exa
except Exception:
    Exa = None

_NON_COMPANY_HOST_KEYWORDS = (
    "wikipedia.org",
    "g2.com",
    "capterra.com",
    "forbes.com",
    "crunchbase.com",
    "linkedin.com",
    "medium.com",
    "exportersindia.com",
    "4allbiz.in",
    "justdial.com",
    "sulekha.com",
    "indiamart.com",
    "tradeindia.com",
)

_NON_COMPANY_NAME_RE = re.compile(
    r"\b(top|best|list|report|guide|overview|market|industry|companies|startups|"
    r"directory|manufacturers|suppliers|exporters|dealers|wholesalers)\b",
    flags=re.IGNORECASE,
)

_INTENT_TERMS: tuple[str, ...] = (
    "company",
    "manufacturers",
    "service providers",
    "suppliers",
    "official website",
)


@dataclass(slots=True)
class GeneratedLeadCandidate:
    company_name: str
    website: str
    contact_email: str = ""
    confidence: float = 0.0
    source_query: str = ""
    source_url: str = ""


@dataclass(slots=True)
class _SearchRow:
    title: str
    url: str
    snippet: str
    source_query: str
    confidence_hint: float

def _split_geo_terms(value: str) -> list[str]:
    # Geo input is expected as comma-separated values: "ahmedabad, vadodara, vapi"
    return [v.strip() for v in (value or "").split(",") if v.strip()]

def _split_csv_terms(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def build_queries(geo: str, sector: str, keywords: str = "", *, max_queries: int = 8) -> list[str]:
    geos = _split_geo_terms(geo)
    sectors = _split_csv_terms(sector)
    extra = _split_csv_terms(keywords)

    if not geos:
        fallback_geo = " ".join((geo or "").split()).strip()
        geos = [fallback_geo] if fallback_geo else []

    if not sectors:
        fallback_sector = " ".join((sector or "").split()).strip()
        sectors = [fallback_sector] if fallback_sector else []

    if not geos or not sectors:
        return []

    # Build pools so we can interleave and avoid spending all query budget on one sector/city.
    base_pool: list[str] = []
    keyword_pool: list[str] = []
    broad_pool: list[str] = []

    for s in sectors:
        for g in geos:
            for term in _INTENT_TERMS:
                base_pool.append(f"{s} {term} {g}")
            broad_pool.append(f"{s} companies in {g}")
            broad_pool.append(f"{s} official website {g}")

    for s in sectors:
        for g in geos:
            for k in extra:
                keyword_pool.append(f"{s} {k} {g}")
                keyword_pool.append(f"{s} company {k} {g}")

    # Interleave pools: base -> keyword -> broad
    out: list[str] = []
    seen: set[str] = set()

    def push(q: str) -> None:
        qn = " ".join(q.split()).strip()
        key = qn.lower()
        if qn and key not in seen:
            seen.add(key)
            out.append(qn)

    max_len = max(len(base_pool), len(keyword_pool), len(broad_pool))
    for i in range(max_len):
        if i < len(base_pool):
            push(base_pool[i])
        if i < len(keyword_pool):
            push(keyword_pool[i])
        if i < len(broad_pool):
            push(broad_pool[i])
        if len(out) >= max_queries:
            break

    return out[:max_queries]

def normalize_website(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw if raw.startswith(("http://", "https://")) else f"https://{raw}")
    if not parsed.netloc:
        return ""

    host = parsed.netloc.lower()
    host_parts = host.split(".")
    if len(host_parts) > 2 and host_parts[0] in {"www", "m", "app", "chat"}:
        host = ".".join(host_parts[1:])

    cleaned = parsed._replace(netloc=host, path="", params="", query="", fragment="")
    return urlunparse(cleaned).rstrip("/")


def root_domain(url: str) -> str:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    parts = host.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


def is_likely_company_website(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    if not host:
        return False
    if any(token in host for token in _NON_COMPANY_HOST_KEYWORDS):
        return False
    if host.endswith(".gov") or host.endswith(".edu"):
        return False
    return True


def is_likely_company_name(name: str) -> bool:
    n = " ".join((name or "").split())
    if not n:
        return False
    if len(n) > 80:
        return False
    if _NON_COMPANY_NAME_RE.search(n) and len(n.split()) >= 4:
        return False
    return True


def _token_score(text: str, tokens: list[str]) -> float:
    if not tokens:
        return 0.0
    low = text.lower()
    hits = sum(1 for token in tokens if token and token.lower() in low)
    return hits / max(1, len(tokens))


class ExaLeadGeneratorService:
    """Generate raw leads from geo/sector filters using Exa search."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _max_results_cap(self) -> int:
        cap = int(getattr(self.settings, "leadgen_max_results_cap", 50) or 50)
        return max(1, cap)

    def _per_query_results(self) -> int:
        per_q = int(getattr(self.settings, "leadgen_per_query_results", 10) or 10)
        return max(1, per_q)

    def _max_queries(self) -> int:
        max_q = int(getattr(self.settings, "leadgen_max_queries", 8) or 8)
        return max(1, max_q)

    def _timeout_seconds(self) -> int:
        timeout_s = int(getattr(self.settings, "leadgen_request_timeout_seconds", 20) or 20)
        return max(5, timeout_s)

    def _make_client(self) -> Exa:
        key = (getattr(self.settings, "exa_api_key", "") or "").strip()
        if not key:
            raise ValueError("EXA_API_KEY is required for lead generation.")
        if Exa is None:
            raise ImportError("exa-py is not installed. Add exa-py to requirements and install deps.")
        return Exa(key)

    @staticmethod
    def _safe_list(value: object) -> list:
        if isinstance(value, list):
            return value
        return []

    def _search_response(self, client: Exa, query: str, num_results: int) -> object:
        attempts: list[dict[str, object]] = [
            {
                "query": query,
                "type": "auto",
                "category": "company",
                "num_results": num_results,
                "contents": {"highlights": {"max_characters": 700}},
            },
            {
                "query": query,
                "type": "auto",
                "num_results": num_results,
                "contents": {"highlights": {"max_characters": 700}},
            },
            {
                "query": query,
                "type": "auto",
                "num_results": num_results,
            },
            {
                "query": query,
                "num_results": num_results,
            },
        ]

        last_exc: Exception | None = None
        for kwargs in attempts:
            try:
                return client.search(**kwargs)
            except TypeError as exc:
                last_exc = exc
                continue

        if last_exc is not None:
            raise RuntimeError(f"Exa.search signature mismatch: {last_exc}") from last_exc
        raise RuntimeError("Exa.search failed with unknown argument mismatch.")

    def _from_output_schema(self, client: Exa, query: str, max_results: int) -> list[_SearchRow]:
        response = self._search_response(
            client,
            query,
            num_results=min(40, max(10, max_results * 2)),
        )
        rows = self._safe_list(getattr(response, "results", []))

        out: list[_SearchRow] = []
        for row in rows:
            title = str(getattr(row, "title", "")).strip()
            website = normalize_website(str(getattr(row, "url", "")).strip())
            highlights = getattr(row, "highlights", None) or []
            snippet = " ".join(str(h).strip() for h in highlights if h)[:500]
            if not title or not website:
                continue
            out.append(
                _SearchRow(
                    title=title,
                    url=website,
                    snippet=snippet,
                    source_query=query,
                    confidence_hint=0.78,
                ),
            )
            if len(out) >= max_results:
                break

        return out

    def _from_company_category(self, client: Exa, query: str, max_results: int) -> list[_SearchRow]:
        response = self._search_response(
            client,
            query,
            num_results=min(80, max(10, max_results * 2)),
        )

        rows = self._safe_list(getattr(response, "results", []))
        out: list[_SearchRow] = []
        for row in rows:
            title = str(getattr(row, "title", "")).strip()
            website = normalize_website(str(getattr(row, "url", "")).strip())
            highlights = getattr(row, "highlights", None) or []
            snippet = " ".join(str(h).strip() for h in highlights if h)[:500]
            if not title or not website:
                continue
            out.append(
                _SearchRow(
                    title=title,
                    url=website,
                    snippet=snippet,
                    source_query=query,
                    confidence_hint=0.72,
                ),
            )
            if len(out) >= max_results:
                break
        return out

    def _search_with_retries(self, client: Exa, query: str, max_results: int) -> list[_SearchRow]:
        last_exc: Exception | None = None
        for attempt in range(1, 4):
            merged: list[_SearchRow] = []
            seen_urls: set[str] = set()
            phase_errors: list[str] = []

            def _add(rows: list[_SearchRow]) -> None:
                for row in rows:
                    key = row.url.lower()
                    if key in seen_urls:
                        continue
                    seen_urls.add(key)
                    merged.append(row)

            try:
                _add(self._from_output_schema(client, query, max_results))
            except Exception as exc:  # noqa: BLE001
                phase_errors.append(str(exc))

            try:
                _add(self._from_company_category(client, query, max_results * 2))
            except Exception as exc:  # noqa: BLE001
                phase_errors.append(str(exc))

            if merged:
                return merged[:max_results]

            if phase_errors:
                last_exc = RuntimeError("; ".join(phase_errors))
            if attempt >= 3:
                break

            backoff = min(8.0, 0.5 * (2 ** (attempt - 1))) + random.uniform(0.0, 0.2)
            time.sleep(backoff)

        if last_exc is not None:
            raise RuntimeError(f"Exa search failed for query '{query}': {last_exc}") from last_exc
        return []

    def generate(
        self,
        *,
        geo: str,
        sector: str,
        keywords: str = "",
        max_results: int = 20,
        enable_email_discovery: bool | None = None,
    ) -> tuple[list[GeneratedLeadCandidate], list[LeadInput], list[str]]:
        requested = max(1, int(max_results))
        capped = min(requested, self._max_results_cap())

        queries = build_queries(geo, sector, keywords, max_queries=self._max_queries())
        if not queries:
            raise ValueError("Could not build queries from geo/sector values.")

        client = self._make_client()

        warnings: list[str] = []
        rows: list[_SearchRow] = []
        for query in queries:
            try:
                rows.extend(self._search_with_retries(client, query, self._per_query_results()))
            except Exception as exc:  # noqa: BLE001
                warnings.append(str(exc))

        geo_tokens = [t for t in geo.replace(",", " ").split() if t]
        sector_tokens = [t for t in sector.replace(",", " ").split() if t]

        generated: list[GeneratedLeadCandidate] = []
        seen_domains: set[str] = set()
        seen_company: set[str] = set()

        for row in rows:
            company_name = " ".join(row.title.split()).strip()
            website = normalize_website(row.url)
            if not company_name or not website:
                continue
            if not is_likely_company_name(company_name) or not is_likely_company_website(website):
                continue

            domain = root_domain(website)
            company_key = company_name.lower()
            if domain and domain in seen_domains:
                continue
            if company_key in seen_company:
                continue

            evidence = " ".join([row.title, row.snippet, row.source_query, row.url])
            geo_match = _token_score(evidence, geo_tokens)
            sector_match = _token_score(evidence, sector_tokens)
            confidence = min(0.99, row.confidence_hint + (0.06 * geo_match) + (0.08 * sector_match))

            candidate = GeneratedLeadCandidate(
                company_name=company_name,
                website=website,
                confidence=round(confidence, 4),
                source_query=row.source_query,
                source_url=row.url,
            )

            generated.append(candidate)
            if domain:
                seen_domains.add(domain)
            seen_company.add(company_key)

        generated.sort(key=lambda c: c.confidence, reverse=True)
        generated = generated[:capped]

        discovery_enabled = (
            enable_email_discovery
            if enable_email_discovery is not None
            else bool(getattr(self.settings, "leadgen_enable_email_discovery", True))
        )
        if discovery_enabled:
            max_b = int(getattr(self.settings, "contact_discovery_max_bytes", 500_000) or 500_000)
            for row in generated:
                discovered = discover_email_from_website(row.website, max_bytes=max_b)
                if discovered:
                    row.contact_email = discovered
                    row.confidence = min(0.99, round(row.confidence + 0.08, 4))

        generated.sort(key=lambda c: c.confidence, reverse=True)
        generated = generated[:capped]

        lead_inputs = [
            LeadInput(
                company_name=row.company_name,
                website=row.website,
                contact_email=row.contact_email,
            )
            for row in generated
        ]

        if not generated and warnings:
            warnings.insert(0, "Lead generation returned no rows.")

        return generated, lead_inputs, warnings
