"""
agvs_core/services/events.py
Typed progress event contract shared between CLI shims and a local FastAPI / macOS Studio Cockpit UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class ProgressEvent:
    stage: str
    step: str
    pct: float
    message: str
    payload: dict[str, Any] = field(default_factory=dict)


ProgressCallback = Callable[[ProgressEvent], None]


def noop_progress(_event: ProgressEvent) -> None:
    """Default no-op progress handler for headless/unit-test execution."""


def print_cli_progress(event: ProgressEvent) -> None:
    """Console progress formatter for `.agents/skills/` CLI invocations."""
    print(f"[{event.stage}:{event.step}] ({event.pct:5.1f}%) {event.message}")
