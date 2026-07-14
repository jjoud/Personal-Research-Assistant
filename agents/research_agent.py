from __future__ import annotations

from tools.research_tools import search_wikipedia_summary


class ResearchAgent:
    """Searches external sources and returns sourced findings."""

    def research(self, query: str) -> dict[str, object]:
        return search_wikipedia_summary(query)
