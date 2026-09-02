import json
import subprocess
from datetime import date
from pathlib import Path

from frob.gates import (
    GateConfig,
    PreworkSweep,
    Severity,
    active_ticket,
    delta_violations,
    is_baseline_stale,
    load_baseline,
    prework_gate,
    record_prework,
    run_gates,
    scope_gate,
    stamp_baseline,
    violation_fingerprint,
)
from frob.gitio import Diff, Hunk, working_diff
from frob.tickets import TicketKind, TicketQueue, TicketState
from tests.conftest import (
    _WIDGET_PY,
    _git_init,
    _rules,
    _snapshot,
    _ticket,
    _violation,
    _write,
    _write_ticket,
)


# frob:ticket T-0906
# frob:ticket T-0584
class TestScopePrework:
    def test_scope001_out_of_scope_file(self, tmp_path: Path) -> None:
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=("src/allowed/**",))
        diff = Diff(base="x", hunks=(Hunk(file="src/other/f.py", span=(1, 1)),))
        violations = scope_gate(diff, ticket, snap)
        assert any(v.rule == "SCOPE001" for v in violations)

    def test_scope001_passes_in_scope(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=("src/allowed/**",))
        diff = Diff(base="x", hunks=(Hunk(file="src/allowed/f.py", span=(1, 1)),))
        violations = scope_gate(diff, ticket, snap)
        assert violations == ()

    # frob:ticket T-0906
    def test_scope001_fires_when_no_scope_declared(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        # T-0906/H1 (docs/audits/gates-vacuous.md): an empty ticket.scope
        # used to short-circuit scope_gate to a silent, unconditional pass
        # -- the least-declared-intent ticket got the LEAST enforcement.
        # It must now get the SAME (loud) SCOPE001 enforcement as any other
        # out-of-scope file.
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=())
        diff = Diff(base="x", hunks=(Hunk(file="src/anything.py", span=(1, 1)),))
        violations = scope_gate(diff, ticket, snap)
        assert any(v.rule == "SCOPE001" for v in violations)

    # frob:ticket T-3296
    def test_scope001_frob_managed_side_effect_path_never_fires(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        """MUST-FIRE (T-3296): --stamp-coverage's rewrite of
        frob-coverage.lock.json must never trip SCOPE001, for a ticket
        with NO declared scope at all -- the exemption does not depend on
        the ticket having claimed the path (that claim is exactly what
        the F-029/F-039/F-042 deadlock made impossible for every ticket
        but one)."""
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=())
        diff = Diff(
            base="x", hunks=(Hunk(file="frob-coverage.lock.json", span=(1, 1)),)
        )
        violations = scope_gate(diff, ticket, snap)
        assert not any(v.rule == "SCOPE001" for v in violations)

    # frob:ticket T-3296
    def test_scope001_still_fires_for_non_exempt_unscoped_file_alongside_exempt_one(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        """MUST-STAY-QUIET (T-3296): the exemption is per-path, not
        per-diff -- a genuinely out-of-scope file in the SAME diff as the
        exempt path still fires SCOPE001."""
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=("src/allowed/**",))
        diff = Diff(
            base="x",
            hunks=(
                Hunk(file="frob-coverage.lock.json", span=(1, 1)),
                Hunk(file="src/other/f.py", span=(1, 1)),
            ),
        )
        violations = scope_gate(diff, ticket, snap)
        scope001 = [v for v in violations if v.rule == "SCOPE001"]
        assert len(scope001) == 1
        assert scope001[0].file == "src/other/f.py"

    # frob:ticket T-0906
    def test_scope001_empty_scope_ledger_still_implicitly_in_scope(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        # T-0906: the ledger stays implicitly in scope even for a ticket
        # with no declared scope at all -- recording a Done report must
        # never itself trip SCOPE001.
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=())
        diff = Diff(base="x", hunks=(Hunk(file="tickets.md", span=(1, 1)),))
        assert scope_gate(diff, ticket, snap) == ()

    # frob:ticket T-0899
    def test_scope001_empty_scope_never_returns_bare_empty_tuple_for_a_real_diff(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        # T-0899, the regression-gate pair for T-0906/H1: an in-progress
        # ticket carrying scope=() must never again silently coexist with
        # scope_gate returning the bare `()` no-violation sentinel for a
        # non-empty, out-of-scope diff -- multiple touched files must each
        # produce their own SCOPE001, not a single silently-cleared pass.
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=())
        diff = Diff(
            base="x",
            hunks=(
                Hunk(file="src/one.py", span=(1, 1)),
                Hunk(file="src/two.py", span=(1, 1)),
            ),
        )
        violations = scope_gate(diff, ticket, snap)
        assert violations != ()
        assert {v.file for v in violations} == {"src/one.py", "src/two.py"}
        assert all(v.rule == "SCOPE001" for v in violations)

    def test_scope001_comma_joined_entry_splits_and_matches(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        # T-0241: a single 'a/,b/,c/' scope entry used to become one fnmatch
        # pattern that matched nothing; the Ticket model now splits it.
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=("src/a/**,src/b/**",))
        diff = Diff(base="x", hunks=(Hunk(file="src/b/f.py", span=(1, 1)),))
        assert scope_gate(diff, ticket, snap) == ()

    def test_scope001_dir_prefix_globs_recursively(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        # T-0241: a bare 'design/' scope entry now matches anything under it.
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=("design/",))
        diff = Diff(base="x", hunks=(Hunk(file="design/sub/f.py", span=(1, 1)),))
        assert scope_gate(diff, ticket, snap) == ()

    def test_scope001_ledger_implicitly_in_scope(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        # T-0241: tickets.md is always implicitly in every ticket's scope.
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=("src/a/**",))
        diff = Diff(base="x", hunks=(Hunk(file="tickets.md", span=(1, 1)),))
        assert scope_gate(diff, ticket, snap) == ()

    # frob:ticket T-0446
    def test_scope001_feature_ticket_cli_wiring_files_implicitly_in_scope(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        # T-0446: a FEATURE ticket adding a new subcommand structurally
        # needs to touch the CLI dispatch/config/runner wiring files no
        # matter what scope it declared -- these must never trip SCOPE001.
        from frob.tickets._models import CLI_WIRING_FILES

        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=("src/frob/tickets/**",), kind=TicketKind.FEATURE)
        diff = Diff(
            base="x",
            hunks=tuple(Hunk(file=f, span=(1, 1)) for f in sorted(CLI_WIRING_FILES)),
        )
        assert scope_gate(diff, ticket, snap) == ()

    def test_scope001_non_feature_ticket_cli_wiring_files_still_out_of_scope(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        # T-0446: the exemption is FEATURE-only -- a bug ticket touching
        # the CLI dispatch table unannounced is real scope creep, not the
        # structural-necessity case T-0446 fixes.
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=("src/frob/tickets/**",), kind=TicketKind.BUG)
        diff = Diff(base="x", hunks=(Hunk(file="src/frob/__main__.py", span=(1, 1)),))
        assert any(v.rule == "SCOPE001" for v in scope_gate(diff, ticket, snap))

    # frob:ticket T-1819
    def test_scope001_own_sharded_ledger_shard_implicitly_in_scope(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        # T-1819: LEDGER_PATH ('tickets.md') predates the sharded
        # per-ticket store -- a ticket's own tickets/<id>/** bookkeeping
        # files (routine start/sweep auto-commits) must not trip a false
        # SCOPE001, mirroring the tickets.md-always-in-scope rule.
        snap = _snapshot(tmp_path)
        ticket = _ticket(ticket_id="T-1819", scope=("src/a/**",))
        diff = Diff(
            base="x",
            hunks=(
                Hunk(file="tickets/T-1819/ticket.md", span=(1, 1)),
                Hunk(file="tickets/T-1819/done-report.md", span=(1, 1)),
            ),
        )
        assert scope_gate(diff, ticket, snap) == ()

    # frob:ticket T-1819
    def test_scope001_another_tickets_shard_still_out_of_scope(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        # T-1819: the implicit exemption is per-ticket -- a DIFFERENT
        # ticket's own shard is not implicitly covered.
        snap = _snapshot(tmp_path)
        ticket = _ticket(ticket_id="T-1819", scope=("src/a/**",))
        diff = Diff(
            base="x", hunks=(Hunk(file="tickets/T-0001/ticket.md", span=(1, 1)),)
        )
        assert any(v.rule == "SCOPE001" for v in scope_gate(diff, ticket, snap))

    def test_scope001_exempts_file_committed_by_earlier_ticket(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        # Reproduces T-0108: ticket A commits within its own scope, then ticket
        # B's scope check must not flag A's already-committed file.
        _git_init(tmp_path)
        _write_ticket(
            tmp_path,
            _ticket(ticket_id="T-0001", scope=("src/a/**",)),
        )
        _write_ticket(
            tmp_path,
            _ticket(ticket_id="T-0002", scope=("src/b/**",)),
        )
        subprocess.run(
            ["git", "checkout", "-q", "-b", "work"], cwd=tmp_path, check=True
        )
        _write(tmp_path, "src/a/mod.py", "def f():\n    return 1\n")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "feat(a): add mod (T-0001)"],
            cwd=tmp_path,
            check=True,
        )
        queue = TicketQueue(
            tickets={
                "T-0001": _ticket(ticket_id="T-0001", scope=("src/a/**",)),
                "T-0002": _ticket(ticket_id="T-0002", scope=("src/b/**",)),
            }
        )
        diff = working_diff(tmp_path, "main").danger_ok
        snap = _snapshot(tmp_path)
        ticket_b = _ticket(ticket_id="T-0002", scope=("src/b/**",))

        # Without root/queue (old behavior): false positive SCOPE001 on A's file.
        violations_no_context = scope_gate(diff, ticket_b, snap)
        assert any(v.file == "src/a/mod.py" for v in violations_no_context)

        # With root/queue: T-0001's committed file is exempt from T-0002's check.
        violations = scope_gate(diff, ticket_b, snap, root=tmp_path, queue=queue)
        assert not any(v.file == "src/a/mod.py" for v in violations)

    # frob:ticket T-3298
    def test_scope001_exempts_new_tickets_own_bookkeeping_shard_filed_from_another(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        """MUST-FIRE (T-3298): ticket A (scope excludes tickets/**) runs
        `frob ticket new` to file ticket B as an out-of-scope discovery --
        the resulting commit (subject references B, per `frob ticket
        new`'s own auto-commit convention) writes tickets/B/ticket.md.
        `frob check --ticket A` must be 0 SCOPE001 findings for
        tickets/B/ticket.md, even though B has an EMPTY declared scope
        (the normal state for a freshly filed ticket) -- the exemption
        must reuse B's own implicit tickets/B/** bookkeeping-shard scope
        (T-1819), not B's declared scope alone."""
        _git_init(tmp_path)
        _write_ticket(tmp_path, _ticket(ticket_id="T-0001", scope=("src/a/**",)))
        subprocess.run(
            ["git", "checkout", "-q", "-b", "work"], cwd=tmp_path, check=True
        )
        _write(tmp_path, "tickets/T-0002/ticket.md", "id: T-0002")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "chore(tickets): file T-0002"],
            cwd=tmp_path,
            check=True,
        )
        queue = TicketQueue(
            tickets={
                "T-0001": _ticket(ticket_id="T-0001", scope=("src/a/**",)),
                # B's own real state: freshly filed, no declared scope yet.
                "T-0002": _ticket(ticket_id="T-0002", scope=()),
            }
        )
        diff = working_diff(tmp_path, "main").danger_ok
        snap = _snapshot(tmp_path)
        ticket_a = _ticket(ticket_id="T-0001", scope=("src/a/**",))

        violations = scope_gate(diff, ticket_a, snap, root=tmp_path, queue=queue)
        assert not any(v.file == "tickets/T-0002/ticket.md" for v in violations)

    # frob:ticket T-3298
    def test_scope001_still_flags_hand_edit_of_unreferenced_tickets_shard(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        """MUST-STAY-QUIET (T-3298): ticket A hand-edits tickets/C/
        ticket.md directly (a ticket it did not create, in a commit whose
        subject names A itself, never C) -- SCOPE001 must still fire; the
        T-3298 fix only reuses an exemption already earned by a commit
        that actually references the OTHER ticket, it does not grant a
        blanket allow on the tickets/ directory."""
        _git_init(tmp_path)
        _write_ticket(tmp_path, _ticket(ticket_id="T-0001", scope=("src/a/**",)))
        _write_ticket(tmp_path, _ticket(ticket_id="T-0003", scope=()))
        subprocess.run(
            ["git", "checkout", "-q", "-b", "work"], cwd=tmp_path, check=True
        )
        _write(tmp_path, "tickets/T-0003/ticket.md", "id: T-0003 hand-edited")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "chore(tickets): note (T-0001)"],
            cwd=tmp_path,
            check=True,
        )
        queue = TicketQueue(
            tickets={
                "T-0001": _ticket(ticket_id="T-0001", scope=("src/a/**",)),
                "T-0003": _ticket(ticket_id="T-0003", scope=()),
            }
        )
        diff = working_diff(tmp_path, "main").danger_ok
        snap = _snapshot(tmp_path)
        ticket_a = _ticket(ticket_id="T-0001", scope=("src/a/**",))

        violations = scope_gate(diff, ticket_a, snap, root=tmp_path, queue=queue)
        assert any(v.file == "tickets/T-0003/ticket.md" for v in violations)

    def test_scope001_still_flags_uncommitted_out_of_scope_edit(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        # The exemption must not swallow a ticket's own dirty, out-of-scope edit.
        _git_init(tmp_path)
        _write_ticket(tmp_path, _ticket(ticket_id="T-0002", scope=("src/b/**",)))
        _write(tmp_path, "src/a/mod.py", "def f():\n    return 1\n")
        queue = TicketQueue(
            tickets={"T-0002": _ticket(ticket_id="T-0002", scope=("src/b/**",))}
        )
        diff = working_diff(tmp_path, "main").danger_ok
        snap = _snapshot(tmp_path)
        ticket_b = _ticket(ticket_id="T-0002", scope=("src/b/**",))

        violations = scope_gate(diff, ticket_b, snap, root=tmp_path, queue=queue)
        assert any(v.file == "src/a/mod.py" for v in violations)

    def test_scope001_does_not_exempt_when_referenced_ticket_lacks_scope(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        # A commit referencing a ticket that doesn't declare the file in its own
        # scope must not grant an exemption.
        _git_init(tmp_path)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "work"], cwd=tmp_path, check=True
        )
        _write(tmp_path, "src/a/mod.py", "def f():\n    return 1\n")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "feat(a): add mod (T-0001)"],
            cwd=tmp_path,
            check=True,
        )
        queue = TicketQueue(
            tickets={
                "T-0001": _ticket(ticket_id="T-0001", scope=("src/other/**",)),
                "T-0002": _ticket(ticket_id="T-0002", scope=("src/b/**",)),
            }
        )
        diff = working_diff(tmp_path, "main").danger_ok
        snap = _snapshot(tmp_path)
        ticket_b = _ticket(ticket_id="T-0002", scope=("src/b/**",))

        violations = scope_gate(diff, ticket_b, snap, root=tmp_path, queue=queue)
        assert any(v.file == "src/a/mod.py" for v in violations)

    def test_scope001_merge_commit_with_no_ticket_ref_falls_back_to_parent(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::scope_gate
        # T-0527: a plain `git merge` conflict-resolution commit carries NO
        # ticket reference of its own in its subject (the default merge
        # message), yet `git blame` attributes the reconciled hunk to that
        # merge commit rather than either parent. The exemption must not
        # treat this as an unattributed touch -- it should fall back to the
        # merge commit's PARENTS' subjects to recover the ticket reference
        # that actually attributes the reconciled content.
        _git_init(tmp_path)
        _write_ticket(
            tmp_path,
            _ticket(ticket_id="T-0001", scope=("src/a/**",)),
        )
        _write_ticket(
            tmp_path,
            _ticket(ticket_id="T-0002", scope=("src/b/**",)),
        )
        subprocess.run(
            ["git", "checkout", "-q", "-b", "work"], cwd=tmp_path, check=True
        )
        _write(tmp_path, "src/a/mod.py", "def f():\n    return 1\n")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "feat(a): add mod (T-0001)"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(["git", "checkout", "-q", "main"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "conflict-source"],
            cwd=tmp_path,
            check=True,
        )
        _write(tmp_path, "src/a/mod.py", "def f():\n    return 2\n")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "feat(a): conflicting change (T-0001)"],
            cwd=tmp_path,
            check=True,
        )
        subprocess.run(["git", "checkout", "-q", "work"], cwd=tmp_path, check=True)
        merge = subprocess.run(
            ["git", "merge", "-q", "--no-ff", "conflict-source"],
            cwd=tmp_path,
            check=False,
        )
        assert merge.returncode != 0  # a real conflict, not a trivial merge
        _write(tmp_path, "src/a/mod.py", "def f():\n    return 3\n")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "Merge branch 'conflict-source'"],
            cwd=tmp_path,
            check=True,
        )
        queue = TicketQueue(
            tickets={
                "T-0001": _ticket(ticket_id="T-0001", scope=("src/a/**",)),
                "T-0002": _ticket(ticket_id="T-0002", scope=("src/b/**",)),
            }
        )
        diff = working_diff(tmp_path, "main").danger_ok
        snap = _snapshot(tmp_path)
        ticket_b = _ticket(ticket_id="T-0002", scope=("src/b/**",))

        violations = scope_gate(diff, ticket_b, snap, root=tmp_path, queue=queue)
        assert not any(v.file == "src/a/mod.py" for v in violations)

    def test_pre001_missing_sweep(self, tmp_path: Path) -> None:
        from typani.option import Nothing

        snap = _snapshot(tmp_path)
        ticket = _ticket(state=TicketState.IN_PROGRESS)
        violations = prework_gate(ticket, snap, Nothing())
        assert any(v.rule == "PRE001" for v in violations)
        # T-3301 (F-031): the remediation must name a verb that does not
        # itself refuse -- `frob ticket start <id>` REFUSES on a ticket
        # that is already in-progress (which prework_gate only ever
        # fires against, see the IN_PROGRESS state check it opens with),
        # so the message must point at `sweep` instead.
        assert "frob ticket sweep" in violations[0].message
        assert "frob ticket start" not in violations[0].message

    def test_pre001_passes_with_current_sweep(self, tmp_path: Path) -> None:
        from typani.option import Some

        _write(tmp_path, "src/a.py", _WIDGET_PY)
        snap = _snapshot(tmp_path)
        ticket = _ticket(state=TicketState.IN_PROGRESS, scope=("src/**",))

        from frob.gates import _scope_digest  # noqa: PLC0415

        digest = _scope_digest(ticket, snap)
        sweep = PreworkSweep(
            date=date(2026, 1, 1), dup_findings=0, xref_hits=(), digest=digest
        )
        violations = prework_gate(ticket, snap, Some(sweep))
        assert violations == ()

    def test_pre001_stale_sweep(self, tmp_path: Path) -> None:
        from typani.option import Some

        _write(tmp_path, "src/a.py", _WIDGET_PY)
        snap = _snapshot(tmp_path)
        ticket = _ticket(state=TicketState.IN_PROGRESS, scope=("src/**",))
        sweep = PreworkSweep(
            date=date(2026, 1, 1), dup_findings=0, xref_hits=(), digest="stale"
        )
        violations = prework_gate(ticket, snap, Some(sweep))
        assert any(v.rule == "PRE001" for v in violations)
        # T-3301 (F-031): same "start refuses on an in-progress ticket"
        # fix as test_pre001_missing_sweep above.
        assert "frob ticket sweep" in violations[0].message
        assert "frob ticket start" not in violations[0].message

    # frob:ticket T-0584
    def test_pre001_passes_with_partial_sweep_matching_digest(
        self, tmp_path: Path
    ) -> None:
        """A partial sweep (budget exceeded mid-scan, T-0584) whose digest
        still matches the ticket's current scope is provisionally clean --
        PRE001 must not re-demand the very sweep that timed out."""
        from typani.option import Some

        _write(tmp_path, "src/a.py", _WIDGET_PY)
        snap = _snapshot(tmp_path)
        ticket = _ticket(state=TicketState.IN_PROGRESS, scope=("src/**",))

        from frob.gates import _scope_digest  # noqa: PLC0415

        digest = _scope_digest(ticket, snap)
        sweep = PreworkSweep(
            date=date(2026, 1, 1),
            dup_findings=0,
            xref_hits=(),
            digest=digest,
            partial=True,
            pending_patterns=("src/**",),
        )
        violations = prework_gate(ticket, snap, Some(sweep))
        assert violations == ()

    def test_prework_skips_when_not_in_progress(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::prework_gate
        from typani.option import Nothing

        snap = _snapshot(tmp_path)
        ticket = _ticket(state=TicketState.QUEUED)
        assert prework_gate(ticket, snap, Nothing()) == ()

    def test_record_and_load_prework_roundtrip(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_prework.py::record_prework
        from frob.gates._prework import load_prework

        sweep = PreworkSweep(
            date=date(2026, 1, 1), dup_findings=2, xref_hits=("a", "b"), digest="abc"
        )
        result = record_prework(tmp_path, "T-0001", sweep)
        assert result.is_ok
        loaded = load_prework(tmp_path, "T-0001")
        assert loaded == sweep

    def test_record_prework_returns_err_on_oserror(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_prework.py::record_prework
        """`record_prework` must return `Err(GateError.WriteFailed)`, not
        raise, when the write fails -- induced here by pre-creating the
        target path AS A DIRECTORY, so `path.write_text(...)` raises
        `IsADirectoryError` (an `OSError`)."""
        from frob.gates._models import GateError
        from frob.gates._prework import _prework_path

        sweep = PreworkSweep(
            date=date(2026, 1, 1), dup_findings=0, xref_hits=(), digest="x"
        )
        path = _prework_path(tmp_path, "T-0002")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.mkdir()  # a directory where record_prework expects to write a file

        result = record_prework(tmp_path, "T-0002", sweep)
        assert result.is_err
        assert result.danger_err == GateError.WriteFailed

    def test_load_prework_returns_none_on_malformed_json(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_prework.py::load_prework
        """`load_prework` must return `None` (never raise) when the
        recorded file exists but is not valid JSON -- the documented
        "unreadable" contract, induced with real malformed content on
        disk rather than a mock."""
        from frob.gates._prework import _prework_path, load_prework

        path = _prework_path(tmp_path, "T-0003")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not valid json", encoding="utf-8")

        assert load_prework(tmp_path, "T-0003") is None

    def test_load_prework_returns_none_on_schema_mismatch(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_prework.py::load_prework
        """Valid JSON that does not satisfy `PreworkSweep`'s schema (a
        pydantic `ValidationError`, itself a `ValueError` subclass) hits
        the same swallow-and-return-None branch as malformed JSON."""
        from frob.gates._prework import _prework_path, load_prework

        path = _prework_path(tmp_path, "T-0004")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"totally": "wrong shape"}), encoding="utf-8")

        assert load_prework(tmp_path, "T-0004") is None

    # frob:ticket T-0584
    def test_prework_sweep_default_partial_is_false_and_treated_as_final(
        self, tmp_path: Path
    ) -> None:
        """`PreworkSweep` constructed WITHOUT `partial=` (T-0584's field
        default) must behave as a COMPLETE sweep, not a partial one: `PRE001`
        must accept it outright with no "resume with `frob ticket sweep`"
        debug path taken, and it must round-trip through record/load with
        `partial` still False and no pending patterns. If the field's
        default ever flipped to `True`, a freshly-recorded "complete" sweep
        would misreport itself as partial forever."""
        from typani.option import Some

        _write(tmp_path, "src/a.py", _WIDGET_PY)
        snap = _snapshot(tmp_path)
        ticket = _ticket(state=TicketState.IN_PROGRESS, scope=("src/**",))

        from frob.gates import _scope_digest  # noqa: PLC0415
        from frob.gates._prework import load_prework  # noqa: PLC0415

        digest = _scope_digest(ticket, snap)
        sweep = PreworkSweep(
            date=date(2026, 1, 1), dup_findings=0, xref_hits=(), digest=digest
        )
        assert sweep.partial is False
        assert sweep.pending_patterns == ()

        result = record_prework(tmp_path, ticket.id, sweep)
        assert result.is_ok
        loaded = load_prework(tmp_path, ticket.id)
        assert loaded is not None
        assert loaded.partial is False

        violations = prework_gate(ticket, snap, Some(sweep))
        assert violations == ()


# frob:ticket T-0998
class TestScope002ClosureGate:
    """`frob.gates._scope002_violations` (SCOPE002, T-0998): scope-
    declaration-time doc-edge + code-edge + private-helper closure
    validation over a ticket's declared scope, WARN-only turn-on."""

    def test_warns_on_unscoped_doc_target(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_scope002_violations
        from frob.gates import _scope002_violations  # noqa: PLC0415

        _write(
            tmp_path,
            "src/a.py",
            "# frob:doc docs/x.md#foo\ndef foo() -> None:\n    pass\n",
        )
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=("src/a.py",))
        violations = _scope002_violations(ticket, snap, tmp_path)
        assert any(v.rule == "SCOPE002" for v in violations)
        found = [v for v in violations if v.rule == "SCOPE002"][0]
        assert found.severity == Severity.WARN
        assert "docs/x.md" in found.message

    def test_warns_on_unscoped_private_helper(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_scope002_violations
        from frob.gates import _scope002_violations  # noqa: PLC0415

        _write(
            tmp_path,
            "src/pkg/a.py",
            "def public_fn() -> None:\n    _helper()\n",
        )
        _write(tmp_path, "src/pkg/b.py", "def _helper() -> None:\n    pass\n")
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=("src/pkg/a.py",))
        violations = _scope002_violations(ticket, snap, tmp_path)
        assert any(
            v.rule == "SCOPE002" and "src/pkg/b.py" in v.message for v in violations
        )

    def test_warns_on_unscoped_test_target(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_scope002_violations
        from frob.gates import _scope002_violations  # noqa: PLC0415

        _write(tmp_path, "src/a.py", "def foo() -> None:\n    pass\n")
        _write(
            tmp_path,
            "tests/test_a.py",
            "# frob:tests src/a.py::foo\ndef test_foo() -> None:\n    pass\n",
        )
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=("src/a.py",))
        violations = _scope002_violations(ticket, snap, tmp_path)
        assert any(
            v.rule == "SCOPE002" and "tests/test_a.py" in v.message for v in violations
        )

    def test_silent_on_closed_scope(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/__init__.py::_scope002_violations
        from frob.gates import _scope002_violations  # noqa: PLC0415

        _write(
            tmp_path,
            "src/a.py",
            "# frob:doc docs/x.md#foo\ndef foo() -> None:\n    pass\n",
        )
        _write(tmp_path, "docs/x.md", "# X\n<!-- frob:describes src/a.py::foo -->\n")
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=("src/a.py", "docs/x.md"))
        violations = _scope002_violations(ticket, snap, tmp_path)
        assert violations == ()

    # frob:ticket T-2608
    def test_groups_many_symbols_pointing_at_the_same_missing_file(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/__init__.py::_scope002_violations
        """T-2608: a scoped file whose public symbols ALL point at the
        SAME out-of-scope doc target must produce ONE SCOPE002 violation
        naming that missing file (with a count and examples), not one
        violation per symbol -- the closure-debt shape T-2608 measured
        (852+ near-duplicate lines from `_gate_cache.py`/`_python.py`,
        every symbol independently recommending the identical `frob
        ticket scope <id> --add docs/modules/gates.md`)."""
        from frob.gates import _scope002_violations  # noqa: PLC0415

        body = "\n".join(
            f"# frob:doc docs/x.md#foo{i}\ndef foo{i}() -> None:\n    pass\n"
            for i in range(5)
        )
        _write(tmp_path, "src/a.py", body)
        snap = _snapshot(tmp_path)
        ticket = _ticket(scope=("src/a.py",))
        violations = _scope002_violations(ticket, snap, tmp_path)
        scope002 = [v for v in violations if v.rule == "SCOPE002"]
        matching = [v for v in scope002 if "docs/x.md" in v.message]
        assert len(matching) == 1, (
            "5 symbols sharing one missing doc target must fold into 1 "
            f"violation, not {len(matching)}: {[v.message for v in matching]}"
        )
        assert "5" in matching[0].message


# frob:ticket T-0584
class TestPreworkSweepBounds:
    """T-0240: the sweep's xref half used to call `xref(symbol, root)` --
    ALWAYS the full repo root, ignoring the per-pattern scan path it had
    already computed -- and derived its search term from a raw glob-syntax
    stem (`Path(pattern).stem`), producing nonsense terms like `"**"`. Both
    made `frob ticket start`/`sweep` unbounded and slow on real scopes.
    These pin the fix: excludes/skip-dirs are honored (reusing
    `frob.excludes`, not a second copy of the rule) and every xref hit is a
    real, graph-known symbol name."""

    def test_sweep_ticket_honors_graph_excludes(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_prework.py::sweep_ticket
        (tmp_path / "frob.toml").write_text('[graph]\nexclude = ["vendor/**"]\n')
        _write(tmp_path, "vendor/big.py", "def vendored_widget():\n    pass\n")
        _write(tmp_path, "src/keep.py", "def kept_widget():\n    pass\n")
        ticket = _ticket(state=TicketState.IN_PROGRESS, scope=("vendor/**", "src/**"))

        from frob.gates._prework import sweep_ticket

        result = sweep_ticket(tmp_path, ticket)
        assert result.is_ok
        sweep = result.danger_ok
        assert "vendored_widget" not in sweep.xref_hits
        assert "kept_widget" in sweep.xref_hits

    def test_sweep_ticket_skips_builtin_skip_dirs(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_prework.py::sweep_ticket
        _write(tmp_path, ".venv/pkg/mod.py", "def hidden_widget():\n    pass\n")
        ticket = _ticket(state=TicketState.IN_PROGRESS, scope=(".venv/pkg/**",))

        from frob.gates._prework import sweep_ticket

        result = sweep_ticket(tmp_path, ticket)
        assert result.is_ok
        assert result.danger_ok.xref_hits == ()

    def test_sweep_ticket_xref_hits_are_real_symbols(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_prework.py::sweep_ticket
        _write(tmp_path, "src/mod.py", "def real_widget():\n    pass\n")
        ticket = _ticket(state=TicketState.IN_PROGRESS, scope=("src/**",))

        from frob.gates._prework import sweep_ticket

        result = sweep_ticket(tmp_path, ticket)
        assert result.is_ok
        sweep = result.danger_ok
        assert sweep.xref_hits == ("real_widget",)
        assert "**" not in sweep.xref_hits

    # frob:ticket T-0584
    def test_sweep_ticket_partial_on_budget_exceeded(self, tmp_path: Path) -> None:
        """A `budget_seconds=0` deadline is exceeded before the first scope
        pattern is scanned -- the sweep must record `partial=True` with
        every pattern still pending, rather than blocking to completion or
        erroring out."""
        # frob:tests src/frob/gates/_prework.py::sweep_ticket
        _write(tmp_path, "src/a/mod.py", "def a_widget():\n    pass\n")
        _write(tmp_path, "src/b/mod.py", "def b_widget():\n    pass\n")
        ticket = _ticket(state=TicketState.IN_PROGRESS, scope=("src/a/**", "src/b/**"))

        from frob.gates._prework import sweep_ticket

        result = sweep_ticket(tmp_path, ticket, budget_seconds=0.0)
        assert result.is_ok
        sweep = result.danger_ok
        assert sweep.partial is True
        assert set(sweep.pending_patterns) == {"src/a/**", "src/b/**"}
        assert sweep.xref_hits == ()

    # frob:ticket T-0584
    def test_sweep_ticket_resumes_pending_patterns(self, tmp_path: Path) -> None:
        """A follow-up call with a real budget picks up exactly the patterns
        the prior partial sweep left pending, and does not re-derive hits
        for patterns it already recorded."""
        # frob:tests src/frob/gates/_prework.py::sweep_ticket
        _write(tmp_path, "src/a/mod.py", "def a_widget():\n    pass\n")
        _write(tmp_path, "src/b/mod.py", "def b_widget():\n    pass\n")
        ticket = _ticket(state=TicketState.IN_PROGRESS, scope=("src/a/**", "src/b/**"))

        from frob.gates._prework import sweep_ticket

        first = sweep_ticket(tmp_path, ticket, budget_seconds=0.0)
        assert first.is_ok
        assert first.danger_ok.partial is True

        resumed = sweep_ticket(tmp_path, ticket, budget_seconds=None)
        assert resumed.is_ok
        sweep = resumed.danger_ok
        assert sweep.partial is False
        assert sweep.pending_patterns == ()
        assert set(sweep.xref_hits) == {"a_widget", "b_widget"}


class TestActiveTicket:
    def test_explicit_flag_wins(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_waive_lease.py::active_ticket
        _git_init(tmp_path)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "T-0002-other"], cwd=tmp_path, check=True
        )
        result = active_ticket(tmp_path, "T-0001")
        assert result.is_some
        assert result.danger_some == "T-0001"

    def test_branch_regex_match(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        subprocess.run(
            ["git", "checkout", "-q", "-b", "T-0042-do-a-thing"],
            cwd=tmp_path,
            check=True,
        )
        result = active_ticket(tmp_path, None)
        assert result.is_some
        assert result.danger_some == "T-0042"

    def test_nothing_fallback(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        result = active_ticket(tmp_path, None)
        assert result.is_nothing


# T-0265: a `frob:tests` directive whose target is written with pytest's
# `Class::method` collect-only separator, on a test that ALSO names itself
# (self-referential) -- the mismatched separator means the string differs
# from the graph's own dotted `Class.method` qualname, so the edge is
# genuinely dangling (T-0237/`TestTest010KindValidation.test_dangling_
# tests_endpoint_still_caught_by_drift002` already documents that a
# `frob:tests` edge's CODE-side endpoint not resolving is DRIFT002's job,
# no TESTS-specific resolver needed -- a self-referential target is not
# special-cased at all: this repo's own widespread convention of a test
# naming itself via a CORRECTLY-formed dotted target is exactly as valid
# as any other `frob:tests` edge, see every `TestDebtGate`/
# `TestDeprecatedGate` method above). What WAS missing is that a caller
# who narrows `gates` to a small subset (the shape a ticket-scoped
# pre-flight check uses) never evaluated `drift` at all, so this same
# dangling edge could be invisible on that path while a wider selection
# caught it -- fixed in `frob.gates._build_jobs` (drift now always runs
# regardless of the caller's `gates` selection).
class TestSelfReferentialTestsDirectiveScopeAgreement:
    """T-0265 regression: a dangling self-referential `frob:tests` target
    must be caught the same way regardless of which gate subset a caller
    selects -- a narrowly-scoped run must never disagree with a wider one."""

    #: A test naming itself with pytest's `Class::method` collect-only
    #: separator instead of the graph's own dotted `Class.method` qualname
    #: -- the two strings differ, so this is a genuinely dangling edge.
    _MISMATCHED_SEPARATOR_SOURCE = (
        "class TestFoo:\n"
        "    # frob:tests tests/test_x.py::TestFoo::test_self\n"
        "    def test_self(self) -> None:\n"
        "        assert True\n"
    )

    def test_narrow_gate_selection_still_surfaces_drift_for_the_same_diff(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/gates_suite/test_prework.py::TestSelfReferentialTestsDirectiveScopeAgreement.test_narrow_gate_selection_still_surfaces_drift_for_the_same_diff  # noqa: E501
        # Same fixture, evaluated through BOTH paths: a caller that narrows
        # `gates` to a small subset (the shape a ticket-scoped pre-flight
        # check uses) and a wider selection. Proves the SHARED mechanism --
        # `run_gates` always folding `drift` into the job set -- is what
        # closes the gap.
        _git_init(tmp_path)
        _write(tmp_path, "tests/test_x.py", self._MISMATCHED_SEPARATOR_SOURCE)
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "add self-tests"], cwd=tmp_path, check=True
        )

        narrow_cfg = GateConfig(
            root=str(tmp_path), base="main", gates=frozenset({"scope"})
        )
        narrow_result = run_gates(narrow_cfg)
        assert narrow_result.is_ok

        # "Full" here is deliberately still a thread-only gate selection
        # (drift + scope), not a bare `GateConfig()` default -- the
        # unrestricted default additionally selects `_PROCESS_POOL_GATES`
        # (archgate/sys/clones/perf/pii_structural/secrets/dead_symbols),
        # and `_run_combined_jobs` forks that `ProcessPoolExecutor` from
        # inside an still-active `ThreadPoolExecutor` block -- a real,
        # pre-existing fork/thread-safety hazard (a fork while another
        # thread holds e.g. the logging lock can deadlock the child) that
        # is unrelated to this ticket's scope and reproduced independently
        # under heavy parallel test load. Restricting to thread-only gates
        # here keeps this regression deterministic while still proving the
        # exact claim T-0265 cares about: a caller that narrows `gates` no
        # longer disagrees with a wider selection on whether DRIFT002 fires.
        full_cfg = GateConfig(
            root=str(tmp_path), base="main", gates=frozenset({"scope", "drift"})
        )
        full_result = run_gates(full_cfg)
        assert full_result.is_ok

        # Both paths now agree: DRIFT002 fires either way -- the
        # narrow, ticket-scoped-shaped selection is no longer green while
        # the wider run is red for the identical tree.
        narrow_rules = _rules(narrow_result.danger_ok.violations)
        full_rules = _rules(full_result.danger_ok.violations)
        assert "DRIFT002" in narrow_rules
        assert "DRIFT002" in full_rules


class TestBaselineDelta:
    """T-0095: baseline stamp + --delta filtering."""

    def test_fingerprint_ignores_line_number(self) -> None:
        # frob:tests src/frob/gates/_baseline.py::violation_fingerprint kind="unit"
        a = _violation(line=1)
        b = _violation(line=99)
        assert violation_fingerprint(a) == violation_fingerprint(b)

    def test_fingerprint_differs_on_rule_file_or_message(self) -> None:
        base = _violation()
        assert violation_fingerprint(base) != violation_fingerprint(
            _violation(rule="R2")
        )
        assert violation_fingerprint(base) != violation_fingerprint(
            _violation(file="b.py")
        )
        assert violation_fingerprint(base) != violation_fingerprint(
            _violation(message="other")
        )

    def test_stamp_and_load_round_trip(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_baseline.py::stamp_baseline kind="unit"
        _write(tmp_path, "src/a.py", "def f():\n    pass\n")
        violations = (_violation(file="src/a.py"),)
        result = stamp_baseline(tmp_path, violations)
        assert result.is_ok
        baseline = load_baseline(tmp_path)
        assert baseline is not None
        assert violation_fingerprint(violations[0]) in baseline["fingerprints"]

    def test_load_baseline_missing_is_none(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_baseline.py::load_baseline kind="unit"
        assert load_baseline(tmp_path) is None

    def test_load_baseline_malformed_json_is_none(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_baseline.py::load_baseline kind="unit"
        """A `.frob/baseline` file that exists but is not valid JSON must
        hit the `except (OSError, ValueError)` branch and return `None`,
        not raise -- distinct from the missing-file branch above."""
        stamp_path = tmp_path / ".frob" / "baseline"
        stamp_path.parent.mkdir(parents=True, exist_ok=True)
        stamp_path.write_text("{not valid json", encoding="utf-8")
        assert load_baseline(tmp_path) is None

    def test_delta_filters_known_violations(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_baseline.py::delta_violations kind="unit"
        _write(tmp_path, "src/a.py", "def f():\n    pass\n")
        old = _violation(file="src/a.py", message="old")
        stamp_baseline(tmp_path, (old,))
        baseline = load_baseline(tmp_path)
        assert baseline is not None
        new = _violation(file="src/a.py", message="new")
        kept = delta_violations((old, new), baseline)
        assert kept == (new,)

    def test_baseline_not_stale_when_files_unchanged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_baseline.py::is_baseline_stale kind="unit"
        _write(tmp_path, "src/a.py", "def f():\n    pass\n")
        stamp_baseline(tmp_path, (_violation(file="src/a.py"),))
        baseline = load_baseline(tmp_path)
        assert baseline is not None
        assert is_baseline_stale(tmp_path, baseline) is False

    def test_baseline_stale_when_file_changes(self, tmp_path: Path) -> None:
        _write(tmp_path, "src/a.py", "def f():\n    pass\n")
        stamp_baseline(tmp_path, (_violation(file="src/a.py"),))
        baseline = load_baseline(tmp_path)
        assert baseline is not None
        _write(tmp_path, "src/a.py", "def f():\n    return 1\n")
        assert is_baseline_stale(tmp_path, baseline) is True
