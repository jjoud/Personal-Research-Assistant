# Demo Transcript

## Exact Commands

```bash
python main.py --demo
python main.py --trace "What is in my note about last week's meeting?"
python main.py --trace "Look up the Model Context Protocol and summarize it."
python main.py --force --trace "Research the top three vector databases and save a report to reports/vector-dbs.md."
python main.py "Read file reports/vector-dbs.md"
python main.py "Create file notes/demo.md with This is a demo note."
python main.py --force "Update file notes/demo.md with Updated demo content."
```

## Sample Outputs

### Flow A: Personal Knowledge

```text
[TRACE] Request: What is in my note about last week's meeting? | User -> Orchestrator; query=What is in my note about last week's meeting?
[TRACE] Intent: knowledge | Orchestrator -> Trace; intent=knowledge
[TRACE] extracted query: last week's meeting
[TRACE] selected agents: Orchestrator -> Knowledge Agent -> General Assistant
[TRACE] tools called: local notes search
[TRACE] knowledge snippets: 1 | citations: workspace/notes/last-weeks-meeting.md
Here is what I found in your notes about 'last week's meeting':
- # Last Week's Meeting The team agreed to build a Personal Research Assistant as a small multi-agent system. The main architecture uses an Orchestrator, Knowledge Agent, Research Agent, File / Workspace Agent, General Assistant, and Report Writer.
  Citation: workspace/notes/last-weeks-meeting.md

Sources: workspace/notes/last-weeks-meeting.md
```

Demonstrates:
- Orchestrator intent routing
- Knowledge Agent note retrieval
- Relative citation output

### Flow B: External Research

```text
[TRACE] Request: Look up the Model Context Protocol and summarize it. | User -> Orchestrator; query=Look up the Model Context Protocol and summarize it.
[TRACE] Intent: research | Orchestrator -> Trace; intent=research
[TRACE] extracted query: the Model Context Protocol
[TRACE] selected agents: Orchestrator -> Research Agent -> General Assistant
[TRACE] tools called: Wikipedia or official product sources
[TRACE] research findings: 1 | sources: https://en.wikipedia.org/wiki/Model_Context_Protocol
Summary for 'the Model Context Protocol':
- The Model Context Protocol (MCP) is an open standard and open-source framework introduced by Anthropic in November 2024 to standardize the way artificial intelligence (AI) systems like large language models (LLMs) integrate and share data with external tools, systems, and data sources. MCP provides a standardized interface for reading files, executing functions, and handling contextual prompts. Following its announcement, the protocol was adopted by major AI providers, including OpenAI and Google DeepMind.

Sources:
- https://en.wikipedia.org/wiki/Model_Context_Protocol
```

Demonstrates:
- Research Agent web lookup
- Source-grounded summary

### Flow C: Research and Save Report

```text
[TRACE] Request: Research the top three vector databases and save a report to reports/vector-dbs.md. | User -> Orchestrator; query=Research the top three vector databases and save a report to reports/vector-dbs.md.
[TRACE] Intent: research_save | Orchestrator -> Trace; intent=research_save
[TRACE] extracted query: the top three vector databases
[TRACE] extracted file path: reports/vector-dbs.md
[TRACE] selected agents: Orchestrator -> Research Agent -> Report Writer -> File / Workspace Agent -> General Assistant
[TRACE] tools called: Wikipedia or official product sources
[TRACE] research findings: 3 | sources: https://milvus.io/, https://weaviate.io/, https://qdrant.tech/
[TRACE] report writer: markdown draft created
[TRACE] path safety ok: reports/vector-dbs.md
[TRACE] existing file detected: reports/vector-dbs.md
[TRACE] force mode: overwrite approved automatically
[TRACE] file write decision: reports/vector-dbs.md
[TRACE] final status: report saved
Report saved successfully.
Path: reports/vector-dbs.md
Sources: https://milvus.io/, https://weaviate.io/, https://qdrant.tech/
```

Demonstrates:
- Research Agent collection
- Report Writer synthesis
- File / Workspace Agent safe write
- MCP-compatible filesystem boundary

## Agent Mapping

- `main.py`: CLI and demo runner
- `agents/orchestrator.py`: routing, trace, shared state
- `agents/knowledge_agent.py`: note lookup
- `agents/research_agent.py`: external lookup
- `agents/report_writer.py`: report formatting
- `agents/file_agent.py`: safe workspace file ops
- `mcp_servers/filesystem_server.py`: workspace boundary
- `schemas/messages.py`: typed trace/routing message objects
