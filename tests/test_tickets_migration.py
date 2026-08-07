"""T-1259: ledger v2 migration -- `migrate_v1_to_v2`'s golden round-trip
and the LEDGERV1001 deprecation gate.

Design doc: docs/design/ledger-v2.md section 7 ("Migration"). This module
covers deliverable 1 (the one-shot, reversible v1 -> v2 migrator) and
deliverable 3 (the deprecation gate) -- deliverable 4 (final cutover) is
deliberately NOT exercised here; see this ticket's Done report for cutover
posture.
"""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

from frob.gates import Severity
from frob.gates._tickets_gate import _LEDGERV1_SUNSET, _ledgerv1001_violations
from frob.tickets._models import (
    AcceptanceCriterion,
    Attachment,
    Origin,
    Ticket,
    TicketKind,
    TicketState,
)
from frob.tickets._store import (
    _parse_ledger,
    _store_mode,
    archive_path,
    atomic_write,
    attachments_dir,
    ledger_path,
    load_all,
    load_archive,
    migrate_v1_to_v2,
    v2_archive_dir,
    v2_done_report_path,
    v2_ticket_dir,
)

_FIXTURE_ATTACHMENT = (
    Path(__file__).parent / "fixtures" / "tickets" / "sample-attachment.txt"
)


# frob:waive WIRE001 reason="test-fixture builder for this module's own \
# golden-round-trip ledger (called by _seed_v1_fixture below, same file) -- no \
# production caller to wire it to by design" permanent="true"
def _git_init(root: Path) -> None:
    import subprocess

    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"], cwd=root, check=True
    )
    subprocess.run(["git", "config", "user.name", "T"], cwd=root, check=True)


# frob:waive WIRE001 reason="test-fixture builder, same shape/precedent as _git_init \
# above -- no production caller to wire it to by design" permanent="true"
def _done_ticket() -> Ticket:
    """A closed ticket carrying a real embedded '## Done report' section
    (the T-1259 case this migrator must split into done-report.md)."""
    return Ticket(
        id="T-0001",
        title="a completed ticket",
        state=TicketState.DONE,
        kind=TicketKind.BUG,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        evidence=("tests/test_example.py::test_thing",),
        acceptance=(
            AcceptanceCriterion(
                text="GIVEN a bug WHEN fixed THEN tests pass",
                evidence=("tests/test_example.py::test_thing",),
            ),
        ),
        body=(
            "## Description\nsome bug that was fixed.\n\n"
            "## Done report\n\n"
            "Fixed the thing.\n\n"
            "### Changed\n- src/example.py::thing\n\n"
            "### Evidence\n- tests/test_example.py::test_thing\n"
        ),
    )


# frob:waive WIRE001 reason="test-fixture builder, same shape/precedent as _git_init \
# above -- no production caller to wire it to by design" permanent="true"
def _queued_ticket() -> Ticket:
    """A queued ticket blocked on the done ticket above -- exercises
    `blocked_by` round-tripping unchanged."""
    return Ticket(
        id="T-0002",
        title="a queued follow-up",
        state=TicketState.QUEUED,
        kind=TicketKind.FEATURE,
        origin=Origin.AGENT,
        created=date(2026, 1, 2),
        blocked_by=("T-0001",),
        attachments=(
            Attachment(path="mockup.txt", caption="a sample mock", sha256="deadbeef"),
        ),
        body="## Description\nfollow-up work, blocked on T-0001.\n",
    )


# frob:waive WIRE001 reason="test-fixture builder, same shape/precedent as _git_init \
# above -- no production caller to wire it to by design" permanent="true"
def _draft_ticket() -> Ticket:
    """A draft-id ticket (filed mid-worktree, never yet renumbered) --
    T-1259 acceptance explicitly calls out a draft-id ticket as one of the
    fixture's required shapes."""
    return Ticket(
        id="T-draft-abc12345",
        title="an unlanded draft",
        state=TicketState.QUEUED,
        kind=TicketKind.BUG,
        origin=Origin.AGENT,
        created=date(2026, 1, 3),
        body="## Description\nfiled mid-worktree, not yet renumbered.\n",
    )


# frob:waive WIRE001 reason="test-fixture builder, same shape/precedent as _git_init \
# above -- no production caller to wire it to by design" permanent="true"
def _archived_ticket() -> Ticket:
    """An already-archived ticket -- migration must place it under
    tickets/archive/T-####/, not tickets/T-####/."""
    return Ticket(
        id="T-0000",
        title="an old archived ticket",
        state=TicketState.DONE,
        kind=TicketKind.BUG,
        origin=Origin.HUMAN,
        created=date(2025, 6, 1),
        body="## Description\nancient history.\n\n## Done report\n\nDone long ago.\n",
    )


# frob:waive WIRE001 reason="test-fixture builder, same shape/precedent as _git_init \
# above -- no production caller to wire it to by design" permanent="true"
def _seed_v1_fixture(root: Path) -> dict[str, Ticket]:
    """Write a v1-mode monofile ledger + archive covering every shape T-1259
    acceptance[3] names: a done ticket with a Done report, a queued ticket
    with blocked_by, a ticket with attachments, an archived ticket, and a
    draft-id ticket. Returns the id -> Ticket map as constructed, for the
    caller's own semantic-equality comparison."""
    from frob.tickets._store import atomic_write, ledger_path, write_all, write_archive

    # T-1553: the fresh-repo default flipped to v2 -- pin v1/'single' mode
    # explicitly (an unseeded root would now write these fixture tickets
    # straight into v2 layout, defeating this migrator fixture's whole
    # point).
    assert atomic_write(ledger_path(root), "# Tickets\n\n").is_ok
    active = {t.id: t for t in (_done_ticket(), _queued_ticket(), _draft_ticket())}
    assert write_all(root, active).is_ok
    archived = {_archived_ticket().id: _archived_ticket()}
    assert write_archive(root, archived).is_ok

    dest = attachments_dir(root, "T-0002")
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(_FIXTURE_ATTACHMENT, dest / "mockup.txt")

    active.update(archived)
    return active


class TestMigrateV1ToV2:
    """`migrate_v1_to_v2`'s own behavior: mode detection, per-shape writes,
    reversibility (monofiles untouched), and the golden round-trip."""

    def test_migrates_one_active_ticket_with_done_report(self, tmp_path: Path) -> None:
        """The Done report splits out into its own done-report.md; the
        remaining ticket.md carries the frontmatter+description only."""
        _git_init(tmp_path)
        _seed_v1_fixture(tmp_path)

        result = migrate_v1_to_v2(tmp_path)
        assert result.is_ok
        assert result.danger_ok == 4

        ticket_md = (v2_ticket_dir(tmp_path, "T-0001") / "ticket.md").read_text(
            encoding="utf-8"
        )
        assert "## Done report" not in ticket_md
        assert "some bug that was fixed" in ticket_md

        report = v2_done_report_path(tmp_path, "T-0001").read_text(encoding="utf-8")
        assert report.startswith("## Done report")
        assert "Fixed the thing." in report

    def test_monofiles_left_in_place_reversible(self, tmp_path: Path) -> None:
        """Design section 7: migrate must NOT delete tickets.md/
        tickets-archive.md in the same call -- rollback is just deleting
        the new v2 directories."""
        _git_init(tmp_path)
        _seed_v1_fixture(tmp_path)
        before_ledger = ledger_path(tmp_path).read_text(encoding="utf-8")
        before_archive = archive_path(tmp_path).read_text(encoding="utf-8")

        assert migrate_v1_to_v2(tmp_path).is_ok

        assert ledger_path(tmp_path).exists()
        assert archive_path(tmp_path).exists()
        assert ledger_path(tmp_path).read_text(encoding="utf-8") == before_ledger
        assert archive_path(tmp_path).read_text(encoding="utf-8") == before_archive

    def test_attachment_moved_under_ticket_dir(self, tmp_path: Path) -> None:
        """T-0002's legacy tickets/attachments/T-0002/mockup.txt relocates
        to tickets/T-0002/attachments/mockup.txt, byte for byte."""
        _git_init(tmp_path)
        _seed_v1_fixture(tmp_path)

        assert migrate_v1_to_v2(tmp_path).is_ok

        moved = v2_ticket_dir(tmp_path, "T-0002") / "attachments" / "mockup.txt"
        assert moved.is_file()
        assert moved.read_bytes() == _FIXTURE_ATTACHMENT.read_bytes()

    def test_archived_ticket_lands_under_archive_dir(self, tmp_path: Path) -> None:
        """T-0000 (already archived pre-migration) lands under
        tickets/archive/T-0000/, not tickets/T-0000/."""
        _git_init(tmp_path)
        _seed_v1_fixture(tmp_path)

        assert migrate_v1_to_v2(tmp_path).is_ok

        assert (v2_archive_dir(tmp_path, "T-0000") / "ticket.md").is_file()
        assert not (v2_ticket_dir(tmp_path, "T-0000") / "ticket.md").is_file()

    def test_draft_id_ticket_migrates_like_any_other(self, tmp_path: Path) -> None:
        """A T-draft-* id is just another directory name -- no special
        casing (design section 1.1)."""
        _git_init(tmp_path)
        _seed_v1_fixture(tmp_path)

        assert migrate_v1_to_v2(tmp_path).is_ok

        assert (v2_ticket_dir(tmp_path, "T-draft-abc12345") / "ticket.md").is_file()

    def test_idempotent_no_v1_state_is_a_no_op(self, tmp_path: Path) -> None:
        """Once a repo is already v2-mode, migrate is a safe Ok(0) no-op --
        it never re-reads a monofile ledger that is no longer authoritative."""
        _git_init(tmp_path)
        _seed_v1_fixture(tmp_path)
        assert migrate_v1_to_v2(tmp_path).is_ok
        assert _store_mode(tmp_path) == "v2"

        second = migrate_v1_to_v2(tmp_path)
        assert second.is_ok
        assert second.danger_ok == 0

    def test_golden_round_trip_semantic_equality(self, tmp_path: Path) -> None:
        """GIVEN the fixture monofile ledger (T-1259 acceptance[3])
        WHEN migrated to v2 THEN the same id set and equal per-ticket
        field values and Done-report text come back out, even though the
        storage shape changed completely (monofile sections ->
        per-ticket directories, Done report split into its own file)."""
        _git_init(tmp_path)
        original = _seed_v1_fixture(tmp_path)

        original_active_text = ledger_path(tmp_path).read_text(encoding="utf-8")
        original_archive_text = archive_path(tmp_path).read_text(encoding="utf-8")
        original_active = _parse_ledger(original_active_text).danger_ok
        original_archived = _parse_ledger(original_archive_text).danger_ok
        assert set(original_active) | set(original_archived) == set(original)

        assert migrate_v1_to_v2(tmp_path).is_ok

        migrated_active = load_all(tmp_path).danger_ok
        migrated_archived = load_archive(tmp_path).danger_ok

        assert set(migrated_active) == set(original_active)
        assert set(migrated_archived) == set(original_archived)

        for ticket_id, before in {**original_active, **original_archived}.items():
            after = migrated_active.get(ticket_id) or migrated_archived.get(ticket_id)
            assert after is not None
            # Every non-body field round-trips unchanged.
            before_fields = before.model_dump(mode="json", exclude={"body"})
            after_fields = after.model_dump(mode="json", exclude={"body"})
            assert before_fields == after_fields, ticket_id

            # The Done report text itself round-trips, just relocated from
            # the body into its own file.
            from frob.tickets._models import recover_done_report_why
            from frob.tickets._store import read_done_report

            before_why = recover_done_report_why(before.body)
            after_report = read_done_report(tmp_path, ticket_id)
            if before_why is None:
                assert after_report is None
            else:
                assert after_report is not None
                assert before_why in after_report


class TestMigrateCliToV2Flag:
    """T-1492: `frob ticket migrate --to v2` wires onto `migrate_v1_to_v2`
    via `AppConfig.ticket_migrate_to`/`ticket_runner._migrate`, and `--to`
    omitted keeps the original collapse-dir-into-monofile behavior."""

    def test_migrate_to_v2_flag_calls_migrate_v1_to_v2(
        self, tmp_path: Path, caplog
    ) -> None:
        # frob:tests \
        # tests/test_tickets_migration.py::TestMigrateCliToV2Flag.test_migrate_to_v2_fl\
        # ag_calls_migrate_v1_to_v2 kind="unit"
        import logging

        from frob.app import ticket_runner
        from frob.app.config import AppConfig

        _git_init(tmp_path)
        _seed_v1_fixture(tmp_path)
        assert _store_mode(tmp_path) == "single"

        cfg = AppConfig(
            ticket_command="migrate", ticket_path=tmp_path, ticket_migrate_to="v2"
        )
        with caplog.at_level(logging.INFO, logger="frob.app.ticket_runner"):
            ticket_runner.run(cfg)

        assert _store_mode(tmp_path) == "v2"
        assert (v2_ticket_dir(tmp_path, "T-0001") / "ticket.md").is_file()
        # Original monofiles are left in place (migrate_v1_to_v2 is
        # reversible, never deletes the v1 ledgers itself).
        assert ledger_path(tmp_path).exists()

    def test_migrate_without_to_keeps_dir_collapse_behavior(
        self, tmp_path: Path, caplog
    ) -> None:
        # frob:tests \
        # tests/test_tickets_migration.py::TestMigrateCliToV2Flag.test_migrate_without_\
        # to_keeps_dir_collapse_behavior kind="unit"
        import logging

        from frob.app import ticket_runner
        from frob.app.config import AppConfig

        _git_init(tmp_path)
        (tmp_path / "tickets.md").write_text("# Tickets\n\n", encoding="utf-8")

        cfg = AppConfig(ticket_command="migrate", ticket_path=tmp_path)
        with caplog.at_level(logging.INFO, logger="frob.app.ticket_runner"):
            ticket_runner.run(cfg)

        assert "no legacy tickets/*.md files to migrate" in "\n".join(
            r.getMessage() for r in caplog.records if r.name == "frob.app.ticket_runner"
        )
        assert _store_mode(tmp_path) == "single"


class TestLedgerV1DeprecationGate:
    """LEDGERV1001 (ledger v2 design section 7, deliverable 3): the
    escalation-after-expiry warning naming `frob ticket migrate --to v2`."""

    def test_monofile_mode_warns_before_sunset(self, tmp_path: Path) -> None:
        """A real monofile-mode repo, today's date still inside the
        recorded window, gets exactly one WARN."""
        assert date.today().isoformat() <= _LEDGERV1_SUNSET, (
            "this test's premise (today is still within the recorded "
            "compatibility window) no longer holds -- see docs/modules/"
            "tickets.md's ledger-v2 migration note"
        )
        _git_init(tmp_path)
        atomic_write(ledger_path(tmp_path), "# Tickets\n\n")
        violations = _ledgerv1001_violations(tmp_path)
        assert len(violations) == 1
        assert violations[0].rule == "LEDGERV1001"
        assert violations[0].severity == Severity.WARN
        assert "frob ticket migrate --to v2" in violations[0].message

    def test_monofile_mode_errors_past_sunset(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Once the recorded sunset has passed, the same finding escalates
        to a hard ERROR (mirrors DEPR004's own expiry escalation)."""
        _git_init(tmp_path)
        atomic_write(ledger_path(tmp_path), "# Tickets\n\n")

        monkeypatch.setattr("frob.gates._tickets_gate._LEDGERV1_SUNSET", "2000-01-01")
        violations = _ledgerv1001_violations(tmp_path)
        assert len(violations) == 1
        assert violations[0].severity == Severity.ERROR

    def test_v2_mode_repo_is_silent(self, tmp_path: Path) -> None:
        """A repo already migrated to v2 never fires LEDGERV1001 -- there
        is nothing left to warn about."""
        _git_init(tmp_path)
        _seed_v1_fixture(tmp_path)
        assert migrate_v1_to_v2(tmp_path).is_ok
        # v2-mode alone is not enough to make the gate silent unless the
        # v2 tree is what `_store_mode` actually reports -- confirm the
        # premise before asserting the gate's own behavior.
        assert _store_mode(tmp_path) == "v2"
        assert _ledgerv1001_violations(tmp_path) == ()

    def test_no_ledger_content_at_all_is_silent(self, tmp_path: Path) -> None:
        """A from-scratch repo with zero ticket content of either shape
        must never fire LEDGERV1001 -- `_store_mode`'s fresh-repo DEFAULT
        ('single') is not the same thing as an actual monofile on disk,
        and plenty of existing gate tests construct exactly this bare
        tmp_path shape and assert `tickets_gate(...) == ()`."""
        assert _ledgerv1001_violations(tmp_path) == ()
