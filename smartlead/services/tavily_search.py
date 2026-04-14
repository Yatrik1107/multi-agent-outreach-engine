from __future__ import annotations

from smartlead.core.settings import Settings


def fetch_search_context(settings: Settings, query: str, max_results: int = 6) -> str:
    if not settings.tavily_configured:
        return ""
    from tavily import TavilyClient

    client = TavilyClient(api_key=(settings.tavily_api_key or "").strip())
    resp = client.search(
        query=query,
        max_results=max_results,
        search_depth="basic",
        include_answer=False,
    )
    results = resp.get("results") if isinstance(resp, dict) else getattr(resp, "results", None)
    if not results:
        return "(Tavily returned no results.)"
    lines: list[str] = []
    for i, item in enumerate(results, start=1):
        if not isinstance(item, dict):
            continue
        title = (item.get("title") or "").strip()
        url = (item.get("url") or "").strip()
        content = (item.get("content") or "").strip()
        if len(content) > 900:
            content = content[:900] + "…"
        lines.append(f"{i}. {title}\n   URL: {url}\n   Snippet: {content}")
    return "\n\n".join(lines) if lines else "(Tavily returned no parseable results.)"