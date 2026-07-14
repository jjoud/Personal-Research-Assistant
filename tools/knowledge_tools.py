from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class NoteMatch:
    path: Path
    snippet: str
    score: int


def search_notes(notes_root: Path, query: str, limit: int = 3) -> list[NoteMatch]:
    notes_root.mkdir(parents=True, exist_ok=True)
    query_terms = _terms(query)
    matches: list[NoteMatch] = []

    for path in sorted(notes_root.glob("**/*")):
        if not path.is_file() or path.suffix.lower() not in {".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8")
        haystack = text.lower()
        score = sum(1 for term in query_terms if term in haystack)
        if query.lower() in haystack:
            score += 3
        if score <= 0:
            continue
        matches.append(
            NoteMatch(
                path=path,
                snippet=_best_snippet(text, query_terms),
                score=score,
            )
        )

    matches.sort(key=lambda item: item.score, reverse=True)
    return matches[:limit]


def _terms(query: str) -> list[str]:
    stop_words = {
        "a",
        "about",
        "an",
        "and",
        "in",
        "is",
        "last",
        "my",
        "note",
        "of",
        "the",
        "what",
        "week",
        "weeks",
    }
    return [
        word.strip(".,?!'\"").lower()
        for word in query.split()
        if word.strip(".,?!'\"").lower() not in stop_words
    ] or [query.lower()]


def _best_snippet(text: str, terms: list[str]) -> str:
    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    for index, paragraph in enumerate(paragraphs):
        lowered = paragraph.lower()
        if any(term in lowered for term in terms):
            if paragraph.startswith("#") and index + 1 < len(paragraphs):
                return f"{paragraph} {paragraphs[index + 1]}".replace("\n", " ")
            return paragraph.replace("\n", " ")
    return text.strip().replace("\n", " ")[:500]
