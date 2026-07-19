"""System (CLI end-to-end) coverage for `frob sys plan` (T-0084): compile a
small design model's obligation frontier into a ticket tree, dry-run by
default, `--apply` writes, and a second run is a no-op (idempotency)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from tests.system.conftest import run

_MODEL = """\
module m
node evil : foreign
node api : trusted abstract
flow f1 : evil -> api
assert c1 noflow evil -> api
"""


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _init_repo(tmp_path: Path) -> Path:
    """A minimal frob-enabled repo: git init, empty ledger, one design file
    with an unrefined abstract node and a REFUTED noflow claim."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", cwd=repo)
    _git("config", "user.email", "test@example.com", cwd=repo)
    _git("config", "user.name", "Test", cwd=repo)
    (repo / "tickets.md").write_text("# Tickets\n")
    (repo / "design").mkdir()
    (repo / "design" / "m.strata").write_text(_MODEL)
    _git("add", "-A", cwd=repo)
    _git("commit", "-q", "-m", "init", cwd=repo)
    return repo


class TestSysPlanCli:
    def test_dry_run_prints_tree_without_writing(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path)
        r = run("sys", "plan", cwd=repo)
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        assert "sys-plan:api:unrefined" in out
        assert "sys-plan:c1:refuted" in out
        assert (repo / "tickets.md").read_text() == "# Tickets\n"

    def test_dry_run_names_apply_flag_in_label(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/sys_runner.py::_print_dry_run kind="system"
        # T-0231: the output must explicitly say DRY RUN and name --apply,
        # not just report a ticket count with no indication of dry-run-ness.
        repo = _init_repo(tmp_path)
        r = run("sys", "plan", cwd=repo)
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        assert "DRY RUN" in out
        assert "--apply" in out

    def test_apply_writes_ticket_tree(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path)
        r = run("sys", "plan", "--apply", cwd=repo)
        out = r.stdout + r.stderr
        assert r.returncode == 0, out

        ledger = (repo / "tickets.md").read_text()
        assert "sys-plan:api:unrefined" in ledger
        assert "sys-plan:api:refine" in ledger
        assert "sys-plan:c1:refuted" in ledger

    def test_second_apply_is_a_noop(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path)
        first = run("sys", "plan", "--apply", cwd=repo)
        assert first.returncode == 0, first.stdout + first.stderr
        ledger_after_first = (repo / "tickets.md").read_text()

        second = run("sys", "plan", "--apply", cwd=repo)
        out = second.stdout + second.stderr
        assert second.returncode == 0, out
        assert (repo / "tickets.md").read_text() == ledger_after_first
        assert "nothing to plan" in out

    def test_dropped_ticket_is_not_recreated(self, tmp_path: Path) -> None:
        """A discharged obligation's ticket is dropped, not left open forever.
        Re-planning must never resurrect it -- a marker match suppresses
        re-creation regardless of the matched ticket's state (module
        docstring in `frob.strata._plan`), so dropping is the durable
        "this is handled" signal, not a re-open trigger."""
        from frob.tickets import TicketState, load_all, transition

        repo = _init_repo(tmp_path)
        first = run("sys", "plan", "--apply", cwd=repo)
        assert first.returncode == 0, first.stdout + first.stderr

        loaded = load_all(repo)
        assert loaded.is_ok, loaded.danger_err
        refuted_id = next(
            t.id for t in loaded.danger_ok.values() if "sys-plan:c1:refuted" in t.body
        )
        dropped = transition(repo, refuted_id, TicketState.DROPPED)
        assert dropped.is_ok, dropped.danger_err
        ledger_after_drop = (repo / "tickets.md").read_text()
        assert "state: dropped" in ledger_after_drop

        second = run("sys", "plan", "--apply", cwd=repo)
        out = second.stdout + second.stderr
        assert second.returncode == 0, out
        assert (repo / "tickets.md").read_text() == ledger_after_drop

        reloaded = load_all(repo)
        assert reloaded.is_ok, reloaded.danger_err
        refuted_tickets = [
            t for t in reloaded.danger_ok.values() if "sys-plan:c1:refuted" in t.body
        ]
        assert len(refuted_tickets) == 1
        assert refuted_tickets[0].state == TicketState.DROPPED
