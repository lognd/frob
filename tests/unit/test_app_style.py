"""TTY-aware color wiring at the app/presentation layer (T-0179).

Covers: the shared `frob.app._style` palette in isolation, and that
`frob ticket list/show/doable` (`frob.app.ticket_runner`) plus `frob
stats` (`frob.app.stats_runner`) grow ANSI color when their output stream
is treated as color-enabled and drop it identically to plain text
otherwise -- the hard constraint the ticket calls out: piped/non-TTY and
`--json` output must stay byte-identical to before this change, in every
mode.

`FORCE_COLOR` (already part of `frob.logging.color.should_color`'s
documented precedence, ahead of the isatty() check) stands in for "a real
TTY" here: these tests capture output at the OS file-descriptor level
(`capfd`), where pytest's own redirection makes stdout a pipe, not a
TTY -- `FORCE_COLOR` is should_color's own sanctioned way to force the
colored branch without needing an actual pty.
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from frob.app import stats_runner, ticket_runner
from frob.app._style import (
    STATE_STYLE,
    style_fail,
    style_header,
    style_ok,
    style_rule,
    style_state,
    style_ticket_id,
    style_warn,
)
from frob.app.config import AppConfig
from frob.tickets._models import Origin, Ticket, TicketKind, TicketState
from frob.tickets._store import write_ticket

_ESC = "\x1b["


# ---------------------------------------------------------------------------
# _style.py: pure functions, no stream involved
# ---------------------------------------------------------------------------


def test_style_ticket_id_paints():
    # frob:tests tests/unit/test_app_style.py::test_style_ticket_id_paints kind="unit"
    assert _ESC in style_ticket_id("T-0042", True)
    assert style_ticket_id("T-0042", False) == "T-0042"


def test_style_state_palette():
    # frob:tests tests/unit/test_app_style.py::test_style_state_palette kind="unit"
    for state in STATE_STYLE:
        assert _ESC in style_state(state, True)
        assert style_state(state, False) == state
    # An unrecognized state passes through verbatim even with color on.
    assert style_state("nonexistent-state", True) == "nonexistent-state"


# frob:tests src/frob/app/_style.py::style_ok kind="unit"
# frob:tests src/frob/app/_style.py::style_fail kind="unit"
# frob:tests src/frob/app/_style.py::style_warn kind="unit"
# frob:tests src/frob/app/_style.py::style_header kind="unit"
# frob:tests src/frob/app/_style.py::style_rule kind="unit"
def test_style_colors_verbatim_off():
    for fn, text in (
        (style_ok, "PROVED"),
        (style_fail, "GAP"),
        (style_warn, "WAIVED"),
        (style_header, "frob stats"),
        (style_rule, "THREAT002"),
    ):
        assert fn(text, False) == text
        assert _ESC in fn(text, True)


# ---------------------------------------------------------------------------
# ticket_runner: list/show/doable byte-identical off, colored on
# ---------------------------------------------------------------------------


def _seed_ticket(root: Path) -> Ticket:
    ticket = Ticket(
        id="T-0001",
        title="Sample ticket",
        state=TicketState.QUEUED,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        blocked_by=(),
        parent=None,
        scope=(),
        evidence=(),
        attachments=(),
        body="## Description\nsomething\n",
    )
    written = write_ticket(root, ticket)
    assert written.is_ok
    return ticket


def _info_text(caplog) -> str:  # noqa: ANN001
    """Concatenate every captured INFO-level `frob.app.ticket_runner`
    record's rendered message -- `caplog` reads logging records directly,
    sidestepping any stream-identity mismatch between the module-level
    `StreamHandler` (bound once, at `frob.logging.logger._init` time, to
    whatever `sys.stdout` object existed then) and a later fd/stdout
    capture fixture."""
    return "\n".join(
        r.getMessage() for r in caplog.records if r.name == "frob.app.ticket_runner"
    )


def test_ticket_list_plain_stdout_has_no_ansi(tmp_path, monkeypatch, caplog):
    # frob:tests \
    # tests/unit/test_app_style.py::test_ticket_list_plain_stdout_has_no_ansi \
    # kind="unit"
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    _seed_ticket(tmp_path)
    cfg = AppConfig(ticket_command="list", ticket_path=tmp_path)
    with caplog.at_level(logging.INFO, logger="frob.app.ticket_runner"):
        ticket_runner.run(cfg)
    out = _info_text(caplog)
    assert _ESC not in out
    assert "T-0001" in out
    assert "queued" in out


# frob:waive DUP001 reason="parallel test methods within test_app_style.py (2 sites) \
# sharing an arrange-act scaffold typical of exhaustive per-case coverage; extracting \
# would obscure per-case intent"
def test_ticket_list_force_color_has_ansi(tmp_path, monkeypatch, caplog):
    # frob:tests tests/unit/test_app_style.py::test_ticket_list_force_color_has_ansi \
    # kind="unit"
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    _seed_ticket(tmp_path)
    cfg = AppConfig(ticket_command="list", ticket_path=tmp_path)
    with caplog.at_level(logging.INFO, logger="frob.app.ticket_runner"):
        ticket_runner.run(cfg)
    out = _info_text(caplog)
    assert _ESC in out
    assert "T-0001" in out


def test_ticket_list_no_color_env_disables_ansi(tmp_path, monkeypatch, caplog):
    # frob:tests \
    # tests/unit/test_app_style.py::test_ticket_list_no_color_env_disables_ansi \
    # kind="unit"
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("FORCE_COLOR", "1")  # NO_COLOR wins regardless
    _seed_ticket(tmp_path)
    cfg = AppConfig(ticket_command="list", ticket_path=tmp_path)
    with caplog.at_level(logging.INFO, logger="frob.app.ticket_runner"):
        ticket_runner.run(cfg)
    out = _info_text(caplog)
    assert _ESC not in out


def test_ticket_list_json_never_has_ansi_even_with_force_color(
    tmp_path, monkeypatch, caplog
):
    # frob:tests \
    # tests/unit/test_app_style.py::test_ticket_list_json_never_has_ansi_even_with_forc\
    # e_color kind="unit"
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    _seed_ticket(tmp_path)
    cfg = AppConfig(ticket_command="list", ticket_path=tmp_path, ticket_json=True)
    with caplog.at_level(logging.INFO, logger="frob.app.ticket_runner"):
        ticket_runner.run(cfg)
    out = _info_text(caplog)
    assert _ESC not in out
    assert '"id": "T-0001"' in out


def test_ticket_show_plain_vs_force_color_same_content(tmp_path, monkeypatch, caplog):
    # frob:tests \
    # tests/unit/test_app_style.py::test_ticket_show_plain_vs_force_color_same_content \
    # kind="unit"
    _seed_ticket(tmp_path)
    cfg = AppConfig(ticket_command="show", ticket_path=tmp_path, ticket_id="T-0001")

    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    with caplog.at_level(logging.INFO, logger="frob.app.ticket_runner"):
        ticket_runner.run(cfg)
    plain_out = _info_text(caplog)
    assert _ESC not in plain_out
    caplog.clear()

    monkeypatch.setenv("FORCE_COLOR", "1")
    with caplog.at_level(logging.INFO, logger="frob.app.ticket_runner"):
        ticket_runner.run(cfg)
    colored_out = _info_text(caplog)
    assert _ESC in colored_out

    # Stripping ANSI recovers the same visible content either way.
    import re

    stripped = re.sub(r"\x1b\[[0-9;]*m", "", colored_out)
    assert stripped == plain_out


def test_ticket_doable_plain_stdout_has_no_ansi(tmp_path, monkeypatch, caplog):
    # frob:tests \
    # tests/unit/test_app_style.py::test_ticket_doable_plain_stdout_has_no_ansi \
    # kind="unit"
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    _seed_ticket(tmp_path)
    cfg = AppConfig(ticket_command="doable", ticket_path=tmp_path)
    with caplog.at_level(logging.INFO, logger="frob.app.ticket_runner"):
        ticket_runner.run(cfg)
    out = _info_text(caplog)
    assert _ESC not in out
    assert "T-0001" in out


# frob:waive DUP001 reason="parallel test methods within test_app_style.py (2 sites) \
# sharing an arrange-act scaffold typical of exhaustive per-case coverage; extracting \
# would obscure per-case intent"
def test_ticket_doable_force_color_has_ansi(tmp_path, monkeypatch, caplog):
    # frob:tests tests/unit/test_app_style.py::test_ticket_doable_force_color_has_ansi \
    # kind="unit"
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    _seed_ticket(tmp_path)
    cfg = AppConfig(ticket_command="doable", ticket_path=tmp_path)
    with caplog.at_level(logging.INFO, logger="frob.app.ticket_runner"):
        ticket_runner.run(cfg)
    out = _info_text(caplog)
    assert _ESC in out
    assert "T-0001" in out


# ---------------------------------------------------------------------------
# stats_runner: plain text stays byte-identical, colored output gains ANSI
# ---------------------------------------------------------------------------


def _init_frob_repo(root: Path) -> None:
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"], cwd=root, check=True
    )
    subprocess.run(["git", "config", "user.name", "T"], cwd=root, check=True)
    (root / "frob.toml").write_text("")
    _seed_ticket(root)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=root, check=True)


def test_stats_plain_stdout_has_no_ansi(tmp_path, monkeypatch, capfd):
    # frob:tests tests/unit/test_app_style.py::test_stats_plain_stdout_has_no_ansi \
    # kind="unit"
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    _init_frob_repo(tmp_path)
    cfg = AppConfig(stats_path=tmp_path)
    stats_runner.run(cfg)
    out = capfd.readouterr().out
    assert _ESC not in out
    assert "frob stats" in out


def test_stats_force_color_has_ansi(tmp_path, monkeypatch, capfd):
    # frob:tests tests/unit/test_app_style.py::test_stats_force_color_has_ansi \
    # kind="unit"
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    _init_frob_repo(tmp_path)
    cfg = AppConfig(stats_path=tmp_path)
    stats_runner.run(cfg)
    out = capfd.readouterr().out
    assert _ESC in out
    assert "frob stats" in out


def test_stats_json_never_has_ansi(tmp_path, monkeypatch, capfd):
    # frob:tests tests/unit/test_app_style.py::test_stats_json_never_has_ansi \
    # kind="unit"
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    _init_frob_repo(tmp_path)
    cfg = AppConfig(stats_path=tmp_path, stats_json=True)
    stats_runner.run(cfg)
    out = capfd.readouterr().out
    assert _ESC not in out


# ---------------------------------------------------------------------------
# vet_runner._print_table: plain text stays byte-identical, colored gains ANSI
# ---------------------------------------------------------------------------


def _vet_report_with_violation():  # noqa: ANN201
    from frob.gates._models import Severity, Violation
    from frob.vet._models import PackageVerdict, VetReport

    verdict = PackageVerdict(name="left-pad", version="1.0.0", ecosystem="npm")
    violation = Violation(
        rule="VET001",
        severity=Severity.ERROR,
        file="package-lock.json",
        line=1,
        message="left-pad: quarantined",
    )
    return VetReport(verdicts=(verdict,), violations=(violation,))


def test_vet_print_table_plain_has_no_ansi(monkeypatch, capsys):
    # frob:tests tests/unit/test_app_style.py::test_vet_print_table_plain_has_no_ansi \
    # kind="unit"
    from frob.app.vet_runner import _print_table

    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    _print_table(_vet_report_with_violation())
    out = capsys.readouterr().out
    assert _ESC not in out
    assert "left-pad" in out
    assert "FAIL" in out
    assert "VET001" in out


def test_vet_print_table_force_color_has_ansi_same_content(monkeypatch, capsys):
    # frob:tests \
    # tests/unit/test_app_style.py::test_vet_print_table_force_color_has_ansi_same_cont\
    # ent kind="unit"
    from frob.app.vet_runner import _print_table

    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    _print_table(_vet_report_with_violation())
    plain_out = capsys.readouterr().out

    monkeypatch.setenv("FORCE_COLOR", "1")
    _print_table(_vet_report_with_violation())
    colored_out = capsys.readouterr().out
    assert _ESC in colored_out

    import re

    stripped = re.sub(r"\x1b\[[0-9;]*m", "", colored_out)
    assert stripped == plain_out
