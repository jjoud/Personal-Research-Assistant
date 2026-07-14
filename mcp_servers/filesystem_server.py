from __future__ import annotations

from pathlib import Path


class FilesystemMCPServer:
    """Small MCP-style filesystem server with a separated tool interface.

    This is intentionally lightweight for the assignment demo. Agents call this
    class through the File / Workspace Agent instead of touching files directly.
    """

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    def check_path_safety(self, path: str) -> dict[str, object]:
        try:
            resolved = (self.workspace_root / path).resolve()
            resolved.relative_to(self.workspace_root)
        except ValueError:
            return {
                "ok": False,
                "message": "Path is outside the safe workspace.",
                "path": path,
            }
        return {
            "ok": True,
            "path": str(resolved),
            "relative_path": resolved.relative_to(self.workspace_root).as_posix(),
            "message": "Path is inside the safe workspace.",
        }

    def list_files(self, path: str = ".") -> dict[str, object]:
        safety = self.check_path_safety(path)
        if not safety["ok"]:
            return safety
        root = Path(str(safety["path"]))
        files = [
            item.relative_to(self.workspace_root).as_posix()
            for item in sorted(root.rglob("*"))
            if item.is_file()
        ]
        return {"ok": True, "files": files, "path": str(safety["relative_path"])}

    def read_file(self, path: str) -> dict[str, object]:
        safety = self.check_path_safety(path)
        if not safety["ok"]:
            return safety
        target = Path(str(safety["path"]))
        if not target.exists() or not target.is_file():
            return {"ok": False, "message": "File does not exist.", "path": path}
        return {
            "ok": True,
            "content": target.read_text(encoding="utf-8"),
            "path": str(safety["relative_path"]),
        }

    def write_file(self, path: str, content: str) -> dict[str, object]:
        safety = self.check_path_safety(path)
        if not safety["ok"]:
            return safety
        target = Path(str(safety["path"]))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {
            "ok": True,
            "path": str(safety["relative_path"]),
            "message": "File written successfully.",
        }

    def update_file(self, path: str, content: str) -> dict[str, object]:
        safety = self.check_path_safety(path)
        if not safety["ok"]:
            return safety
        target = Path(str(safety["path"]))
        if not target.exists():
            return {"ok": False, "message": "Cannot update a missing file.", "path": path}
        target.write_text(content, encoding="utf-8")
        return {
            "ok": True,
            "path": str(safety["relative_path"]),
            "message": "File updated successfully.",
        }
