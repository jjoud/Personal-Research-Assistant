from __future__ import annotations

import argparse
from pathlib import Path

from agents.orchestrator import Orchestrator


def build_orchestrator() -> Orchestrator:
    project_root = Path(__file__).resolve().parent
    workspace_root = project_root / "workspace"
    return Orchestrator(workspace_root=workspace_root)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Personal Research Assistant command-line demo"
    )
    parser.add_argument(
        "request",
        nargs="*",
        help="User request, for example: Look up MCP and summarize it.",
    )
    args = parser.parse_args()

    orchestrator = build_orchestrator()

    if args.request:
        user_request = " ".join(args.request)
        print(orchestrator.handle_request(user_request))
        return

    print("Personal Research Assistant. Type 'exit' to quit.")
    while True:
        try:
            user_request = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if user_request.lower() in {"exit", "quit"}:
            break
        if not user_request:
            continue

        print(orchestrator.handle_request(user_request))


if __name__ == "__main__":
    main()
