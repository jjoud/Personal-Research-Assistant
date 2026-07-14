# Personal Research Assistant

A small command-line implementation of the Personal Research Assistant multi-agent
system from the Masar Applied AI Engineering design project.

The original `week2-project.pdf` is a design-track assignment with no code
deliverable. This repo turns that design into a practical end-to-end demo while
keeping the scope small.

## Project Overview

The app supports three required flows:

1. Ask about a local note.
2. Look up a topic on Wikipedia and summarize it with sources.
3. Research a topic, write a Markdown report, and save it inside the safe
   workspace.

The interface is a simple Python CLI in `main.py`.

## Architecture Mapping

This implementation follows the previous architecture with a simplified
Supervisor / Worker topology:

- `Orchestrator`: receives the request, classifies intent, maintains simple
  shared state, routes to the correct worker, handles errors, and returns the
  final response.
- `GeneralAssistant`: handles general conversation and formats final user-facing
  answers. It does not use network tools or file-write tools directly.
- `KnowledgeAgent`: searches local files in `workspace/notes` and returns cited
  snippets.
- `ResearchAgent`: uses Wikipedia public endpoints for free external research.
- `FileWorkspaceAgent`: is the only agent allowed to read or write workspace
  files.
- `ReportWriter`: creates a structured Markdown report from research findings.

The shared state is intentionally small and lives in memory for the current
request. It includes fields such as `intent`, `query`, `knowledge_snippets`,
`research_findings`, `citations`, `draft_report`, `file_path`, and
`file_operation_status`.

## MCP Server Used

The demo implements a lightweight local MCP-style filesystem server in
`mcp_servers/filesystem_server.py`.

It exposes a separated tool interface:

- `check_path_safety`
- `list_files`
- `read_file`
- `write_file`
- `update_file`

For demo simplicity, this is not the official MCP Python package. The important
architecture boundary is preserved: agents do not write directly to the
filesystem. File operations go through `FileWorkspaceAgent`, which calls the
MCP-style server.

## Installation

Use Python 3.10 or newer.

```bash
pip install -r requirements.txt
```

No third-party packages, paid APIs, secrets, or API keys are required.

## Run

Interactive mode:

```bash
python main.py
```

Single request mode:

```bash
python main.py "What is in my note about last week's meeting?"
```

## Example Commands

Knowledge-base request:

```bash
python main.py "What is in my note about last week's meeting?"
```

External research request:

```bash
python main.py "Look up the Model Context Protocol and summarize it."
```

Research and save request:

```bash
python main.py "Research the top three vector databases and save a report to reports/vector-dbs.md."
```

If the output file already exists, the File / Workspace Agent asks for overwrite
confirmation before writing.

## Sample Data

Two sample notes are included:

- `workspace/notes/last-weeks-meeting.md`
- `workspace/notes/mcp-notes.md`

The first note answers the required example: "What is in my note about last
week's meeting?"

## Known Limitations

- Intent classification is rule-based, not LLM-based.
- Research uses Wikipedia only, so it is a small free-source demo rather than a
  broad web research system.
- Shared state is in memory and not checkpointed to disk.
- Communication schemas are represented through simple dictionaries rather than
  Pydantic models to avoid extra dependencies.
- The filesystem server is MCP-style, not an official MCP server package.
- The optional voice-agent bonus is not implemented because the required text
  flows come first.

## What Changed From The Architecture

- The architecture described a production-ready design; this implementation keeps
  only what is needed for an end-to-end CLI demo.
- The Orchestrator uses deterministic routing rules instead of an LLM router.
- The Report Writer is a class, not a separate long-running agent.
- Persistence, checkpointers, and durable memory are omitted.
- Only the filesystem capability is implemented as an MCP-style server. Wikipedia
  research remains a plain local tool because reuse and permission isolation are
  less important for this small demo.
