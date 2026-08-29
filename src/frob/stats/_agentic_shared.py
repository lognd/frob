"""Telemetry-stream primitives shared by `frob.stats._agentic` (time
breakdown) and `frob.stats._agentic_dispatch` (cost breakdown), T-3059.
Neither report family owns these -- both read the same
`.frob/telemetry.jsonl` stream and both need "parse a line", "parse a
timestamp", and "which tool events are completions" answered the same
way, so they live here rather than in either report module (avoiding the
import cycle a one-sided "cost imports time" or "time imports cost"
re-export would otherwise create)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from frob.logging import get_logger

_log = get_logger(__name__)

# frob:doc docs/modules/stats.md#public-api
# frob:ticket T-3059
TELEMETRY_REL = Path(".frob") / "telemetry.jsonl"
"""Path (relative to a repo root) the agentic report reads events from --
same relative path `frob.app.telemetry.TELEMETRY_REL` writes to."""


# frob:ticket T-3059
def _load_events(root: Path) -> list[dict[str, Any]]:
    """Every valid JSON line in `root`'s telemetry stream; malformed lines
    are skipped with a debug log, never raised -- a hand-edited or
    partially-written telemetry file must not break `frob stats`."""
    path = root / TELEMETRY_REL
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    # frob:waive SELFAUDIT001 follow_up="T-3409" reason="T-3059 moved this fs.read \
    # caller out of src/frob/stats/_agentic.py, which design/frob.strata's SYS100 \
    # fs.read capability list already declared -- the same capability, just relocated. \
    # design/frob.strata itself was under a live cross-worktree lease (T-3388) at \
    # split time so the declaration could not be updated here; follow_up tracks \
    # landing that one-line swap."
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except Exception:
            _log.debug("stats: telemetry line %d unparseable, skipped", lineno)
    return events


# frob:ticket T-3059
def _parse_iso(ts: str) -> float | None:
    """Seconds-since-epoch for an `iso_now()`-shaped timestamp, or None."""
    from datetime import datetime

    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


# frob:ticket T-3059
def _completed_tool_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every `kind="tool"` event that represents a COMPLETED call -- i.e.
    every event with no `phase` field at all (the pre-T-2912 shape, which
    only ever recorded completions) plus every `phase="post"` event
    (T-2912's `.claude/hooks/tool-call-telemetry.py`). `phase="pre"`
    events are attempts, not completions, and must be excluded here so a
    blocked/retried call is not double-counted as two calls' worth of cost
    -- `_tool_call_histogram` (in `_agentic.py`) is where `phase="pre"`
    events earn their keep, for retry/blocked detection specifically."""
    return [e for e in events if e.get("kind") == "tool" and e.get("phase") != "pre"]
