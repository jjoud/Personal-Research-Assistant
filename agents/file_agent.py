from __future__ import annotations

from mcp_servers.filesystem_server import FilesystemMCPServer


class FileWorkspaceAgent:
    """Only agent allowed to perform workspace file operations."""

    def __init__(self, filesystem_server: FilesystemMCPServer, force: bool = False) -> None:
        self.filesystem_server = filesystem_server
        self.force = force

    def read_file(
        self,
        path: str,
        trace_lines: list[str] | None = None,
        trace: bool = False,
    ) -> dict[str, object]:
        if not path.strip():
            return {"ok": False, "message": "Please provide a file path.", "path": path}
        if trace and trace_lines is not None:
            trace_lines.append(f"file server: read_file({path})")
        return self.filesystem_server.read_file(path)

    def _write_with_overwrite_check(
        self,
        path: str,
        content: str,
        trace_lines: list[str] | None = None,
        trace: bool = False,
    ) -> dict[str, object]:
        if not path.strip():
            return {"ok": False, "message": "Please provide a file path.", "path": path}
        safety = self.filesystem_server.check_path_safety(path)
        if not safety["ok"]:
            if trace and trace_lines is not None:
                trace_lines.append(f"path safety failed: {safety['message']}")
            return safety
        if trace and trace_lines is not None:
            trace_lines.append(f"path safety ok: {safety['relative_path']}")

        existing_files = self.filesystem_server.list_files(".")
        normalized = str(safety["relative_path"])
        if normalized in existing_files["files"]:
            if trace and trace_lines is not None:
                trace_lines.append(f"existing file detected: {normalized}")
            if self.force:
                if trace and trace_lines is not None:
                    trace_lines.append("force mode: overwrite approved automatically")
                return self.filesystem_server.write_file(path, content)
            try:
                answer = input(f"{normalized} already exists. Overwrite? [y/N] ").strip().lower()
            except EOFError:
                answer = ""
            if answer not in {"y", "yes"}:
                return {
                    "ok": False,
                    "path": normalized,
                    "message": "Write cancelled because overwrite was not approved.",
                }

        if trace and trace_lines is not None:
            trace_lines.append(f"write_file requested: {normalized}")
        return self.filesystem_server.write_file(path, content)

    def write_file_safely(
        self,
        path: str,
        content: str,
        trace_lines: list[str] | None = None,
        trace: bool = False,
    ) -> dict[str, object]:
        return self._write_with_overwrite_check(path, content, trace_lines=trace_lines, trace=trace)

    def create_file(
        self,
        path: str,
        content: str,
        trace_lines: list[str] | None = None,
        trace: bool = False,
    ) -> dict[str, object]:
        if trace and trace_lines is not None:
            trace_lines.append(f"file server: create_file({path})")
        return self._write_with_overwrite_check(path, content, trace_lines=trace_lines, trace=trace)

    def create_directory(
        self,
        path: str,
        trace_lines: list[str] | None = None,
        trace: bool = False,
    ) -> dict[str, object]:
        if not path.strip():
            return {"ok": False, "message": "Please provide a directory path.", "path": path}
        safety = self.filesystem_server.check_path_safety(path)
        if not safety["ok"]:
            if trace and trace_lines is not None:
                trace_lines.append(f"path safety failed: {safety['message']}")
            return safety
        if trace and trace_lines is not None:
            trace_lines.append(f"file server: create_directory({safety['relative_path']})")
        return self.filesystem_server.create_directory(path)

    def update_file(
        self,
        path: str,
        content: str,
        trace_lines: list[str] | None = None,
        trace: bool = False,
    ) -> dict[str, object]:
        if not path.strip():
            return {"ok": False, "message": "Please provide a file path.", "path": path}
        safety = self.filesystem_server.check_path_safety(path)
        if not safety["ok"]:
            if trace and trace_lines is not None:
                trace_lines.append(f"path safety failed: {safety['message']}")
            return safety
        target = self.filesystem_server.workspace_root / safety["relative_path"]
        if not target.exists():
            if trace and trace_lines is not None:
                trace_lines.append(f"update blocked: missing file {safety['relative_path']}")
            return {"ok": False, "message": "Cannot update a missing file.", "path": str(safety["relative_path"])}
        if trace and trace_lines is not None:
            trace_lines.append(f"path safety ok: {safety['relative_path']}")
        if self.force:
            if trace and trace_lines is not None:
                trace_lines.append("force mode: update approved automatically")
            return self.filesystem_server.update_file(path, content)
        try:
            answer = input(f"{safety['relative_path']} will be updated. Continue? [y/N] ").strip().lower()
        except EOFError:
            answer = ""
        if answer not in {"y", "yes"}:
            return {
                "ok": False,
                "path": str(safety["relative_path"]),
                "message": "Update cancelled because confirmation was not approved.",
            }
        if trace and trace_lines is not None:
            trace_lines.append(f"update_file requested: {safety['relative_path']}")
        return self.filesystem_server.update_file(path, content)
