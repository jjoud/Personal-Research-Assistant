from __future__ import annotations


class GeneralAssistant:
    """User-facing assistant that phrases final responses without risky tools."""

    def respond(self, request: str) -> str:
        return (
            "I can help with general questions, local notes, external research, "
            "and saving research reports. Try: "
            "\"What is in my note about last week's meeting?\""
        )

    def compose_knowledge_answer(
        self,
        query: str,
        snippets: list[dict[str, str]],
        citations: list[str],
    ) -> str:
        if not snippets:
            return f"I could not find a local note about '{query}'."

        lines = [f"Here is what I found in your notes about '{query}':", ""]
        for snippet in snippets:
            lines.append(f"- {snippet['text']}")
            lines.append(f"  Citation: {snippet['source']}")
        if citations:
            lines.append("")
            lines.append("Sources: " + ", ".join(citations))
        return "\n".join(lines)

    def compose_research_answer(
        self,
        query: str,
        findings: list[dict[str, str]],
        sources: list[str],
        error: str = "",
    ) -> str:
        if error and not findings:
            return f"I could not complete external research for '{query}'. Reason: {error}"
        if not findings:
            return f"I could not find sourced research findings for '{query}'."

        lines = [f"Summary for '{query}':", ""]
        for finding in findings:
            lines.append(f"- {finding['summary']}")
        if sources:
            lines.append("")
            lines.append("Sources:")
            for source in sources:
                lines.append(f"- {source}")
        if error:
            lines.append("")
            lines.append(f"Note: Some research failed: {error}")
        return "\n".join(lines)
