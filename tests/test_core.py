from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agents.file_agent import FileWorkspaceAgent
from agents.general_assistant import GeneralAssistant
from agents.knowledge_agent import KnowledgeAgent
from agents.orchestrator import Orchestrator
from agents.report_writer import ReportWriter
from tools.research_tools import search_wikipedia_summary
from mcp_servers.filesystem_server import FilesystemMCPServer


class CoreProjectTests(unittest.TestCase):
    def test_path_safety_blocks_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            server = FilesystemMCPServer(Path(tmp))
            result = server.check_path_safety("../outside.md")
            self.assertFalse(result["ok"])

    def test_file_agent_blocks_unsafe_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            server = FilesystemMCPServer(workspace)
            agent = FileWorkspaceAgent(server, force=True)
            result = agent.create_file("../secret.md", "nope")
            self.assertFalse(result["ok"])
            self.assertIn("outside the safe workspace", result["message"])

    def test_knowledge_citation_is_relative(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            notes = root / "workspace" / "notes"
            notes.mkdir(parents=True)
            note_path = notes / "demo.md"
            note_path.write_text("This note mentions the team sync.", encoding="utf-8")

            agent = KnowledgeAgent(notes)
            result = agent.answer("team sync")
            self.assertTrue(result["citations"])
            self.assertTrue(result["citations"][0].startswith("workspace/notes/"))

    def test_no_matching_note_returns_clear_message(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            notes = root / "workspace" / "notes"
            notes.mkdir(parents=True)
            agent = KnowledgeAgent(notes)
            result = agent.answer("missing topic")
            self.assertEqual(result["snippets"], [])

    def test_file_create_read_update(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            server = FilesystemMCPServer(workspace)
            agent = FileWorkspaceAgent(server, force=True)

            create_result = agent.create_file("notes/demo.md", "hello")
            self.assertTrue(create_result["ok"])

            read_result = agent.read_file("notes/demo.md")
            self.assertTrue(read_result["ok"])
            self.assertEqual(read_result["content"], "hello")

            update_result = agent.update_file("notes/demo.md", "updated")
            self.assertTrue(update_result["ok"])
            self.assertEqual((workspace / "notes" / "demo.md").read_text(encoding="utf-8"), "updated")

    def test_orchestrator_routes_file_commands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            (workspace / "notes").mkdir(parents=True)
            (workspace / "reports").mkdir(parents=True)
            (workspace / "notes" / "demo.md").write_text("demo note", encoding="utf-8")

            orchestrator = Orchestrator(workspace_root=workspace, force=True)
            create_reply = orchestrator.handle_request("Create file notes/new.md with hello")
            self.assertIn("File created successfully", create_reply)
            read_reply = orchestrator.handle_request("Read file notes/new.md")
            self.assertIn("hello", read_reply)
            update_reply = orchestrator.handle_request("Update file notes/new.md with updated")
            self.assertIn("File updated successfully", update_reply)
            dir_reply = orchestrator.handle_request("Create directory notes/archive")
            self.assertIn("File created successfully", dir_reply)

    def test_trace_mode_records_routing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            (workspace / "notes").mkdir(parents=True)
            (workspace / "reports").mkdir(parents=True)
            (workspace / "notes" / "demo.md").write_text("demo note", encoding="utf-8")

            orchestrator = Orchestrator(workspace_root=workspace, force=True)
            result = orchestrator.run_request("Read file notes/demo.md", trace=True)
            self.assertTrue(result.trace_lines)
            self.assertTrue(any("Intent:" in line for line in result.trace_lines))
            self.assertTrue(any("file server: read_file" in line for line in result.trace_lines))
            self.assertIn("demo note", result.final_answer)

    def test_unknown_intent_falls_back_to_general_assistant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            orchestrator = Orchestrator(workspace_root=workspace, force=True)
            result = orchestrator.handle_request("tell me something surprising")
            self.assertIn("I can help with general questions", result)

    def test_vector_report_shape(self) -> None:
        writer = ReportWriter()
        result = writer.create_markdown_report(
            title="the top three vector databases",
            findings=[
                {
                    "database": "Milvus",
                    "type_positioning": "Open-source distributed vector database for high-scale AI similarity search.",
                    "key_strengths": ["Scalable similarity search"],
                    "common_use_cases": ["RAG"],
                    "source": "https://milvus.io/",
                    "source_label": "official/product source",
                }
            ],
            sources=["https://milvus.io/"],
            mode="vector_database_comparison",
        )
        self.assertIn("Executive Summary", result)
        self.assertIn("Comparison Table", result)
        self.assertIn("Milvus", result)
        self.assertIn("Sources", result)

    def test_vector_database_research_returns_three_sources(self) -> None:
        result = search_wikipedia_summary("top three vector databases")
        self.assertEqual(result["mode"], "vector_database_comparison")
        self.assertEqual(len(result["findings"]), 3)
        self.assertEqual(len(result["sources"]), 3)


if __name__ == "__main__":
    unittest.main()
