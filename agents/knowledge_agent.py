from __future__ import annotations

from pathlib import Path

from tools.knowledge_tools import search_notes


class KnowledgeAgent:
    """Searches local notes and returns cited snippets."""

    def __init__(self, notes_root: Path) -> None:
        self.notes_root = notes_root
        self.project_root = notes_root.parent.parent

    def answer(self, query: str) -> dict[str, list]:
        matches = search_notes(self.notes_root, query)
        snippets = [
            {"text": match.snippet, "source": self._relative_source(match.path)}
            for match in matches
        ]
        citations = sorted({snippet["source"] for snippet in snippets})
        return {"snippets": snippets, "citations": citations}

    def _relative_source(self, path: Path) -> str:
        try:
            return path.resolve().relative_to(self.project_root.resolve()).as_posix()
        except ValueError:
            return path.name
