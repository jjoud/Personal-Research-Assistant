from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from agents.file_agent import FileWorkspaceAgent
from agents.general_assistant import GeneralAssistant
from agents.knowledge_agent import KnowledgeAgent
from agents.report_writer import ReportWriter
from agents.research_agent import ResearchAgent
from mcp_servers.filesystem_server import FilesystemMCPServer


@dataclass
class SharedState:
    messages: list[dict[str, str]] = field(default_factory=list)
    intent: str = "general"
    query: str = ""
    research_findings: list[dict[str, str]] = field(default_factory=list)
    knowledge_snippets: list[dict[str, str]] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    draft_report: str = ""
    file_path: str = ""
    file_operation_status: dict[str, object] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


class Orchestrator:
    """Routes user requests to specialist agents and owns shared state."""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        (self.workspace_root / "notes").mkdir(exist_ok=True)
        (self.workspace_root / "reports").mkdir(exist_ok=True)

        filesystem_server = FilesystemMCPServer(workspace_root)
        self.general_assistant = GeneralAssistant()
        self.knowledge_agent = KnowledgeAgent(self.workspace_root / "notes")
        self.research_agent = ResearchAgent()
        self.file_agent = FileWorkspaceAgent(filesystem_server)
        self.report_writer = ReportWriter()

    def handle_request(self, user_request: str) -> str:
        state = SharedState(messages=[{"role": "user", "content": user_request}])
        try:
            state.intent = self._classify_intent(user_request)
            if state.intent == "knowledge":
                return self._handle_knowledge_request(user_request, state)
            if state.intent == "research_save":
                return self._handle_research_and_save_request(user_request, state)
            if state.intent == "research":
                return self._handle_research_request(user_request, state)
            if state.intent == "file_read":
                return self._handle_file_read_request(user_request, state)
            return self.general_assistant.respond(user_request)
        except Exception as exc:  # pragma: no cover - final safety net for CLI use
            state.errors.append(str(exc))
            return f"I could not complete the request safely: {exc}"

    def _classify_intent(self, request: str) -> str:
        text = request.lower()
        if self._extract_save_path(request) and any(
            word in text for word in ["research", "look up", "lookup"]
        ):
            return "research_save"
        if "my note" in text or "my notes" in text or "note about" in text:
            return "knowledge"
        if text.startswith("read ") or text.startswith("open "):
            return "file_read"
        if any(phrase in text for phrase in ["look up", "lookup", "research", "summarize"]):
            return "research"
        return "general"

    def _handle_knowledge_request(self, request: str, state: SharedState) -> str:
        state.query = self._extract_topic(request)
        result = self.knowledge_agent.answer(state.query)
        state.knowledge_snippets = result["snippets"]
        state.citations = result["citations"]
        return self.general_assistant.compose_knowledge_answer(
            query=state.query,
            snippets=state.knowledge_snippets,
            citations=state.citations,
        )

    def _handle_research_request(self, request: str, state: SharedState) -> str:
        state.query = self._extract_topic(request)
        research_result = self.research_agent.research(state.query)
        state.research_findings = research_result["findings"]
        state.citations = research_result["sources"]
        if research_result.get("error"):
            state.errors.append(research_result["error"])
        return self.general_assistant.compose_research_answer(
            query=state.query,
            findings=state.research_findings,
            sources=state.citations,
            error=research_result.get("error", ""),
        )

    def _handle_research_and_save_request(self, request: str, state: SharedState) -> str:
        state.file_path = self._extract_save_path(request) or "reports/report.md"
        state.query = self._extract_research_topic_before_save(request)

        research_result = self.research_agent.research(state.query)
        state.research_findings = research_result["findings"]
        state.citations = research_result["sources"]
        if research_result.get("error"):
            state.errors.append(research_result["error"])
            return self.general_assistant.compose_research_answer(
                query=state.query,
                findings=state.research_findings,
                sources=state.citations,
                error=research_result["error"],
            )

        state.draft_report = self.report_writer.create_markdown_report(
            title=state.query,
            findings=state.research_findings,
            sources=state.citations,
        )
        write_result = self.file_agent.write_file_safely(
            path=state.file_path,
            content=state.draft_report,
        )
        state.file_operation_status = write_result
        if not write_result["ok"]:
            return str(write_result["message"])
        return (
            "Report saved successfully.\n"
            f"Path: {write_result['path']}\n"
            f"Sources: {', '.join(state.citations) if state.citations else 'none'}"
        )

    def _handle_file_read_request(self, request: str, state: SharedState) -> str:
        path = request.split(maxsplit=1)[1] if " " in request else ""
        result = self.file_agent.read_file(path)
        if not result["ok"]:
            return str(result["message"])
        return f"Contents of {result['path']}:\n\n{result['content']}"

    def _extract_topic(self, request: str) -> str:
        text = request.strip().rstrip(".?")
        patterns = [
            r"what is in my note about\s+(.+)",
            r"what's in my note about\s+(.+)",
            r"look up\s+(.+?)\s+and summarize",
            r"lookup\s+(.+?)\s+and summarize",
            r"research\s+(.+)",
            r"summarize\s+(.+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return text

    def _extract_research_topic_before_save(self, request: str) -> str:
        cleaned = re.sub(r"\s+to\s+[\w./\\ -]+\.md\s*$", "", request, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+and\s+save\s+.*$", "", cleaned, flags=re.IGNORECASE)
        return self._extract_topic(cleaned)

    def _extract_save_path(self, request: str) -> str:
        match = re.search(r"\bto\s+([\w./\\ -]+\.md)\b", request, flags=re.IGNORECASE)
        if not match:
            return ""
        return match.group(1).strip().replace("\\", "/")
