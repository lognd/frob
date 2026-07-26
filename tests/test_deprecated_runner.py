"""T-0638: `frob deprecated` CLI wiring (`frob.app.deprecated_runner`) --
lists outstanding `frob:deprecated` entries via `frob.gates.list_deprecated`,
JSON and human-readable modes, no mutation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.deprecated_runner import run


# frob:ticket T-0638
def _write(root: Path, rel: str, text: str) -> Path:
    """Write `text` to `root/rel`, creating parent dirs, for a fixture repo."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


# frob:ticket T-0638
def _write_ticket(root: Path, ticket_id: str, state: str) -> None:
    tickets_path = root / "tickets.md"
    body = tickets_path.read_text() if tickets_path.exists() else "# Tickets\n"
    body += (
        f"\n<!-- ticket:{ticket_id} -->\n"
        "```yaml\n"
        f"id: {ticket_id}\n"
        "title: test ticket\n"
        f"state: {state}\n"
        "kind: bug\n"
        "origin: human\n"
        "created: '2026-01-01'\n"
        "parent: null\n"
        "scope:\n"
        "- src/**\n"
        "threat: null\n"
        "component: null\n"
        "```\n"
        "test body\n"
    )
    tickets_path.write_text(body)


# frob:ticket T-0638
class TestDeprecatedRunner:
    """`frob deprecated` CLI listing behavior (T-0638): JSON/human dual
    mode, clean-repo message, and the in-window/past-sunset/orphaned
    status tri-state."""

    # frob:ticket T-0638
    def test_json_mode_lists_deprecated_entries(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """`--json` is logged via `_log.info` under `quiet_stdout_logs`
        (RENDER001), matching `frob debt`'s established `--json`-via-logger
        test convention."""
        _write_ticket(tmp_path, "T-0001", "in-progress")
        _write(
            tmp_path,
            "src/a.py",
            "def helper(x):\n"
            '    # frob:deprecated 2026-01-01 sunset="2099-01-01" '
            'ticket="T-0001"\n'
            "    return x\n",
        )
        cfg = AppConfig(deprecated_path=tmp_path, deprecated_json=True)
        with caplog.at_level("INFO"):
            run(cfg)
        json_records = [r.message for r in caplog.records if r.message.startswith("[")]
        assert len(json_records) == 1
        out = json.loads(json_records[0])
        assert len(out) == 1
        assert out[0]["ticket"] == "T-0001"
        assert out[0]["expired"] is False
        assert out[0]["status"] == "in-window"

    # frob:ticket T-0638
    def test_no_deprecations_logs_clean_message(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        _write(tmp_path, "src/a.py", "def helper(x):\n    return x\n")
        cfg = AppConfig(deprecated_path=tmp_path, deprecated_json=False)
        run(cfg)
        assert "no outstanding frob:deprecated entries" in caplog.text

    # frob:ticket T-0638
    def test_human_mode_reports_past_sunset_status(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        _write_ticket(tmp_path, "T-0002", "in-progress")
        _write(
            tmp_path,
            "src/a.py",
            "def helper(x):\n"
            '    # frob:deprecated 2000-01-01 sunset="2000-06-01" '
            'ticket="T-0002"\n'
            "    return x\n",
        )
        cfg = AppConfig(deprecated_path=tmp_path, deprecated_json=False)
        run(cfg)
        assert "past-sunset" in caplog.text
        assert "T-0002" in caplog.text

    # frob:ticket T-0638
    def test_human_mode_reports_orphaned_status_for_closed_ticket(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """A `frob:deprecated` bound to a `done`/`dropped` (or unknown)
        ticket shows as `orphaned` -- T-0638's tri-state status
        requirement, distinct from the in-window/past-sunset split
        `DeprecatedEntry.expired` alone can express."""
        _write_ticket(tmp_path, "T-0003", "done")
        _write(
            tmp_path,
            "src/a.py",
            "def helper(x):\n"
            '    # frob:deprecated 2026-01-01 sunset="2099-01-01" '
            'ticket="T-0003"\n'
            "    return x\n",
        )
        cfg = AppConfig(deprecated_path=tmp_path, deprecated_json=False)
        run(cfg)
        assert "orphaned" in caplog.text
        assert "T-0003" in caplog.text
