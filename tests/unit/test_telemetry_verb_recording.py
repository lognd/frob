"""T-4689: every `frob` invocation records verb and subverb on both
telemetry paths -- `kind="cli"` (`frob.app.telemetry.record_cli_event`,
driven by `frob.app.app.App.__call__`) and `kind="tool"` (`.claude/hooks/
tool-call-telemetry.py`'s parse of a `Bash` tool call's command). Before
this ticket, 91% of all telemetry rows carried an empty `subcommand`: every
`kind="tool"` row (the hook never parsed a verb at all) plus the collapsed
`kind="cli"` rows (only the first word was ever recorded, so `frob ticket
show` and `frob ticket land` were indistinguishable)."""

from __future__ import annotations

import importlib.util
import json
import types
from pathlib import Path

import pytest

from frob.app.app import App
from frob.app.config import AppConfig, Subcommand
from frob.app.telemetry import TELEMETRY_REL, record_cli_event

_HOOK_PATH = (
    Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "tool-call-telemetry.py"
)


def _load_hook_module() -> types.ModuleType:
    """Load `.claude/hooks/tool-call-telemetry.py` by path, matching how
    Claude Code itself invokes it (a bare script, never a package import --
    see the hook's own module docstring's "NO `frob` IMPORT" note)."""
    spec = importlib.util.spec_from_file_location(
        "tool_call_telemetry_under_test", _HOOK_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _last_event(root: Path) -> dict:
    """The last JSON line appended to `root`'s telemetry stream."""
    lines = (root / TELEMETRY_REL).read_text(encoding="utf-8").splitlines()
    return json.loads(lines[-1])


# frob:tests tests/unit/test_telemetry_verb_recording.py::test_record_cli_event_carries_verb_and_subverb  # noqa: E501
# frob:tests src/frob/app/telemetry/__init__.py::record_cli_event
def test_record_cli_event_carries_verb_and_subverb(tmp_path: Path) -> None:
    """`record_cli_event`'s new `subverb` kwarg lands in the written record
    as both `verb` (mirroring `subcommand`, unchanged for back-compat) and
    `subverb`."""
    record_cli_event(
        tmp_path,
        subcommand="ticket",
        subverb="show",
        args_head="ticket show T-4689",
        duration_ms=1.0,
        exit_code=0,
    )
    event = _last_event(tmp_path)
    assert event["kind"] == "cli"
    assert event["subcommand"] == "ticket"
    assert event["verb"] == "ticket"
    assert event["subverb"] == "show"


def test_record_cli_event_subverb_defaults_to_none(tmp_path: Path) -> None:
    """A leaf verb with no group sub-dispatch field (e.g. `frob dup`)
    records `subverb=None` rather than a guess."""
    record_cli_event(
        tmp_path,
        subcommand="dup",
        args_head="dup",
        duration_ms=1.0,
        exit_code=0,
    )
    event = _last_event(tmp_path)
    assert event["subverb"] is None


# frob:tests tests/unit/test_telemetry_verb_recording.py::TestAppDispatchRecordsSubverb.test_ticket_show_records_verb_ticket_subverb_show  # noqa: E501
class TestAppDispatchRecordsSubverb:
    """`App.__call__` (T-4689) reads the subverb straight off the already-
    parsed `AppConfig` (`<verb>_command`), never by re-lexing `sys.argv`."""

    def test_ticket_show_records_verb_ticket_subverb_show(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The positive control this ticket's acceptance criteria name:
        a fixture telemetry root, `frob ticket show T-xxxx` dispatched
        through `App`, and the appended row carries verb=ticket,
        subverb=show."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "frob.app.ticket_runner.run", lambda _cfg: None, raising=False
        )
        cfg = AppConfig(subcommand=Subcommand.ticket, ticket_command="show")
        App(cfg)()
        event = _last_event(tmp_path)
        assert event["kind"] == "cli"
        assert event["verb"] == "ticket"
        assert event["subverb"] == "show"

    def test_leaf_verb_with_no_group_field_records_subverb_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """`frob dup` has no `dup_command` field on `AppConfig` at all --
        `getattr` returns `None`, recorded verbatim rather than guessed."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("frob.app.dup_runner.run", lambda _cfg: None, raising=False)
        cfg = AppConfig(subcommand=Subcommand.dup)
        App(cfg)()
        event = _last_event(tmp_path)
        assert event["verb"] == "dup"
        assert event["subverb"] is None


# frob:tests tests/unit/test_telemetry_verb_recording.py::TestHookParsesFrobVerbFromBash.test_uv_run_frob kind="unit"  # noqa: E501
class TestHookParsesFrobVerbFromBash:
    """`.claude/hooks/tool-call-telemetry.py::_frob_verb_subverb` (T-4689):
    the five command shapes the ticket names, plus the "not a frob command
    at all" negative case that must record neither field rather than a
    guess."""

    @pytest.fixture(autouse=True)
    def _hook(self):
        self.hook = _load_hook_module()

    def test_uv_run_frob(self) -> None:
        """`uv run frob ticket show T-4689` -> verb=ticket, subverb=show."""
        assert self.hook._frob_verb_subverb("uv run frob ticket show T-4689") == (
            "ticket",
            "show",
        )

    def test_dot_venv_bin_frob(self) -> None:
        """A path ending in `/frob` (`.venv/bin/frob`) is recognized by
        basename, same as the bare `frob` token."""
        assert self.hook._frob_verb_subverb(".venv/bin/frob ticket show T-4689") == (
            "ticket",
            "show",
        )

    def test_python_dash_m_frob(self) -> None:
        """`python -m frob ticket show T-4689` -> the `frob` token after
        `-m` is found the same generic way as any other."""
        assert self.hook._frob_verb_subverb("python -m frob ticket show T-4689") == (
            "ticket",
            "show",
        )

    def test_nice_wrapped_frob(self) -> None:
        """`nice -n 10 <path>/frob ...` -- `nice`/`-n`/`10` never match the
        basename test, so the real `frob` token is found regardless."""
        assert self.hook._frob_verb_subverb(
            "nice -n 10 /home/logan/projects/frob/.venv/bin/frob ticket show T-4689"
        ) == ("ticket", "show")

    def test_compound_command_several_frob_calls(self) -> None:
        """A compound command with several frob calls: the FIRST resolvable
        `frob <verb> [<subverb>]` wins. `check --only dup` has no subverb
        of its own (`dup` is `--only`'s VALUE, not a positional subverb --
        it is not adjacent to `check`), so this also proves the flag-value
        case is not misclassified as a subverb."""
        assert self.hook._frob_verb_subverb(
            "frob check --only dup && frob ticket show T-4689"
        ) == ("check", None)

    def test_non_frob_bash_command_records_neither(self) -> None:
        """A Bash command that never invokes frob at all records nothing
        rather than a guess."""
        assert self.hook._frob_verb_subverb("git status") is None
        assert self.hook._frob_verb_subverb("echo hello world") is None

    def test_build_record_omits_verb_subverb_for_non_frob_command(self) -> None:
        """`_build_record` (the function that shapes the actual written
        telemetry row) leaves `verb`/`subverb` out entirely for a non-frob
        `Bash` command -- never writes them as `None`/empty-string."""
        payload = {
            "hook_event_name": "PreToolUse",
            "session_id": "s1",
            "tool_name": "Bash",
            "tool_input": {"command": "git status"},
        }
        record = self.hook._build_record(payload, phase="pre", root=Path("."))
        assert "verb" not in record
        assert "subverb" not in record

    def test_build_record_includes_verb_subverb_for_frob_command(self) -> None:
        """`_build_record` for a `Bash` call that does invoke frob carries
        both fields through into the row."""
        payload = {
            "hook_event_name": "PreToolUse",
            "session_id": "s1",
            "tool_name": "Bash",
            "tool_input": {"command": "uv run frob ticket show T-4689"},
        }
        record = self.hook._build_record(payload, phase="pre", root=Path("."))
        assert record["verb"] == "ticket"
        assert record["subverb"] == "show"
