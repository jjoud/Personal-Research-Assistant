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
from schemas.messages import AgentMessage


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


@dataclass
class RequestResult:
    final_answer: str
    trace_lines: list[str] = field(default_factory=list)
    messages: list[AgentMessage] = field(default_factory=list)


class Orchestrator:
    """Routes user requests to specialist agents and owns shared state."""

    def __init__(self, workspace_root: Path, force: bool = False) -> None:
        self.workspace_root = workspace_root
        self.force = force
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        (self.workspace_root / "notes").mkdir(exist_ok=True)
        (self.workspace_root / "reports").mkdir(exist_ok=True)

        filesystem_server = FilesystemMCPServer(workspace_root)
        self.general_assistant = GeneralAssistant()
        self.knowledge_agent = KnowledgeAgent(self.workspace_root / "notes")
        self.research_agent = ResearchAgent()
        self.file_agent = FileWorkspaceAgent(filesystem_server, force=force)
        self.report_writer = ReportWriter()

    def handle_request(self, user_request: str) -> str:
        return self.run_request(user_request).final_answer

    def run_request(self, user_request: str, trace: bool = False) -> RequestResult:
        state = SharedState(messages=[{"role": "user", "content": user_request}])
        trace_lines: list[str] = []
        trace_messages: list[AgentMessage] = []
        self._trace_message(
            trace_lines,
            trace_messages,
            trace,
            sender="User",
            recipient="Orchestrator",
            type_="request",
            payload={"event": "Request", "query": user_request},
        )
        try:
            state.intent = self._classify_intent(user_request)
            self._trace_message(
                trace_lines,
                trace_messages,
                trace,
                sender="Orchestrator",
                recipient="Trace",
                type_="response",
                payload={"event": f"Intent: {state.intent}", "intent": state.intent},
            )
            if state.intent == "knowledge":
                final = self._handle_knowledge_request(user_request, state, trace_lines, trace)
                return RequestResult(final_answer=final, trace_lines=trace_lines, messages=trace_messages)
            if state.intent == "research_save":
                final = self._handle_research_and_save_request(user_request, state, trace_lines, trace)
                return RequestResult(final_answer=final, trace_lines=trace_lines, messages=trace_messages)
            if state.intent == "research":
                final = self._handle_research_request(user_request, state, trace_lines, trace)
                return RequestResult(final_answer=final, trace_lines=trace_lines, messages=trace_messages)
            if state.intent == "file_read":
                final = self._handle_file_read_request(user_request, state, trace_lines, trace)
                return RequestResult(final_answer=final, trace_lines=trace_lines, messages=trace_messages)
            if state.intent == "file_create":
                final = self._handle_file_create_request(user_request, state, trace_lines, trace)
                return RequestResult(final_answer=final, trace_lines=trace_lines, messages=trace_messages)
            if state.intent == "file_update":
                final = self._handle_file_update_request(user_request, state, trace_lines, trace)
                return RequestResult(final_answer=final, trace_lines=trace_lines, messages=trace_messages)
            if state.intent == "directory_create":
                final = self._handle_directory_create_request(user_request, state, trace_lines, trace)
                return RequestResult(final_answer=final, trace_lines=trace_lines, messages=trace_messages)
            self._trace(trace_lines, trace, "route: general assistant")
            self._trace_message(
                trace_lines,
                trace_messages,
                trace,
                sender="Orchestrator",
                recipient="General Assistant",
                type_="handoff",
                payload={"event": "Selected agents", "agents": ["General Assistant"]},
            )
            final = self.general_assistant.respond(user_request)
            self._trace_message(
                trace_lines,
                trace_messages,
                trace,
                sender="General Assistant",
                recipient="User",
                type_="response",
                payload={"event": "Final status", "status": "response prepared"},
            )
            return RequestResult(final_answer=final, trace_lines=trace_lines, messages=trace_messages)
        except Exception as exc:  # pragma: no cover - final safety net for CLI use
            state.errors.append(str(exc))
            self._trace(trace_lines, trace, f"error: {exc}")
            self._trace_message(
                trace_lines,
                trace_messages,
                trace,
                sender="Orchestrator",
                recipient="User",
                type_="error",
                payload={"event": "Final status", "status": "error", "error": str(exc)},
            )
            return RequestResult(
                final_answer=f"I could not complete the request safely: {exc}",
                trace_lines=trace_lines,
                messages=trace_messages,
            )

    def _classify_intent(self, request: str) -> str:
        text = request.lower()
        if self._extract_save_path(request) and any(
            word in text for word in ["research", "look up", "lookup"]
        ):
            return "research_save"
        if "my note" in text or "my notes" in text or "note about" in text:
            return "knowledge"
        if text.startswith("read file ") or text.startswith("open file "):
            return "file_read"
        if text.startswith("create file "):
            return "file_create"
        if text.startswith("update file "):
            return "file_update"
        if text.startswith("create directory "):
            return "directory_create"
        if any(phrase in text for phrase in ["look up", "lookup", "research", "summarize"]):
            return "research"
        return "general"

    def _handle_knowledge_request(
        self,
        request: str,
        state: SharedState,
        trace_lines: list[str],
        trace: bool,
    ) -> str:
        state.query = self._extract_topic(request)
        self._trace(trace_lines, trace, f"extracted query: {state.query}")
        self._trace(trace_lines, trace, "selected agents: Orchestrator -> Knowledge Agent -> General Assistant")
        result = self.knowledge_agent.answer(state.query)
        state.knowledge_snippets = result["snippets"]
        state.citations = result["citations"]
        self._trace(trace_lines, trace, "tools called: local notes search")
        self._trace(
            trace_lines,
            trace,
            f"knowledge snippets: {len(state.knowledge_snippets)} | citations: {', '.join(state.citations) if state.citations else 'none'}",
        )
        return self.general_assistant.compose_knowledge_answer(
            query=state.query,
            snippets=state.knowledge_snippets,
            citations=state.citations,
        )

    def _handle_research_request(
        self,
        request: str,
        state: SharedState,
        trace_lines: list[str],
        trace: bool,
    ) -> str:
        state.query = self._extract_topic(request)
        self._trace(trace_lines, trace, f"extracted query: {state.query}")
        self._trace(trace_lines, trace, "selected agents: Orchestrator -> Research Agent -> General Assistant")
        research_result = self.research_agent.research(state.query)
        state.research_findings = research_result["findings"]
        state.citations = research_result["sources"]
        if research_result.get("error"):
            state.errors.append(research_result["error"])
        self._trace(trace_lines, trace, "tools called: Wikipedia or official product sources")
        self._trace(
            trace_lines,
            trace,
            f"research findings: {len(state.research_findings)} | sources: {', '.join(state.citations) if state.citations else 'none'}",
        )
        return self.general_assistant.compose_research_answer(
            query=state.query,
            findings=state.research_findings,
            sources=state.citations,
            error=research_result.get("error", ""),
        )

    def _handle_research_and_save_request(
        self,
        request: str,
        state: SharedState,
        trace_lines: list[str],
        trace: bool,
    ) -> str:
        state.file_path = self._extract_save_path(request) or "reports/report.md"
        state.query = self._extract_research_topic_before_save(request)
        self._trace(trace_lines, trace, f"extracted query: {state.query}")
        self._trace(trace_lines, trace, f"extracted file path: {state.file_path}")
        self._trace(
            trace_lines,
            trace,
            "selected agents: Orchestrator -> Research Agent -> Report Writer -> File / Workspace Agent -> General Assistant",
        )

        research_result = self.research_agent.research(state.query)
        state.research_findings = research_result["findings"]
        state.citations = research_result["sources"]
        if research_result.get("error"):
            state.errors.append(research_result["error"])
            self._trace(trace_lines, trace, f"research error: {research_result['error']}")
            return self.general_assistant.compose_research_answer(
                query=state.query,
                findings=state.research_findings,
                sources=state.citations,
                error=research_result["error"],
            )
        self._trace(trace_lines, trace, "tools called: Wikipedia or official product sources")
        self._trace(
            trace_lines,
            trace,
            f"research findings: {len(state.research_findings)} | sources: {', '.join(state.citations) if state.citations else 'none'}",
        )

        state.draft_report = self.report_writer.create_markdown_report(
            title=state.query,
            findings=state.research_findings,
            sources=state.citations,
            mode=research_result.get("mode", "summary"),
        )
        self._trace(trace_lines, trace, "report writer: markdown draft created")
        write_result = self.file_agent.write_file_safely(
            path=state.file_path,
            content=state.draft_report,
            trace_lines=trace_lines if trace else None,
            trace=trace,
        )
        state.file_operation_status = write_result
        if not write_result["ok"]:
            self._trace(trace_lines, trace, f"file write failed: {write_result['message']}")
            return str(write_result["message"])
        self._trace(trace_lines, trace, f"file write decision: {write_result['path']}")
        self._trace(trace_lines, trace, "final status: report saved")
        return (
            "Report saved successfully.\n"
            f"Path: {write_result['path']}\n"
            f"Sources: {', '.join(state.citations) if state.citations else 'none'}"
        )

    def _handle_file_read_request(
        self,
        request: str,
        state: SharedState,
        trace_lines: list[str],
        trace: bool,
    ) -> str:
        path = self._extract_file_path(request, "read file")
        if not path:
            path = self._extract_file_path(request, "open file")
        self._trace(trace_lines, trace, f"route: file agent | action: read | path: {path}")
        self._trace(trace_lines, trace, "selected agents: Orchestrator -> File / Workspace Agent -> General Assistant")
        result = self.file_agent.read_file(path, trace_lines=trace_lines if trace else None, trace=trace)
        if not result["ok"]:
            self._trace(trace_lines, trace, f"file read failed: {result['message']}")
            return str(result["message"])
        self._trace(trace_lines, trace, f"file read ok: {result['path']}")
        return f"Contents of {result['path']}:\n\n{result['content']}"

    def _handle_file_create_request(
        self,
        request: str,
        state: SharedState,
        trace_lines: list[str],
        trace: bool,
    ) -> str:
        path, content = self._extract_path_and_content(request, "create file")
        self._trace(trace_lines, trace, f"route: file agent | action: create | path: {path}")
        self._trace(trace_lines, trace, "selected agents: Orchestrator -> File / Workspace Agent -> General Assistant")
        result = self.file_agent.create_file(path, content, trace_lines=trace_lines if trace else None, trace=trace)
        return self._format_file_result(result, "created")

    def _handle_file_update_request(
        self,
        request: str,
        state: SharedState,
        trace_lines: list[str],
        trace: bool,
    ) -> str:
        path, content = self._extract_path_and_content(request, "update file")
        self._trace(trace_lines, trace, f"route: file agent | action: update | path: {path}")
        self._trace(trace_lines, trace, "selected agents: Orchestrator -> File / Workspace Agent -> General Assistant")
        result = self.file_agent.update_file(path, content, trace_lines=trace_lines if trace else None, trace=trace)
        return self._format_file_result(result, "updated")

    def _handle_directory_create_request(
        self,
        request: str,
        state: SharedState,
        trace_lines: list[str],
        trace: bool,
    ) -> str:
        path = self._extract_file_path(request, "create directory")
        self._trace(trace_lines, trace, f"route: file agent | action: create_directory | path: {path}")
        self._trace(trace_lines, trace, "selected agents: Orchestrator -> File / Workspace Agent")
        result = self.file_agent.create_directory(path, trace_lines=trace_lines if trace else None, trace=trace)
        return self._format_file_result(result, "created")

    def _format_file_result(self, result: dict[str, object], action: str) -> str:
        if not result["ok"]:
            return str(result["message"])
        return f"File {action} successfully.\nPath: {result['path']}"

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

    def _extract_file_path(self, request: str, prefix: str) -> str:
        pattern = rf"^{re.escape(prefix)}\s+([^\n]+?)(?:\s+with\s+.*)?$"
        match = re.search(pattern, request.strip(), flags=re.IGNORECASE)
        if not match:
            return ""
        return match.group(1).strip().rstrip(".")

    def _extract_path_and_content(self, request: str, prefix: str) -> tuple[str, str]:
        pattern = rf"^{re.escape(prefix)}\s+(.+?)\s+with\s+(.+)$"
        match = re.search(pattern, request.strip(), flags=re.IGNORECASE)
        if not match:
            return "", ""
        return match.group(1).strip().rstrip("."), match.group(2).strip()

    def _trace(self, trace_lines: list[str], enabled: bool, message: str) -> None:
        if enabled:
            trace_lines.append(message)

    def _trace_message(
        self,
        trace_lines: list[str],
        trace_messages: list[AgentMessage],
        enabled: bool,
        sender: str,
        recipient: str,
        type_: str,
        payload: dict[str, object],
    ) -> None:
        message = AgentMessage(sender=sender, recipient=recipient, type=type_, payload=payload)
        trace_messages.append(message)
        if enabled:
            trace_lines.append(message.to_trace_line())
