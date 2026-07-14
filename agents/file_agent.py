from __future__ import annotations

from mcp_servers.filesystem_server import FilesystemMCPServer


class FileWorkspaceAgent:
    """Only agent allowed to perform workspace file operations."""

    def __init__(self, filesystem_server: FilesystemMCPServer) -> None:
        self.filesystem_server = filesystem_server

    def read_file(self, path: str) -> dict[str, object]:
        return self.filesystem_server.read_file(path)

    def write_file_safely(self, path: str, content: str) -> dict[str, object]:
        safety = self.filesystem_server.check_path_safety(path)
        if not safety["ok"]:
            return safety

        existing_files = self.filesystem_server.list_files(".")
        normalized = str(safety["relative_path"])
        if normalized in existing_files["files"]:
            answer = input(f"{normalized} already exists. Overwrite? [y/N] ").strip().lower()
            if answer not in {"y", "yes"}:
                return {
                    "ok": False,
                    "path": normalized,
                    "message": "Write cancelled because overwrite was not approved.",
                }

        return self.filesystem_server.write_file(path, content)

    def update_file(self, path: str, content: str) -> dict[str, object]:
        return self.filesystem_server.update_file(path, content)
