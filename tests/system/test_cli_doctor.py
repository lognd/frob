"""End-to-end litmus for `frob doctor` (T-0319): a first-class CLI surface
for the native-extension check that `docs/guides/install.md`'s T-0316
section previously described only as a manual `python3 -c "import
strata_core, frob_core"` paragraph.

`tests/fixtures/fake_no_native/strata_core.py` shadows the real compiled
extension via `PYTHONPATH` order (same fixture `test_cli_native_missing.py`
uses), so the natives-absent case exercises the real subprocess CLI path
end to end, not a monkeypatched import.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

FROB = [sys.executable, "-m", "frob"]

_FAKE_NATIVE_DIR = str(Path(__file__).parent.parent / "fixtures" / "fake_no_native")


def _run_with_faked_missing_native(
    *args: str, cwd: Path
) -> subprocess.CompletedProcess:
    """Run `frob <args>` in a subprocess whose `PYTHONPATH` shadows the real
    `strata_core` with the raise-on-import fixture, so `frob doctor` sees
    exactly what a natives-less `uv tool install frob` sees."""
    env = dict(os.environ)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        _FAKE_NATIVE_DIR
        if not existing
        else f"{_FAKE_NATIVE_DIR}{os.pathsep}{existing}"
    )
    return subprocess.run(
        FROB + list(args), cwd=cwd, capture_output=True, text=True, env=env
    )


class TestDoctorCli:
    # frob:tests src/frob/doctor.py
    def test_doctor_reports_healthy_when_natives_present(self, tmp_path: Path) -> None:
        """A normal environment (this worktree's own built natives) reports
        healthy and exits 0."""
        r = subprocess.run(
            FROB + ["doctor"], cwd=tmp_path, capture_output=True, text=True
        )
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        assert "frob_core" in out
        assert "strata_core" in out

    def test_doctor_json_reports_healthy_when_natives_present(
        self, tmp_path: Path
    ) -> None:
        """`--json` emits a parseable `DoctorReport` with `healthy: true`."""
        r = subprocess.run(
            FROB + ["doctor", "--json"], cwd=tmp_path, capture_output=True, text=True
        )
        assert r.returncode == 0, r.stdout + r.stderr
        report = json.loads(r.stdout)
        assert report["healthy"] is True
        assert report["remediation"] is None
        names = {ext["name"] for ext in report["extensions"]}
        assert names == {"frob_core", "strata_core"}

    def test_doctor_fails_loud_when_native_missing(self, tmp_path: Path) -> None:
        """A faked-missing `strata_core` exits nonzero and prints the exact
        remediation, not a silent/degraded pass."""
        r = _run_with_faked_missing_native("doctor", cwd=tmp_path)
        out = r.stdout + r.stderr
        assert r.returncode != 0, out
        assert "strata_core" in out
        assert "NOT importable" in out or "not importable" in out
        assert "make core" in out or "make install-tool" in out

    def test_doctor_json_fails_loud_when_native_missing(self, tmp_path: Path) -> None:
        """`--json` on a natives-missing environment reports `healthy: false`
        with the remediation hint and still exits nonzero."""
        r = _run_with_faked_missing_native("doctor", "--json", cwd=tmp_path)
        assert r.returncode != 0, r.stdout + r.stderr
        report = json.loads(r.stdout)
        assert report["healthy"] is False
        assert report["remediation"]
        by_name = {ext["name"]: ext for ext in report["extensions"]}
        assert by_name["strata_core"]["available"] is False


class TestDoctorDerivedStateManifest:
    """T-0570: `frob doctor` fingerprints every derived artifact it knows
    about (`.frob/cache.db`, `.frob/dup.db`, `.frob/vet.db`,
    `.frob/coverage-stamp`, `.frob/baseline`, `frob-coverage.lock.json`) and
    reports corruption before any gate consumes the stale/corrupt state."""

    # frob:tests src/frob/doctor.py
    def test_verify_derived_state_reports_absent_as_healthy(
        self, tmp_path: Path
    ) -> None:
        """No `.frob/` at all (a fresh checkout) reports every artifact as
        absent-and-healthy, never as a false corruption finding."""
        from frob.doctor import verify_derived_state

        statuses = verify_derived_state(tmp_path)
        assert statuses
        assert all(not s.present and s.healthy for s in statuses)

    # frob:tests src/frob/doctor.py
    def test_verify_derived_state_flags_corrupt_sqlite_cache(
        self, tmp_path: Path
    ) -> None:
        """A `.frob/dup.db` that is not actually SQLite bytes (the T-0517
        stale/corrupt-fixture-cache incident shape) is reported unhealthy
        with a fingerprint and an explanatory detail, not silently passed
        through to whatever reads it next."""
        from frob.doctor import verify_derived_state

        frob_dir = tmp_path / ".frob"
        frob_dir.mkdir()
        (frob_dir / "dup.db").write_bytes(b"not a real sqlite file")

        statuses = verify_derived_state(tmp_path)
        by_name = {s.name: s for s in statuses}
        dup_cache = by_name["dup-cache"]
        assert dup_cache.present is True
        assert dup_cache.healthy is False
        assert dup_cache.fingerprint is not None
        assert dup_cache.detail is not None

    # frob:tests src/frob/doctor.py
    def test_verify_derived_state_flags_malformed_json_stamp(
        self, tmp_path: Path
    ) -> None:
        """A `.frob/coverage-stamp` that is not valid JSON is reported
        unhealthy with a detail explaining why."""
        from frob.doctor import verify_derived_state

        frob_dir = tmp_path / ".frob"
        frob_dir.mkdir()
        (frob_dir / "coverage-stamp").write_text("{not json")

        statuses = verify_derived_state(tmp_path)
        by_name = {s.name: s for s in statuses}
        stamp = by_name["coverage-stamp"]
        assert stamp.present is True
        assert stamp.healthy is False
        assert stamp.detail is not None

    # frob:tests src/frob/doctor.py
    def test_verify_derived_state_accepts_valid_json_stamp(
        self, tmp_path: Path
    ) -> None:
        """A well-formed `.frob/baseline` is reported present and healthy,
        with a stable content fingerprint."""
        from frob.doctor import verify_derived_state

        frob_dir = tmp_path / ".frob"
        frob_dir.mkdir()
        (frob_dir / "baseline").write_text('{"violations": []}')

        statuses = verify_derived_state(tmp_path)
        by_name = {s.name: s for s in statuses}
        baseline = by_name["baseline"]
        assert baseline.present is True
        assert baseline.healthy is True
        assert baseline.fingerprint is not None

    # frob:tests src/frob/doctor.py
    def test_run_diagnosis_unhealthy_when_derived_state_corrupt(
        self, tmp_path: Path
    ) -> None:
        """`run_diagnosis(root)` folds a corrupt derived artifact into the
        overall `healthy` verdict and names it in `remediation`, even when
        every native extension is available."""
        from frob.doctor import run_diagnosis

        frob_dir = tmp_path / ".frob"
        frob_dir.mkdir()
        (frob_dir / "cache.db").write_bytes(b"garbage")

        report = run_diagnosis(tmp_path)
        assert report.healthy is False
        assert report.remediation is not None
        assert "graph-cache" in report.remediation
        corrupt_names = {d.name for d in report.derived_state if not d.healthy}
        assert "graph-cache" in corrupt_names

    # frob:tests src/frob/doctor.py
    def test_run_diagnosis_healthy_with_no_derived_state(self, tmp_path: Path) -> None:
        """`run_diagnosis(root)` against a directory with no `.frob/` at all
        stays healthy (matching the natives-only historical behavior) --
        an empty derived-state manifest is not itself a failure."""
        from frob.doctor import run_diagnosis

        report = run_diagnosis(tmp_path)
        assert report.healthy is True
        assert all(not d.present for d in report.derived_state)


class TestDoctorDerivedStateDrift:
    """T-0604: `frob doctor` persists a fingerprint manifest each run and
    reports content drift against the PREVIOUS run's manifest -- an
    artifact rewritten out-of-band between two `frob doctor` invocations,
    distinct from T-0570's per-run corruption check."""

    # frob:tests src/frob/doctor.py
    def test_first_run_reports_no_drift_and_writes_manifest(
        self, tmp_path: Path
    ) -> None:
        """A brand-new tree has no prior manifest to compare against, so
        the first `run_diagnosis` call reports zero drift -- and leaves a
        manifest behind for the next call to compare against."""
        from frob.doctor import run_diagnosis

        frob_dir = tmp_path / ".frob"
        frob_dir.mkdir()
        (frob_dir / "baseline").write_text('{"violations": []}')

        report = run_diagnosis(tmp_path)
        assert report.drift == []
        assert (frob_dir / "derived-state-manifest.json").exists()

    # frob:tests src/frob/doctor.py
    def test_rewritten_artifact_between_two_runs_reports_drift(
        self, tmp_path: Path
    ) -> None:
        """An artifact rewritten (still validly-formatted) between two
        `frob doctor` runs is reported as drift naming both fingerprints
        -- the T-0604 acceptance case."""
        from frob.doctor import run_diagnosis

        frob_dir = tmp_path / ".frob"
        frob_dir.mkdir()
        (frob_dir / "baseline").write_text('{"violations": []}')

        first = run_diagnosis(tmp_path)
        assert first.drift == []

        # Simulate a foreign process/stale tool rewriting the artifact
        # out-of-band, between the two doctor invocations.
        (frob_dir / "baseline").write_text('{"violations": ["something new"]}')

        second = run_diagnosis(tmp_path)
        assert len(second.drift) == 1
        drifted = second.drift[0]
        assert drifted.name == "baseline"
        assert drifted.previous_fingerprint != drifted.current_fingerprint
        assert drifted.previous_fingerprint
        assert drifted.current_fingerprint

    # frob:tests src/frob/doctor.py
    def test_drift_is_informational_and_does_not_affect_healthy(
        self, tmp_path: Path
    ) -> None:
        """Drift alone (a validly-formatted artifact that simply changed)
        must never flip `healthy` to False -- ordinary cache churn between
        two `frob doctor` runs (frob's own tools rewriting their own
        caches) is expected, not a failure."""
        from frob.doctor import run_diagnosis

        frob_dir = tmp_path / ".frob"
        frob_dir.mkdir()
        (frob_dir / "baseline").write_text('{"violations": []}')

        run_diagnosis(tmp_path)
        (frob_dir / "baseline").write_text('{"violations": ["something new"]}')
        second = run_diagnosis(tmp_path)

        assert second.drift != []
        assert second.healthy is True

    # frob:tests src/frob/doctor.py
    def test_unchanged_artifact_reports_no_drift(self, tmp_path: Path) -> None:
        """An artifact that is byte-identical across two runs is never
        reported as drift."""
        from frob.doctor import run_diagnosis

        frob_dir = tmp_path / ".frob"
        frob_dir.mkdir()
        (frob_dir / "baseline").write_text('{"violations": []}')

        run_diagnosis(tmp_path)
        second = run_diagnosis(tmp_path)

        assert second.drift == []

    # frob:tests src/frob/doctor.py
    def test_malformed_manifest_is_treated_as_no_prior_run(
        self, tmp_path: Path
    ) -> None:
        """A corrupt/malformed manifest file (itself derived state) must
        not crash `run_diagnosis` -- it degrades to "no prior data",
        exactly like a missing manifest."""
        from frob.doctor import run_diagnosis

        frob_dir = tmp_path / ".frob"
        frob_dir.mkdir()
        (frob_dir / "baseline").write_text('{"violations": []}')
        (frob_dir / "derived-state-manifest.json").write_text("not json at all")

        report = run_diagnosis(tmp_path)
        assert report.drift == []
        assert report.healthy is True


class TestDoctorScaffoldConformance:
    """T-0736: `frob doctor` folds managed-boilerplate-block conformance
    into the overall verdict, opt-in on `frob.toml` existing."""

    # frob:tests src/frob/doctor.py
    def test_run_diagnosis_ignores_non_frob_directory(self, tmp_path: Path) -> None:
        """No `frob.toml` under `root` -- a bare directory, same as every
        other doctor test's `tmp_path` -- reports an empty scaffold-blocks
        list and never drags `healthy` down for it."""
        from frob.doctor import run_diagnosis

        report = run_diagnosis(tmp_path)
        assert report.scaffold_blocks == []
        assert report.healthy is True

    # frob:tests src/frob/doctor.py
    def test_run_diagnosis_unhealthy_when_scaffold_blocks_missing(
        self, tmp_path: Path
    ) -> None:
        """A `frob.toml`-bearing repo that has never run `frob scaffold
        apply` reports every managed block missing and folds that into an
        unhealthy verdict naming `frob scaffold apply` as the remedy."""
        from frob.doctor import run_diagnosis

        (tmp_path / "frob.toml").write_text("[project]\n")
        report = run_diagnosis(tmp_path)
        assert report.healthy is False
        assert report.scaffold_blocks
        assert all(not s.present for s in report.scaffold_blocks)
        assert report.remediation is not None
        assert "frob scaffold apply" in report.remediation

    # frob:tests src/frob/doctor.py
    def test_run_diagnosis_healthy_after_scaffold_apply(self, tmp_path: Path) -> None:
        """After `apply_managed_blocks`, the same repo reports every block
        present and not stale, and the overall verdict is healthy again
        (assuming natives/derived-state are otherwise clean)."""
        import subprocess

        from frob.doctor import run_diagnosis
        from frob.scaffold import apply_managed_blocks

        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
        (tmp_path / "frob.toml").write_text("[project]\n")
        result = apply_managed_blocks(tmp_path)
        assert result.is_ok

        report = run_diagnosis(tmp_path)
        assert all(s.present and not s.stale for s in report.scaffold_blocks)


class TestDoctorMutateJournal:
    """T-0857: `frob doctor` reports a stale `frob mutate` backup journal
    (a crashed prior run's not-yet-restored target) as an unhealthy
    verdict, read-only -- it never restores anything itself."""

    # frob:tests src/frob/doctor.py
    def test_run_diagnosis_healthy_with_no_mutate_journals(
        self, tmp_path: Path
    ) -> None:
        """No `.frob/mutate-backup/` at all -- the normal case -- reports
        an empty `mutate_journals` list and never drags `healthy` down."""
        from frob.doctor import run_diagnosis

        report = run_diagnosis(tmp_path)
        assert report.mutate_journals == []
        assert report.healthy is True

    # frob:tests src/frob/doctor.py
    def test_run_diagnosis_unhealthy_with_stale_mutate_journal(
        self, tmp_path: Path
    ) -> None:
        """A journal left by a crashed (dead-PID) `frob mutate` run folds
        into an unhealthy verdict naming the target and the fix."""
        from frob.doctor import run_diagnosis
        from frob.mutate._journal import write_journal

        target = tmp_path / "m.py"
        target.write_bytes(b"def add(a, b):\n    return a + b\n")
        dead_pid_proc = subprocess.Popen(["python3", "-c", "pass"])  # noqa: S603
        dead_pid_proc.wait()
        assert write_journal(
            tmp_path,
            target,
            b"def add(a, b):\n    return a + b\n",
            pid=dead_pid_proc.pid,
        ).is_ok

        report = run_diagnosis(tmp_path)
        assert report.healthy is False
        assert len(report.mutate_journals) == 1
        assert report.mutate_journals[0].target == "m.py"
        assert report.remediation is not None
        assert "m.py" in report.remediation
        assert "frob mutate" in report.remediation

    # frob:tests src/frob/doctor.py
    def test_run_diagnosis_ignores_journal_owned_by_live_pid(
        self, tmp_path: Path
    ) -> None:
        """A journal owned by a STILL-RUNNING pid (this test process
        itself) is an in-progress `frob mutate` run, not a crash -- doctor
        must not flag it, or every ordinary concurrent run would look
        broken."""
        from frob.doctor import run_diagnosis
        from frob.mutate._journal import write_journal

        target = tmp_path / "m.py"
        target.write_bytes(b"original\n")
        assert write_journal(tmp_path, target, b"original\n", pid=os.getpid()).is_ok

        report = run_diagnosis(tmp_path)
        assert report.mutate_journals == []
        assert report.healthy is True


class TestDoctorMalformedTicketEdges:
    """T-1132: `frob doctor` flags an existing malformed `blocked_by`/
    `parent` entry in the shared ledger (the T-0380 incident: an
    empty-string `blocked_by` entry left a ticket silently undoable for
    days with nothing surfacing why) -- read-only, it never repairs
    anything itself."""

    # frob:tests src/frob/doctor.py
    # frob:waive PII012 reason="test name mirrors the run_diagnosis API symbol it exercises; repository self-check machinery, no person-related data anywhere in the test"  # noqa: E501
    def test_run_diagnosis_healthy_with_no_malformed_edges(
        self, tmp_path: Path
    ) -> None:
        """No tickets.md at all (or one with only well-formed edges)
        reports an empty `malformed_ticket_edges` list."""
        from frob.doctor import run_diagnosis

        report = run_diagnosis(tmp_path)
        assert report.malformed_ticket_edges == []
        assert report.healthy is True

    # frob:tests src/frob/doctor.py::scan_malformed_ticket_edges
    def test_scan_flags_empty_string_blocked_by(self, tmp_path: Path) -> None:
        """The exact T-0380 repro: an empty-string blocked_by entry
        alongside real ones."""
        from frob.doctor import run_diagnosis

        (tmp_path / "tickets.md").write_text(
            "# Tickets\n\n"
            "<!-- ticket:T-0001 -->\n"
            "```yaml\n"
            "id: T-0001\n"
            "title: bad\n"
            "state: queued\n"
            "kind: bug\n"
            "origin: human\n"
            "created: 2026-01-01\n"
            'blocked_by: ["", "T-0002"]\n'
            "```\n"
        )

        report = run_diagnosis(tmp_path)
        assert report.healthy is False
        assert len(report.malformed_ticket_edges) == 1
        edge = report.malformed_ticket_edges[0]
        assert edge.ticket_id == "T-0001"
        assert edge.field == "blocked_by"
        assert edge.value == ""
        assert edge.ledger_file == "tickets.md"
        assert report.remediation is not None
        assert "T-0001.blocked_by" in report.remediation

    # frob:tests src/frob/doctor.py::scan_malformed_ticket_edges
    def test_scan_flags_malformed_parent(self, tmp_path: Path) -> None:
        """A `parent` value that is not a real ticket-id shape is flagged
        too, independent of `blocked_by`."""
        from frob.doctor import run_diagnosis

        (tmp_path / "tickets.md").write_text(
            "# Tickets\n\n"
            "<!-- ticket:T-0001 -->\n"
            "```yaml\n"
            "id: T-0001\n"
            "title: bad\n"
            "state: queued\n"
            "kind: bug\n"
            "origin: human\n"
            "created: 2026-01-01\n"
            "parent: nope\n"
            "```\n"
        )

        report = run_diagnosis(tmp_path)
        assert report.healthy is False
        assert len(report.malformed_ticket_edges) == 1
        assert report.malformed_ticket_edges[0].field == "parent"
        assert report.malformed_ticket_edges[0].value == "nope"

    # frob:tests src/frob/doctor.py::scan_malformed_ticket_edges
    def test_scan_ignores_well_formed_edges(self, tmp_path: Path) -> None:
        """Real T-#### and T-draft-<hex> edges are never flagged."""
        from frob.doctor import run_diagnosis

        (tmp_path / "tickets.md").write_text(
            "# Tickets\n\n"
            "<!-- ticket:T-0002 -->\n"
            "```yaml\n"
            "id: T-0002\n"
            "title: good\n"
            "state: queued\n"
            "kind: bug\n"
            "origin: human\n"
            "created: 2026-01-01\n"
            'blocked_by: ["T-0001", "T-draft-deadbeef"]\n'
            "parent: T-0001\n"
            "```\n"
        )

        report = run_diagnosis(tmp_path)
        assert report.malformed_ticket_edges == []
        assert report.healthy is True


class TestDoctorStaleTicketLeases:
    """T-1131 (the T-1050 incident): `frob doctor` reports any ticket
    stuck IN_PROGRESS with no live cross-worktree lease, reusing
    `frob.tickets._reconcile.reconcile`'s dry-run detection -- read-only,
    it never requeues anything itself."""

    @staticmethod
    def _git_init(root: Path) -> None:
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=str(root), check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=str(root),
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"], cwd=str(root), check=True
        )
        (root / ".gitkeep").write_text("")
        subprocess.run(["git", "add", "-A"], cwd=str(root), check=True)
        subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=str(root), check=True)

    # frob:tests src/frob/doctor.py
    # frob:waive PII012 reason="test name mirrors the run_diagnosis API symbol it exercises; repository self-check machinery, no person-related data anywhere in the test"  # noqa: E501
    def test_run_diagnosis_healthy_with_no_stale_leases(self, tmp_path: Path) -> None:
        """A fresh checkout with no tickets.md at all reports an empty
        `stale_ticket_leases` list."""
        from frob.doctor import run_diagnosis

        self._git_init(tmp_path)
        report = run_diagnosis(tmp_path)
        assert report.stale_ticket_leases == []
        assert report.healthy is True

    # frob:tests src/frob/doctor.py::scan_stale_ticket_leases
    def test_scan_flags_in_progress_ticket_with_no_lease(self, tmp_path: Path) -> None:
        """A ticket whose `state:` was set to in-progress WITHOUT ever
        going through `transition` (so no lease was recorded -- the exact
        shape a lease-stamp ledger sync onto a checkout produces, per
        `tests/test_ticket_reconcile.py`'s own fixture recipe) is flagged,
        with a remediation naming the fix."""
        from frob.doctor import run_diagnosis
        from frob.tickets import Origin, TicketKind, TicketSpec, new_ticket
        from frob.tickets._store import load_all, write_ticket

        self._git_init(tmp_path)
        created = new_ticket(
            tmp_path,
            TicketSpec(title="Stuck", kind=TicketKind.BUG, origin=Origin.AGENT),
        )
        assert created.is_ok
        ticket_id = created.danger_ok.id

        loaded = load_all(tmp_path)
        assert loaded.is_ok
        ticket = loaded.danger_ok[ticket_id]
        from frob.tickets import TicketState

        assert write_ticket(
            tmp_path, ticket.model_copy(update={"state": TicketState.IN_PROGRESS})
        ).is_ok

        report = run_diagnosis(tmp_path)
        assert report.healthy is False
        assert ticket_id in report.stale_ticket_leases
        assert report.remediation is not None
        assert ticket_id in report.remediation
        assert "frob ticket requeue" in report.remediation

        # T-1131: `frob doctor` is READ-ONLY -- it must never actually
        # requeue the ticket itself (that is scan_stale_ticket_leases's
        # `reconcile(root, apply=False)` call's whole point). Confirm the
        # ledger's own state is untouched by the scan.
        reloaded = load_all(tmp_path)
        assert reloaded.is_ok
        assert reloaded.danger_ok[ticket_id].state == TicketState.IN_PROGRESS

    # frob:tests src/frob/doctor.py::scan_stale_ticket_leases
    def test_scan_ignores_live_leased_ticket(self, tmp_path: Path) -> None:
        """A ticket started normally (via `transition`, which records a
        real lease) is never flagged."""
        from frob.doctor import run_diagnosis
        from frob.tickets import (
            Origin,
            TicketKind,
            TicketSpec,
            TicketState,
            new_ticket,
            transition,
        )

        self._git_init(tmp_path)
        created = new_ticket(
            tmp_path,
            TicketSpec(title="Live", kind=TicketKind.BUG, origin=Origin.AGENT),
        )
        assert created.is_ok
        ticket_id = created.danger_ok.id
        assert transition(tmp_path, ticket_id, TicketState.PLANNED).is_ok
        assert transition(tmp_path, ticket_id, TicketState.IN_PROGRESS).is_ok

        report = run_diagnosis(tmp_path)
        assert ticket_id not in report.stale_ticket_leases
        assert report.healthy is True

    # frob:tests src/frob/doctor.py::scan_stale_ticket_leases
    def test_scan_degrades_to_empty_on_a_malformed_ledger(self, tmp_path: Path) -> None:
        """A ledger `reconcile` cannot even load (malformed frontmatter)
        must not crash `frob doctor` -- `scan_stale_ticket_leases` degrades
        to an empty tuple, logging a warning, so one broken ledger row
        never blocks the OTHER native/derived-state/mutate-journal checks
        `run_diagnosis` also performs in the same call."""
        from frob.doctor import run_diagnosis

        self._git_init(tmp_path)
        (tmp_path / "tickets.md").write_text(
            "# Tickets\n\n<!-- ticket:T-0001 -->\n```yaml\nnot: [valid, ticket\n```\n"
        )

        report = run_diagnosis(tmp_path)
        assert report.stale_ticket_leases == []


# frob:ticket T-1161
class TestDoctorVenvShims:
    """T-1161 (the 2026-07-28 incident): `frob doctor` scans `.venv/bin/`
    entrypoint scripts for a shebang pointing at a python interpreter
    OUTSIDE this checkout's own venv -- a cross-worktree `uv` operation
    rewrote the root venv's `pytest` shim shebang in place, and once that
    other worktree was removed every `uv run pytest` broke with no direct
    diagnostic naming the real cause."""

    @staticmethod
    def _make_venv_bin(tmp_path: Path) -> Path:
        venv_bin = tmp_path / ".venv" / "bin"
        venv_bin.mkdir(parents=True)
        return venv_bin

    # frob:tests src/frob/doctor.py::scan_venv_shims
    def test_flags_shebang_outside_venv(self, tmp_path: Path) -> None:
        """A shim shebanged at a DIFFERENT (even if still-existing)
        worktree's `.venv/bin/python` is flagged, with a remediation
        naming the exact `uv sync --reinstall-package` repair command."""
        from frob.doctor import run_diagnosis, scan_venv_shims

        venv_bin = self._make_venv_bin(tmp_path)
        other_python = tmp_path.parent / "other-worktree" / ".venv" / "bin" / "python"
        pytest_shim = venv_bin / "pytest"
        pytest_shim.write_text(f"#!{other_python}\nfrom pytest import main\nmain()\n")
        pytest_shim.chmod(0o755)

        drifted = scan_venv_shims(tmp_path)
        assert len(drifted) == 1
        assert drifted[0].script == "pytest"
        assert drifted[0].shebang_path == str(other_python)

        report = run_diagnosis(tmp_path)
        assert report.healthy is False
        assert len(report.venv_shims) == 1
        assert report.remediation is not None
        assert "uv sync --reinstall-package" in report.remediation
        assert "pytest" in report.remediation

    # frob:tests src/frob/doctor.py::scan_venv_shims
    def test_clean_shebang_reports_nothing(self, tmp_path: Path) -> None:
        """A shim shebanged at THIS venv's own `.venv/bin/python` (the
        healthy, ordinary case) reports no drift and stays healthy."""
        from frob.doctor import run_diagnosis, scan_venv_shims

        venv_bin = self._make_venv_bin(tmp_path)
        own_python = venv_bin / "python"
        own_python.write_text("")
        pytest_shim = venv_bin / "pytest"
        pytest_shim.write_text(f"#!{own_python}\nfrom pytest import main\nmain()\n")
        pytest_shim.chmod(0o755)

        assert scan_venv_shims(tmp_path) == ()

        report = run_diagnosis(tmp_path)
        assert report.venv_shims == []
        assert report.healthy is True

    # frob:tests src/frob/doctor.py::scan_venv_shims
    def test_no_venv_directory_reports_nothing(self, tmp_path: Path) -> None:
        """A tree with no `.venv/bin/` at all (not yet set up) contributes
        zero findings, not an error -- an ordinary not-yet-set-up state,
        not drift."""
        from frob.doctor import scan_venv_shims

        assert scan_venv_shims(tmp_path) == ()
