from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid


@dataclass(slots=True)
class AgentMessage:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str | None = None
    sender: str = ""
    recipient: str = ""
    type: str = "request"
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_trace_line(self) -> str:
        event = str(self.payload.get("event", self.type))
        headline = event
        if event.lower().startswith("intent") and "intent" in self.payload:
            headline = f"Intent: {self.payload['intent']}"
        elif event.lower() == "request" and "query" in self.payload:
            headline = f"Request: {self.payload['query']}"
        elif event.lower() == "final status" and "status" in self.payload:
            headline = f"Final status: {self.payload['status']}"
        elif event.lower() == "file write decision" and "path" in self.payload:
            headline = f"File write decision: {self.payload['path']}"
        details: list[str] = []
        if self.sender and self.recipient:
            details.append(f"{self.sender} -> {self.recipient}")
        for key in ("intent", "query", "path", "status", "result", "tools", "agents"):
            value = self.payload.get(key)
            if value:
                if isinstance(value, list):
                    value = ", ".join(str(item) for item in value)
                details.append(f"{key}={value}")
        tail = f" | {'; '.join(details)}" if details else ""
        return f"[TRACE] {headline}{tail}"
