"""System (CLI end-to-end) coverage for `frob sys plan` (T-0084): compile a
small design model's obligation frontier into a ticket tree, dry-run by
default, `--apply` writes, and a second run is a no-op (idempotency).

T-0724 note: `TestSysAuditContentionCli` below drives `frob sys audit`,
not `sys plan` -- it lives in this file because T-0724's declared ticket
`scope` names this exact path for its required system test (acceptance:
"a duplicate-port fixture surfaces SYS200 through the real CLI"), and the
agent playbook's scope discipline takes that literally over moving it to
the thematically-closer `test_cli_sys_audit.py`."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.system.conftest import init_repo, run

_MODEL = """\
module m
node evil : foreign
node api : trusted abstract
flow f1 : evil -> api
assert c1 noflow evil -> api
"""


def _init_repo(tmp_path: Path) -> Path:
    """A minimal frob-enabled repo: git init, empty ledger, one design file
    with an unrefined abstract node and a REFUTED noflow claim (T-0364:
    arrange step extracted to conftest.init_repo, shared with
    test_cli_sys_doc.py)."""
    return init_repo(tmp_path, _MODEL)


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
        # frob:tests src/frob/app/sys_runner.py::_print_dry_run kind="integration"
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

    def test_threat_pre_discharge_count_never_reads_as_contradicting_output(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/strata/_threat.py::evaluate_threats kind="integration"
        # T-0217: `_frontier_threats` only turns THREAT003 violations into
        # obligation tickets; `evaluate_threats`'s pre-discharge count spans
        # catalog/capability/discharge completeness too, so it can be
        # nonzero while zero threat obligation tickets are planned. The old
        # "threat: evaluated ... -> N violation(s)" wording made that look
        # like a contradiction next to the rest of this output. The exact
        # old phrase must never appear.
        repo = _init_repo(tmp_path)
        r = run("sys", "plan", cwd=repo)
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        assert "-> 0 violation(s)" not in out
        assert "threat: evaluated view=" not in out

    # frob:ticket T-0908
    def test_dropped_ticket_is_not_recreated(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A discharged obligation's ticket is dropped, not left open forever.
        Re-planning must never resurrect it -- a marker match suppresses
        re-creation regardless of the matched ticket's state (module
        docstring in `frob.strata._plan`), so dropping is the durable
        "this is handled" signal, not a re-open trigger.

        T-0908: `load_all`/`transition` below are called IN-PROCESS (no
        subprocess boundary), so a dispatching agent's `FROB_WORKTREE`/
        `FROB_AGENT` lease env is stripped here first; otherwise it leaks
        in and trips `enforce_worktree_lease` against this test's own
        `tmp_path` repo, unrelated to drop/re-plan correctness."""
        monkeypatch.delenv("FROB_WORKTREE", raising=False)
        monkeypatch.delenv("FROB_AGENT", raising=False)
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


# frob:ticket T-0724
_DUPLICATE_PORT_MODEL = """\
module m
node api_a : trusted {
    clearance Internal;
    listens 8080;
}
node api_b : trusted {
    clearance Internal;
    listens 8080;
}
"""


class TestSysAuditContentionCli:
    """T-0724: `check_resource_contention` (T-0699) wired into `frob sys
    audit` for real -- a duplicate-port design fixture must surface SYS200
    through the actual CLI dispatch, not just the unit-level
    `check_resource_contention` call `tests/unit/strata/test_contention.py`
    already covers."""

    # frob:tests \
    # tests/system/test_cli_sys_plan.py::TestSysAuditContentionCli.test_duplicate_port_\
    # fires_sys200_through_cli
    def test_duplicate_port_fires_sys200_through_cli(self, tmp_path: Path) -> None:
        repo = init_repo(tmp_path, _DUPLICATE_PORT_MODEL)
        r = run("sys", "audit", cwd=repo)
        out = r.stdout + r.stderr
        assert r.returncode != 0, out
        assert "SYS200" in out
        assert "8080" in out
        assert "api_a" in out
        assert "api_b" in out
