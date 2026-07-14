# Last Week's Meeting

The team agreed to build a Personal Research Assistant as a small multi-agent system.
The main architecture uses an Orchestrator, Knowledge Agent, Research Agent, File /
Workspace Agent, General Assistant, and Report Writer.

Key decisions:
- Use a Supervisor / Worker topology.
- Keep workspace file writes inside a safe sandbox.
- Require citations for personal notes and external research.
- Start with a simple command-line demo before adding optional voice features.
