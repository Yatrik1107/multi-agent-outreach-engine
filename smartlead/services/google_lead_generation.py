from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass

from google import genai
from google.genai import types

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


def _extract_json_payload(text: str) -> object | None:
    raw = (text or "").strip()
    if not raw:
        return None

    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw, flags=re.IGNORECASE).strip()
        raw = re.sub(r"```$", "", raw).strip()

    try:
        return json.loads(raw)
    except Exception:
        pass

    start_obj = raw.find("{")
    end_obj = raw.rfind("}")
    if start_obj != -1 and end_obj > start_obj:
        try:
            return json.loads(raw[start_obj : end_obj + 1])
        except Exception:
            pass

    start_arr = raw.find("[")
    end_arr = raw.rfind("]")
    if start_arr != -1 and end_arr > start_arr:
        try:
            return json.loads(raw[start_arr : end_arr + 1])
        except Exception:
            return None

    return None


def _parse_json_rows(text: str) -> list[_SearchRow]:
    payload = _extract_json_payload(text)
    if payload is None:
        return []

    items: list[object]
    if isinstance(payload, dict):
        leads = payload.get("leads")
        if isinstance(leads, list):
            items = leads
        else:
            items = []
    elif isinstance(payload, list):
        items = payload
    else:
        items = []

    out: list[_SearchRow] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("company") or item.get("company_name") or "").strip()
        website = normalize_website(str(item.get("url") or item.get("website") or "").strip())
        email = str(item.get("email") or item.get("contact_email") or "").strip()
        source_query = str(item.get("source_query") or "").strip()
        confidence_raw = item.get("confidence")
        confidence_hint = 0.74
        if isinstance(confidence_raw, (int, float)):
            c = float(confidence_raw)
            if c > 1:
                c = c / 100.0
            confidence_hint = max(0.4, min(0.95, c))
        if not title or not website:
            continue
        out.append(
            _SearchRow(
                title=title,
                url=website,
                snippet=email,
                source_query=source_query,
                confidence_hint=confidence_hint,
            )
        )
    return out


class GoogleLeadGeneratorService:
    """Generate raw leads using Google Search grounding through Gemini."""

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
        cap = int(getattr(self.settings, "google_grounding_max_queries_cap", 6) or 6)
        return max(1, min(max_q, cap))

    def _model_name(self) -> str:
        return (getattr(self.settings, "google_search_grounding_model", "") or "gemini-2.5-flash").strip()

    def _fallback_models(self) -> list[str]:
        raw = (getattr(self.settings, "google_search_grounding_fallback_models", "") or "").strip()
        if not raw:
            return []
        out: list[str] = []
        seen: set[str] = set()
        for part in raw.split(","):
            model = part.strip()
            if not model:
                continue
            key = model.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(model)
        return out

    @staticmethod
    def _is_quota_exhausted(message: str) -> bool:
        low = (message or "").lower()
        return (
            "resource_exhausted" in low
            or "quota exceeded" in low
            or "generate_content_free_tier_requests" in low
        )

    @staticmethod
    def _retry_seconds(message: str) -> int | None:
        text = message or ""
        m1 = re.search(r"retry in\s+([0-9]+(?:\.[0-9]+)?)s", text, flags=re.IGNORECASE)
        if m1:
            return max(1, math.ceil(float(m1.group(1))))
        m2 = re.search(r"retryDelay'\s*:\s*'(\d+)s'", text)
        if m2:
            return max(1, int(m2.group(1)))
        return None

    @staticmethod
    def _compact_error(exc: Exception, *, max_len: int = 260) -> str:
        txt = " ".join(str(exc).split())
        if len(txt) <= max_len:
            return txt
        return txt[: max_len - 3] + "..."

    def _make_client(self) -> genai.Client:
        key = (getattr(self.settings, "gemini_api_key", "") or "").strip()
        if not key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY is required for lead generation.")
        return genai.Client(api_key=key)

    def _search_once(
        self,
        client: genai.Client,
        queries: list[str],
        *,
        max_results: int,
        model_name: str,
    ) -> list[_SearchRow]:
        query_block = "\n".join(f"- {q}" for q in queries)
        prompt = (
            "Use Google search grounding to find real companies for these lead search intents.\n"
            "Search intents:\n"
            f"{query_block}\n\n"
            f"Return STRICTLY JSON with this shape and at most {max_results} objects:\n"
            '{"leads":[{"company":"...","url":"https://...","email":"...","source_query":"...","confidence":0.0}]}\n'
            "Rules:\n"
            "- Only real companies\n"
            "- Official website only\n"
            "- Prefer public contact emails if visible\n"
            "- No duplicates\n"
            "- No explanation, no markdown, no code fences\n"
        )

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}],
                temperature=0.2,
            ),
        )

        text = getattr(response, "text", "") or ""
        return _parse_json_rows(text)

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
        seen_urls: set[str] = set()
        active_model = self._model_name()

        try:
            for row in self._search_once(
                client,
                queries,
                max_results=capped,
                model_name=active_model,
            ):
                key = row.url.lower()
                if key in seen_urls:
                    continue
                seen_urls.add(key)
                rows.append(row)
        except Exception as exc:  # noqa: BLE001
            raw = str(exc)
            if self._is_quota_exhausted(raw):
                switched = False
                for candidate in self._fallback_models():
                    if candidate.strip().lower() == active_model.strip().lower():
                        continue
                    try:
                        for row in self._search_once(
                            client,
                            queries,
                            max_results=capped,
                            model_name=candidate,
                        ):
                            key = row.url.lower()
                            if key in seen_urls:
                                continue
                            seen_urls.add(key)
                            rows.append(row)
                        warnings.append(
                            f"Switched Google grounding model from '{active_model}' to '{candidate}' after quota exhaustion."
                        )
                        active_model = candidate
                        switched = True
                        break
                    except Exception as fallback_exc:  # noqa: BLE001
                        if self._is_quota_exhausted(str(fallback_exc)):
                            continue
                        warnings.append(
                            f"Google grounding fallback model '{candidate}' failed: {self._compact_error(fallback_exc)}"
                        )
                if not switched:
                    wait_s = self._retry_seconds(raw)
                    detail = (
                        f"Google grounding quota exhausted for model '{active_model}'. "
                        f"Retry after ~{wait_s}s."
                        if wait_s
                        else f"Google grounding quota exhausted for model '{active_model}'."
                    )
                    warnings.append(detail)
            elif "UNAVAILABLE" in raw and "high demand" in raw:
                warnings.append(
                    f"Google grounding temporarily unavailable: {self._compact_error(exc)}"
                )
            else:
                warnings.append(f"Google grounding search failed: {self._compact_error(exc)}")

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
            confidence = min(0.99, row.confidence_hint + (0.05 * geo_match) + (0.07 * sector_match))

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