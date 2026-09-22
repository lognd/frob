""".claude/hooks/sync-claude-config.py: coverage for T-5124's
duplicate hook-registration dedupe (`dedupe_hook_registrations` /
`sync_dedupe_hook_registrations`).

HOOK-AUDIT.md section 0b (HIGH): `frob-suggest.py` was registered in BOTH
the project `.claude/settings.json` and the materialized `~/.claude/
settings.json`, so `_record_attempt` ran twice per Bash call inside this
repo and the documented "re-run it exactly and it will be allowed" path
never executed. These tests exercise the dedupe against the REAL script
(loaded by path, same technique as `tests/unit/
test_sync_claude_config_stale_guard_t3408.py` -- a hyphenated filename
blocks a normal `import`), not a re-typed approximation of it."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

_REAL_HOOK = (
    Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "sync-claude-config.py"
)


def _load_hook_module() -> ModuleType:
    """Import the real `sync-claude-config.py` by path."""
    spec = importlib.util.spec_from_file_location(
        "_sync_claude_config_under_test_dedupe", _REAL_HOOK
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def hook():  # noqa: ANN201
    """The real hook module, freshly loaded per test."""
    return _load_hook_module()


def _settings(*, event: str, commands: list[str]) -> dict:
    """A minimal settings.json-shaped dict registering `commands` for
    `event`, one hook per command, all in a single group -- enough
    structure for `dedupe_hook_registrations` to read."""
    return {
        "hooks": {
            event: [
                {
                    "matcher": "Bash",
                    "hooks": [{"type": "command", "command": cmd} for cmd in commands],
                }
            ]
        }
    }


class TestDedupeHookRegistrations:
    """`dedupe_hook_registrations` -- the pure decision, no I/O."""

    # frob:tests tests/test_hook_sync_claude_config.py::TestDedupeHookRegistrations.test_duplicate_basename_same_event_is_removed  # noqa: E501
    # frob:tests .claude/hooks/sync-claude-config.py::dedupe_hook_registrations  # noqa: E501
    def test_duplicate_basename_same_event_is_removed(self, hook) -> None:  # noqa: ANN001
        """MUST-FIRE: the project already registers `frob-suggest.py` for
        PreToolUse; the user copy's own registration of the SAME basename
        for the SAME event is a pure duplicate and is stripped."""
        project = _settings(
            event="PreToolUse",
            commands=["python3 /repo/.claude/hooks/frob-suggest.py"],
        )
        user = _settings(
            event="PreToolUse",
            commands=["python3 /home/user/.claude/hooks/frob-suggest.py"],
        )
        new_user, removed = hook.dedupe_hook_registrations(project, user)
        assert removed == ["PreToolUse/frob-suggest.py"]
        assert new_user["hooks"]["PreToolUse"] == []

    # frob:tests tests/test_hook_sync_claude_config.py::TestDedupeHookRegistrations.test_distinct_basenames_are_kept  # noqa: E501
    # frob:tests .claude/hooks/sync-claude-config.py::dedupe_hook_registrations  # noqa: E501
    def test_distinct_basenames_are_kept(self, hook) -> None:  # noqa: ANN001
        """MUST-STAY-QUIET: a user-level hook the project does not
        register at all (a different basename) survives untouched."""
        project = _settings(
            event="PreToolUse", commands=["python3 /repo/.claude/hooks/frob-suggest.py"]
        )
        user = _settings(
            event="PreToolUse",
            commands=["python3 /home/user/.claude/hooks/protect-secrets.py"],
        )
        new_user, removed = hook.dedupe_hook_registrations(project, user)
        assert removed == []
        kept = new_user["hooks"]["PreToolUse"][0]["hooks"]
        assert len(kept) == 1
        assert kept[0]["command"].endswith("protect-secrets.py")

    # frob:tests tests/test_hook_sync_claude_config.py::TestDedupeHookRegistrations.test_empty_group_after_removal_is_dropped  # noqa: E501
    # frob:tests .claude/hooks/sync-claude-config.py::dedupe_hook_registrations  # noqa: E501
    def test_empty_group_after_removal_is_dropped(self, hook) -> None:  # noqa: ANN001
        """A hook GROUP left with zero surviving entries is dropped
        entirely rather than kept as a dead `"hooks": []` entry."""
        project = _settings(
            event="PreToolUse", commands=["python3 /repo/.claude/hooks/frob-suggest.py"]
        )
        user = _settings(
            event="PreToolUse",
            commands=["python3 /home/user/.claude/hooks/frob-suggest.py"],
        )
        new_user, _removed = hook.dedupe_hook_registrations(project, user)
        assert new_user["hooks"]["PreToolUse"] == []

    def test_different_event_is_not_deduped(self, hook) -> None:  # noqa: ANN001
        """MUST-STAY-QUIET: the same basename registered for a DIFFERENT
        event than the project uses is not a duplicate of it."""
        project = _settings(
            event="PreToolUse", commands=["python3 /repo/.claude/hooks/frob-suggest.py"]
        )
        user = _settings(
            event="Stop", commands=["python3 /home/user/.claude/hooks/frob-suggest.py"]
        )
        new_user, removed = hook.dedupe_hook_registrations(project, user)
        assert removed == []
        assert len(new_user["hooks"]["Stop"][0]["hooks"]) == 1


class TestSyncDedupeHookRegistrations:
    """`sync_dedupe_hook_registrations` -- the real-file-I/O wrapper."""

    # frob:tests tests/test_hook_sync_claude_config.py::TestSyncDedupeHookRegistrations.test_writes_deduped_user_settings  # noqa: E501
    # frob:tests .claude/hooks/sync-claude-config.py::sync_dedupe_hook_registrations  # noqa: E501
    def test_writes_deduped_user_settings(self, hook, tmp_path: Path) -> None:  # noqa: ANN001
        """A real duplicate on disk is removed and the user settings.json
        is rewritten to reflect it."""
        project_path = tmp_path / "project-settings.json"
        user_path = tmp_path / "user-settings.json"
        project_path.write_text(
            json.dumps(
                _settings(
                    event="PreToolUse",
                    commands=["python3 /repo/.claude/hooks/frob-suggest.py"],
                )
            ),
            encoding="utf-8",
        )
        user_path.write_text(
            json.dumps(
                _settings(
                    event="PreToolUse",
                    commands=["python3 /home/user/.claude/hooks/frob-suggest.py"],
                )
            ),
            encoding="utf-8",
        )
        removed = hook.sync_dedupe_hook_registrations(project_path, user_path)
        assert removed == ["PreToolUse/frob-suggest.py"]
        written = json.loads(user_path.read_text(encoding="utf-8"))
        assert written["hooks"]["PreToolUse"] == []

    # frob:tests tests/test_hook_sync_claude_config.py::TestSyncDedupeHookRegistrations.test_dry_run_does_not_write  # noqa: E501
    # frob:tests .claude/hooks/sync-claude-config.py::sync_dedupe_hook_registrations  # noqa: E501
    def test_dry_run_does_not_write(self, hook, tmp_path: Path) -> None:  # noqa: ANN001
        """`dry_run=True` (the `--check` path) reports what WOULD be
        removed without touching the file on disk."""
        project_path = tmp_path / "project-settings.json"
        user_path = tmp_path / "user-settings.json"
        project_path.write_text(
            json.dumps(
                _settings(
                    event="PreToolUse",
                    commands=["python3 /repo/.claude/hooks/frob-suggest.py"],
                )
            ),
            encoding="utf-8",
        )
        original_user_text = json.dumps(
            _settings(
                event="PreToolUse",
                commands=["python3 /home/user/.claude/hooks/frob-suggest.py"],
            )
        )
        user_path.write_text(original_user_text, encoding="utf-8")
        removed = hook.sync_dedupe_hook_registrations(
            project_path, user_path, dry_run=True
        )
        assert removed == ["PreToolUse/frob-suggest.py"]
        assert user_path.read_text(encoding="utf-8") == original_user_text

    def test_missing_files_return_empty(self, hook, tmp_path: Path) -> None:  # noqa: ANN001
        """Neither settings.json existing (a fresh machine) is not an
        error -- best-effort, `[]`, matching this module's posture for
        every other optional-file read."""
        removed = hook.sync_dedupe_hook_registrations(
            tmp_path / "no-project.json", tmp_path / "no-user.json"
        )
        assert removed == []
