from __future__ import annotations
import re
from urllib.parse import urlparse

from dataclasses import dataclass
from urllib.parse import urlparse


from smartlead.api.v1.schemas.leads import LeadInput
from smartlead.core.settings import Settings
from smartlead.services.email_discovery import discover_email_from_website
from smartlead.services.lead_generation import (
    GeneratedLeadCandidate,
    build_queries,
    is_likely_company_name,
    is_likely_company_website,
    normalize_website,
    root_domain,
)

try:
    from tavily import TavilyClient
except Exception:
    TavilyClient = None


_NON_COMPANY_HOST_TOKENS = (
    "indeed.com",
    "linkedin.com",
    "naukri.com",
    "glassdoor.com",
    "clutch.co",
    "goodfirms.co",
    "g2.com",
    "capterra.com",
    "justdial.com",
    "sulekha.com",
    "crunchbase.com",
    "wikipedia.org",
)
_NON_COMPANY_TITLE_RE = re.compile(
    r"\b("
    r"top|best|list|directory|vacancies|jobs?|hiring|rankings?|"
    r"compare|comparison|agencies|agency|consulting|outsourcing|services?"
    r")\b",
    flags=re.IGNORECASE,
)
_AGENCY_SIGNAL_RE = re.compile(
    r"\b("
    r"outsourcing|consulting|service provider|it services|agency|agencies|"
    r"digital agency|marketing agency|development services"
    r")\b",
    flags=re.IGNORECASE,
)
_PRODUCT_SIGNAL_RE = re.compile(
    r"\b("
    r"saa[sd]|platform|product|software product|b2b software|saas platform"
    r")\b",
    flags=re.IGNORECASE,
)

@dataclass(slots=True)
class _SearchRow:
    title: str
    url: str
    snippet: str
    source_query: str
    confidence_hint: float


def _token_score(text: str, tokens: list[str]) -> float:
    if not tokens:
        return 0.0
    low = text.lower()
    hits = sum(1 for token in tokens if token and token.lower() in low)
    return hits / max(1, len(tokens))

def _is_noise_or_agency_candidate(title: str, url: str, snippet: str) -> bool:
    host = (urlparse(url).hostname or "").lower().removeprefix("www.")
    text = f"{title} {snippet}".strip()

    if any(token in host for token in _NON_COMPANY_HOST_TOKENS):
        return True

    if _NON_COMPANY_TITLE_RE.search(title):
        return True

    # If it looks agency-like and has no product signal, reject.
    if _AGENCY_SIGNAL_RE.search(text) and not _PRODUCT_SIGNAL_RE.search(text):
        return True

    return False

class TavilyLeadGeneratorService:
    """Generate raw leads from geo/sector filters using Tavily search."""

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

    def _make_client(self) -> TavilyClient:
        key = (getattr(self.settings, "tavily_api_key", "") or "").strip()
        if not key:
            raise ValueError("TAVILY_API_KEY is required for lead generation.")
        if TavilyClient is None:
            raise ImportError("tavily-python is not installed. Add tavily-python to requirements.")
        return TavilyClient(api_key=key)

    def _search_once(self, client: TavilyClient, query: str, max_results: int) -> list[_SearchRow]:
        resp = client.search(
            query=query,
            max_results=max_results,
            search_depth="basic",
            include_answer=False,
            include_images=False,
        )
        rows = resp.get("results") if isinstance(resp, dict) else getattr(resp, "results", None)
        if not isinstance(rows, list):
            return []

        out: list[_SearchRow] = []
        for item in rows:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            url = normalize_website(str(item.get("url") or "").strip())
            snippet = str(item.get("content") or "").strip()[:500]
            score = item.get("score")
            base_conf = 0.68
            if isinstance(score, (int, float)):
                base_conf = max(0.55, min(0.9, float(score)))
            if not title or not url:
                continue
            out.append(
                _SearchRow(
                    title=title,
                    url=url,
                    snippet=snippet,
                    source_query=query,
                    confidence_hint=base_conf,
                )
            )
        return out

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

        seen_url: set[str] = set()
        for query in queries:
            try:
                for row in self._search_once(client, query, self._per_query_results()):
                    key = row.url.lower()
                    if key in seen_url:
                        continue
                    seen_url.add(key)
                    rows.append(row)
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"Tavily query failed '{query}': {exc}")

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
            if _is_noise_or_agency_candidate(row.title, website, row.snippet):
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
            confidence = row.confidence_hint + (0.04 * geo_match) + (0.06 * sector_match)
            # Penalize generic titles a bit
            if len(company_name.split()) >= 7:
                confidence -= 0.06

            confidence = max(0.35, min(0.95, confidence))

            generated.append(
                GeneratedLeadCandidate(
                    company_name=company_name,
                    website=website,
                    confidence=round(confidence, 4),
                    source_query=row.source_query,
                    source_url=row.url,
                )
            )
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