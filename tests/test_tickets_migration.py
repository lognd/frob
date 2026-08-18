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
    _migrate_one_v2,
    _parse_ledger,
    _serialize_ticket,
    _store_mode,
    archive_path,
    atomic_write,
    attachments_dir,
    ledger_path,
    load_all,
    load_archive,
    migrate_missing_v2,
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
        """A repo already migrated to v2, with the monofiles ALSO deleted
        (the T-2356 cutover's second commit), never fires LEDGERV1001 --
        there is nothing left to warn about."""
        _git_init(tmp_path)
        _seed_v1_fixture(tmp_path)
        assert migrate_v1_to_v2(tmp_path).is_ok
        # v2-mode alone is not enough to make the gate silent unless the
        # v2 tree is what `_store_mode` actually reports -- confirm the
        # premise before asserting the gate's own behavior.
        assert _store_mode(tmp_path) == "v2"
        # T-2356: migrate_v1_to_v2 deliberately LEAVES the monofiles in
        # place (design section 7's reversibility guarantee) -- silence
        # requires the cutover's own second commit to have actually
        # deleted them, not just v2-mode alone (see the companion test
        # below for the "still there" case, which must NOT be silent).
        ledger_path(tmp_path).unlink()
        archive_path(tmp_path).unlink()
        assert _ledgerv1001_violations(tmp_path) == ()

    def test_v2_mode_repo_with_a_lingering_monofile_errors(
        self, tmp_path: Path
    ) -> None:
        """T-2356: a v2-mode repo that still has tickets.md/tickets-
        archive.md sitting on disk (the cutover's first commit landed --
        migrate_v1_to_v2 ran -- but its second commit, deleting the
        monofiles, never did) must NOT be silently accepted as a
        permanent, indefinite compatibility window. Unconditional ERROR,
        not sunset-gated -- there is no "still migrating" grace period
        for a v2-mode repo that kept a stray monofile around."""
        _git_init(tmp_path)
        _seed_v1_fixture(tmp_path)
        assert migrate_v1_to_v2(tmp_path).is_ok
        assert _store_mode(tmp_path) == "v2"
        # Monofiles deliberately left in place -- this is the incomplete-
        # cutover shape.
        assert ledger_path(tmp_path).exists()
        assert archive_path(tmp_path).exists()

        violations = _ledgerv1001_violations(tmp_path)
        assert len(violations) == 1
        assert violations[0].rule == "LEDGERV1001"
        assert violations[0].severity == Severity.ERROR
        assert "tickets.md" in violations[0].message
        assert "cutover" in violations[0].message

    def test_no_ledger_content_at_all_is_silent(self, tmp_path: Path) -> None:
        """A from-scratch repo with zero ticket content of either shape
        must never fire LEDGERV1001 -- `_store_mode`'s fresh-repo DEFAULT
        ('single') is not the same thing as an actual monofile on disk,
        and plenty of existing gate tests construct exactly this bare
        tmp_path shape and assert `tickets_gate(...) == ()`."""
        assert _ledgerv1001_violations(tmp_path) == ()


_GOLDEN_LEDGER = Path(__file__).parent / "fixtures" / "tickets" / "golden-monofile-ledger.md"
_GOLDEN_ARCHIVE = (
    Path(__file__).parent / "fixtures" / "tickets" / "golden-monofile-archive.md"
)


# frob:waive WIRE001 reason="test-fixture builder for the CHECKED-IN golden fixture \
# files -- no production caller to wire it to by design, same precedent as \
# _seed_v1_fixture" permanent="true"
def _seed_golden_fixture_files(root: Path) -> None:
    """Seed `root` from the CHECKED-IN `tests/fixtures/tickets/golden-
    monofile-ledger.md`/`golden-monofile-archive.md` files (design section
    7.3's own fixture, as opposed to `_seed_v1_fixture`'s programmatically
    constructed equivalent) plus the matching attachment, so the golden
    round-trip test below exercises the actual on-disk fixture text a
    reviewer can read and diff, not just code that happens to produce
    the same shapes."""
    _git_init(root)
    atomic_write(ledger_path(root), _GOLDEN_LEDGER.read_text(encoding="utf-8"))
    atomic_write(archive_path(root), _GOLDEN_ARCHIVE.read_text(encoding="utf-8"))
    dest = attachments_dir(root, "T-0002")
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(_FIXTURE_ATTACHMENT, dest / "mockup.txt")


class TestGoldenFixtureRoundTrip:
    """T-2355: design section 7.3's golden round-trip test, built from the
    CHECKED-IN fixture files rather than an in-code construction -- and,
    per T-2355's own positive-control requirement, a companion test
    proving the equivalence check can actually FAIL on a genuinely
    divergent v2 tree, not just pass on a healthy one."""

    def test_checked_in_fixture_round_trips_to_v2_and_back(
        self, tmp_path: Path
    ) -> None:
        """GIVEN the checked-in golden monofile fixture WHEN migrated to
        v2 THEN the same id set and equal per-ticket field values and
        Done-report text come back out -- the exact assertion design
        section 7.3 specifies, run against the real fixture file."""
        _seed_golden_fixture_files(tmp_path)

        original_active = _parse_ledger(
            ledger_path(tmp_path).read_text(encoding="utf-8")
        ).danger_ok
        original_archived = _parse_ledger(
            archive_path(tmp_path).read_text(encoding="utf-8")
        ).danger_ok
        # The fixture must actually cover every shape design section 7.3
        # names -- a fixture that silently lost a shape would make this
        # whole test class vacuous.
        assert {t.state for t in original_active.values() if t.id == "T-0001"} == {
            TicketState.DONE
        }
        assert original_active["T-0002"].blocked_by == ("T-0001",)
        assert original_active["T-0002"].attachments
        assert original_active["T-draft-abc12345"].id.startswith("T-draft-")
        assert "T-0000" in original_archived

        assert migrate_v1_to_v2(tmp_path).is_ok

        _assert_semantically_equal_round_trip(
            tmp_path, original_active, original_archived
        )

    def test_a_genuinely_divergent_v2_tree_fails_the_equivalence_check(
        self, tmp_path: Path
    ) -> None:
        """MUST-FAIL positive control (T-2355's own non-negotiable
        requirement): a round-trip check that can never fail proves
        nothing. Migrate the golden fixture normally, then hand-corrupt
        the v2 ticket's title AFTER migration (simulating a real
        divergence class this whole ticket exists to catch) and confirm
        `_assert_semantically_equal_round_trip` -- the exact helper the
        test above relies on -- actually raises on it."""
        import pytest

        _seed_golden_fixture_files(tmp_path)
        original_active = _parse_ledger(
            ledger_path(tmp_path).read_text(encoding="utf-8")
        ).danger_ok
        original_archived = _parse_ledger(
            archive_path(tmp_path).read_text(encoding="utf-8")
        ).danger_ok
        assert migrate_v1_to_v2(tmp_path).is_ok

        corrupted_path = v2_ticket_dir(tmp_path, "T-0001") / "ticket.md"
        corrupted_text = corrupted_path.read_text(encoding="utf-8").replace(
            "title: a completed ticket", "title: A DIVERGED TITLE NOBODY WROTE"
        )
        assert corrupted_text != corrupted_path.read_text(encoding="utf-8")
        atomic_write(corrupted_path, corrupted_text)

        with pytest.raises(AssertionError):
            _assert_semantically_equal_round_trip(
                tmp_path, original_active, original_archived
            )


# frob:waive WIRE001 reason="shared assertion helper for this module's two \
# golden-round-trip tests (healthy fixture + must-fail positive control) -- no \
# production caller by design, same precedent as the other test-only builders in this \
# file" permanent="true"
def _assert_semantically_equal_round_trip(
    root: Path,
    original_active: dict[str, Ticket],
    original_archived: dict[str, Ticket],
) -> None:
    """Shared body of the golden round-trip's own equivalence check
    (originally `TestMigrateV1ToV2.test_golden_round_trip_semantic_
    equality`'s inline assertions, extracted so the must-fail positive
    control above can invoke the identical check against a corrupted
    tree). Raises `AssertionError` the moment any ticket's non-body
    fields or Done-report text disagree between the pre-migration parse
    and the post-migration v2 load."""
    from frob.tickets._models import recover_done_report_why
    from frob.tickets._store import read_done_report

    migrated_active = load_all(root).danger_ok
    migrated_archived = load_archive(root).danger_ok

    assert set(migrated_active) == set(original_active)
    assert set(migrated_archived) == set(original_archived)

    for ticket_id, before in {**original_active, **original_archived}.items():
        after = migrated_active.get(ticket_id) or migrated_archived.get(ticket_id)
        assert after is not None
        before_fields = before.model_dump(mode="json", exclude={"body"})
        after_fields = after.model_dump(mode="json", exclude={"body"})
        assert before_fields == after_fields, ticket_id

        before_why = recover_done_report_why(before.body)
        after_report = read_done_report(root, ticket_id)
        if before_why is None:
            assert after_report is None
        else:
            assert after_report is not None
            assert before_why in after_report


class TestMigrateMissingV2:
    """T-2355: `migrate_missing_v2` -- the partial-migration gap
    `migrate_v1_to_v2` leaves open once a repo is already v2-mode
    (already-v2 no-ops the whole migrator, so legacy monofile-only
    tickets from before full cutover never get a v2 file at all)."""

    def test_migrates_only_the_monofile_only_tickets(self, tmp_path: Path) -> None:
        """GIVEN a repo that is ALREADY v2-mode (one ticket already has a
        real `tickets/T-####/ticket.md`) but the monofile ledger still
        lists an ADDITIONAL ticket with no v2 file of its own (the exact
        158-vs-478 shape T-2355 was filed to close) WHEN
        `migrate_missing_v2` runs THEN the missing ticket gets a real v2
        file and the count returned is 1, not 4 (`migrate_v1_to_v2`'s own
        whole-ledger count) -- only the genuinely missing id is written."""
        _git_init(tmp_path)
        _seed_v1_fixture(tmp_path)
        # Cut the repo over to v2-mode the normal way first (T-0001 alone,
        # so the repo already satisfies `_store_mode(root) == "v2"`),
        # exactly like a real repo that migrated a handful of tickets by
        # hand and then stalled.
        already = _done_ticket()
        assert _migrate_one_v2(tmp_path, already, v2_ticket_dir(tmp_path, "T-0001")).is_ok
        assert _store_mode(tmp_path) == "v2"
        assert migrate_v1_to_v2(tmp_path).danger_ok == 0  # confirms the gap this closes

        result = migrate_missing_v2(tmp_path)
        assert result.is_ok
        assert result.danger_ok == 3  # T-0002, T-draft-abc12345, T-0000 (archived)

        assert (v2_ticket_dir(tmp_path, "T-0002") / "ticket.md").is_file()
        assert (v2_ticket_dir(tmp_path, "T-draft-abc12345") / "ticket.md").is_file()
        assert (v2_archive_dir(tmp_path, "T-0000") / "ticket.md").is_file()

    def test_never_overwrites_an_already_migrated_ticket(self, tmp_path: Path) -> None:
        """T-2355's non-negotiable positive control: a ticket whose v2
        state has already DIVERGED from its stale `tickets.md` row (the
        exact 21-ticket shape the parent ticket names) must be left
        completely alone -- the v2 file is current truth, the monofile
        row is a stale snapshot, and this function only ever fills a
        genuinely missing file."""
        _git_init(tmp_path)
        _seed_v1_fixture(tmp_path)
        # T-0001 is 'done' in the monofile; migrate it once, then mutate
        # its v2 state to 'in_progress' -- simulating a ticket that moved
        # on after being individually migrated, exactly like the 21 real
        # divergent tickets T-2355 must not touch.
        already = _done_ticket()
        assert _migrate_one_v2(tmp_path, already, v2_ticket_dir(tmp_path, "T-0001")).is_ok
        diverged = already.model_copy(
            update={"state": TicketState.IN_PROGRESS, "title": "diverged since migration"}
        )
        assert atomic_write(
            v2_ticket_dir(tmp_path, "T-0001") / "ticket.md", _serialize_ticket(diverged)
        ).is_ok

        assert migrate_missing_v2(tmp_path).is_ok

        still = load_all(tmp_path).danger_ok["T-0001"]
        assert still.state == TicketState.IN_PROGRESS
        assert still.title == "diverged since migration"

    def test_idempotent_second_run_is_a_no_op(self, tmp_path: Path) -> None:
        """Running `migrate_missing_v2` again once every id already has a
        v2 file returns 0 -- safe to re-run without re-reading the same
        gap it already closed."""
        _git_init(tmp_path)
        _seed_v1_fixture(tmp_path)
        assert migrate_v1_to_v2(tmp_path).is_ok  # fresh repo: full migrate covers all 4

        second = migrate_missing_v2(tmp_path)
        assert second.is_ok
        assert second.danger_ok == 0

    def test_a_stale_active_row_whose_v2_state_already_moved_to_archive_is_not_duplicated(
        self, tmp_path: Path
    ) -> None:
        """Regression test for a real incident hit while implementing
        T-2355 against this repo's own tickets.md: a monofile row still
        claiming a ticket is 'active' can already have its v2 state under
        `tickets/archive/<id>/` (migrated once, then archived for real,
        with the monofile row never updated or deleted). Checking only
        the row's own claimed side (`v2_ticket_dir`) missed this and
        wrote a genuine duplicate id under `tickets/T-####/` too -- every
        one of the 108 ids this repo's own first migration attempt wrote
        turned out to already be archived in v2, and `frob check`'s
        DuplicateId gate refused the result. This must never write a
        second copy anywhere."""
        _git_init(tmp_path)
        active = _seed_v1_fixture(tmp_path)
        # T-0001 is 'active' per the monofile row, but its real v2 state
        # is already archived (the exact stale-row shape above).
        assert _migrate_one_v2(
            tmp_path, active["T-0001"], v2_archive_dir(tmp_path, "T-0001")
        ).is_ok
        assert _store_mode(tmp_path) == "v2"

        result = migrate_missing_v2(tmp_path)
        assert result.is_ok
        # T-0002, T-draft-abc12345, T-0000 -- T-0001 must NOT be
        # rewritten under tickets/T-0001/ as a duplicate.
        assert result.danger_ok == 3
        assert not (v2_ticket_dir(tmp_path, "T-0001") / "ticket.md").exists()
        assert (v2_archive_dir(tmp_path, "T-0001") / "ticket.md").is_file()
