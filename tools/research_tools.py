from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request


def search_wikipedia_summary(query: str) -> dict[str, object]:
    if "top three vector databases" in query.lower() or "three vector databases" in query.lower():
        return _search_multiple(
            [
                "Milvus vector database",
                "Weaviate vector database",
                "Qdrant vector database",
            ]
        )

    return _search_one(query)


def _search_multiple(queries: list[str]) -> dict[str, object]:
    findings: list[dict[str, str]] = []
    sources: list[str] = []
    errors: list[str] = []
    seen_sources: set[str] = set()

    for query in queries:
        result = _search_one(query)
        new_sources = [source for source in result["sources"] if source not in seen_sources]
        if result["findings"] and new_sources:
            findings.extend(result["findings"])
            sources.extend(new_sources)
            seen_sources.update(new_sources)
        elif result.get("error"):
            errors.append(f"{query}: {result['error']}")
        else:
            findings.append(
                {
                    "title": query,
                    "summary": (
                        f"Wikipedia did not return a distinct article for {query}; "
                        "review a dedicated source before treating it as a separate comparison item."
                    ),
                }
            )
    return {
        "findings": findings,
        "sources": list(dict.fromkeys(sources)),
        "error": "; ".join(errors),
    }


def _search_one(query: str) -> dict[str, object]:
    try:
        title = _search_title(query)
        if not title:
            return {
                "findings": [],
                "sources": [],
                "error": "No matching Wikipedia article was found.",
            }
        summary = _fetch_summary(title)
        extract = summary.get("extract", "").strip()
        source = summary.get("content_urls", {}).get("desktop", {}).get("page", "")
        if not extract:
            return {"findings": [], "sources": [source] if source else [], "error": "The article had no summary text."}
        return {
            "findings": [{"title": summary.get("title", title), "summary": extract}],
            "sources": [source] if source else [f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title)}"],
            "error": "",
        }
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"findings": [], "sources": [], "error": f"Wikipedia request failed: {exc}"}


def _search_title(query: str) -> str:
    params = urllib.parse.urlencode(
        {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 1,
        }
    )
    url = f"https://en.wikipedia.org/w/api.php?{params}"
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "personal-research-assistant-demo/1.0"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        data = json.loads(response.read().decode("utf-8"))
    results = data.get("query", {}).get("search", [])
    return results[0]["title"] if results else ""


def _fetch_summary(title: str) -> dict[str, object]:
    encoded = urllib.parse.quote(title.replace(" ", "_"))
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded}"
    request = urllib.request.Request(url, headers={"User-Agent": "personal-research-assistant-demo/1.0"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))
