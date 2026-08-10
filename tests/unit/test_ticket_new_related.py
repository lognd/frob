"""T-1995: `frob ticket new` surfaces existing OR archived tickets whose
title closely matches the one being filed, and refuses to create the new
ticket until the caller explicitly acknowledges (`--ack-related`) -- the
measured incident this closes: 7 tickets filed and dropped in one session,
several costing a dispatched agent a full cycle, including T-1986 (a
duplicate of an ALREADY-SHIPPED, ARCHIVED capability that a standing
pre-filing search over open tickets alone could never have caught).

Acceptance criterion 1 (must FAIL before the fix): file a ticket whose
title closely matches an ARCHIVED done ticket and assert the related
ticket is surfaced by id -- `TestRefusesUnacknowledgedRelatedTicket`.
Criterion 2: a genuinely novel ticket files without friction --
`TestNovelTicketFilesWithoutFriction`. Criterion 3: a successor ticket
deliberately similar to its predecessor can still be filed after
acknowledgement -- `TestSuccessorTicketAfterAcknowledgement`."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner._new import _new, related_tickets
from frob.tickets import (
    Origin,
    Priority,
    Ticket,
    TicketKind,
    TicketState,
    load_queue,
)
from frob.tickets._store import write_archived_ticket


def _archive_a_done_ticket(root: Path, ticket_id: str, title: str) -> None:
    """Write `ticket_id` directly into ARCHIVE storage (T-1561's
    `write_archived_ticket`) -- the T-1986 shape: a ticket whose covering
    work is DONE and already moved out of the active ledger, invisible to
    any search that only ever looks at open tickets."""
    ticket = Ticket(
        id=ticket_id,
        title=title,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        priority=Priority.MEDIUM,
        state=TicketState.DONE,
        scope=(),
        body="shipped capability",
    )
    result = write_archived_ticket(root, ticket)
    assert result.is_ok, result.err


class TestRelatedTicketsSearch:
    def test_finds_an_archived_close_title_match(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_new_related.py::TestRelatedTicketsSearch.test_finds_an_archived_close_title_match  # noqa: E501
        _archive_a_done_ticket(
            tmp_path,
            "T-1866",
            "Refuse ticket start when declared scope is over-broad",
        )
        matches = related_tickets(
            tmp_path, "Refuse ticket start when scope is over-broad"
        )
        assert any(m[0] == "T-1866" for m in matches)

    def test_no_match_for_a_genuinely_distinct_title(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_new_related.py::TestRelatedTicketsSearch.test_no_match_for_a_genuinely_distinct_title  # noqa: E501
        _archive_a_done_ticket(
            tmp_path, "T-1866", "Refuse ticket start when declared scope is over-broad"
        )
        matches = related_tickets(tmp_path, "Rewrite the color palette for dark mode")
        assert matches == ()


# frob:ticket T-1995
class TestRefusesUnacknowledgedRelatedTicket:
    """Acceptance criterion 1: must FAIL before the fix existed at all --
    before `_refuse_unacknowledged_related_tickets`, `_new` had no related-
    ticket check, so this would have created the duplicate silently
    instead of raising `SystemExit`."""

    def test_close_match_against_an_archived_ticket_refuses(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_ticket_new_related.py::TestRefusesUnacknowledgedRelatedTicket.test_close_match_against_an_archived_ticket_refuses  # noqa: E501
        _archive_a_done_ticket(
            tmp_path,
            "T-1866",
            "Refuse ticket start when declared scope is over-broad",
        )
        cfg = AppConfig(
            ticket_command="new",
            ticket_title="Refuse ticket start when scope is over-broad",
            ticket_kind="bug",
            ticket_path=tmp_path,
        )
        before = load_queue(tmp_path).danger_ok.tickets.keys()
        with pytest.raises(SystemExit) as exc:
            _new(tmp_path, cfg)
        assert exc.value.code == 1
        loaded = load_queue(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok.tickets.keys() == before

    def test_ack_related_proceeds_despite_the_match(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_new_related.py::TestRefusesUnacknowledgedRelatedTicket.test_ack_related_proceeds_despite_the_match  # noqa: E501
        _archive_a_done_ticket(
            tmp_path,
            "T-1866",
            "Refuse ticket start when declared scope is over-broad",
        )
        before = load_queue(tmp_path).danger_ok.tickets.keys()
        cfg = AppConfig(
            ticket_command="new",
            ticket_title="Refuse ticket start when scope is over-broad",
            ticket_kind="bug",
            ticket_path=tmp_path,
            ticket_ack_related=True,
        )
        _new(tmp_path, cfg)
        loaded = load_queue(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok.tickets.keys() != before


# frob:ticket T-1995
class TestNovelTicketFilesWithoutFriction:
    """Acceptance criterion 2: a genuinely novel title needs no flag at
    all -- the check must never fire on unrelated work."""

    def test_novel_title_needs_no_ack(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_new_related.py::TestNovelTicketFilesWithoutFriction.test_novel_title_needs_no_ack  # noqa: E501
        _archive_a_done_ticket(
            tmp_path,
            "T-1866",
            "Refuse ticket start when declared scope is over-broad",
        )
        before = load_queue(tmp_path).danger_ok.tickets.keys()
        cfg = AppConfig(
            ticket_command="new",
            ticket_title="Rewrite the color palette for dark mode",
            ticket_kind="feature",
            ticket_path=tmp_path,
        )
        _new(tmp_path, cfg)  # must not raise
        loaded = load_queue(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok.tickets.keys() != before


# frob:ticket T-1995
class TestSuccessorTicketAfterAcknowledgement:
    """Acceptance criterion 3: a successor ticket deliberately similar to
    its predecessor (a legitimate, common shape this repo's own history
    names -- per-node burn-downs, sweep-filed regressions) can still be
    filed, once acknowledged."""

    def test_successor_of_an_open_ticket_files_after_ack(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_new_related.py::TestSuccessorTicketAfterAcknowledgement.test_successor_of_an_open_ticket_files_after_ack  # noqa: E501
        first = AppConfig(
            ticket_command="new",
            ticket_title="Burn down TEST005 in src/frob/gates",
            ticket_kind="bug",
            ticket_path=tmp_path,
        )
        _new(tmp_path, first)

        successor = AppConfig(
            ticket_command="new",
            ticket_title="Burn down TEST005 in src/frob/tickets",
            ticket_kind="bug",
            ticket_path=tmp_path,
            ticket_ack_related=True,
        )
        _new(tmp_path, successor)

        loaded = load_queue(tmp_path)
        assert loaded.is_ok
        assert {"T-0001", "T-0002"} <= set(loaded.danger_ok.tickets)


# frob:ticket T-1995
class TestPossibleEnforcementSymbolsCue:
    """The second, additive class: a body claiming a missing enforcement
    surfaces candidate `_refuse_*`/`_check_*` symbols, but ONLY when the
    body actually makes that claim -- an unrelated ticket never triggers
    the grep."""

    def test_missing_enforcement_cue_surfaces_a_real_symbol(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_ticket_new_related.py::TestPossibleEnforcementSymbolsCue.test_missing_enforcement_cue_surfaces_a_real_symbol  # noqa: E501
        # The exact T-1986 shape (quoted in T-1995's own body):
        # "nothing refuses an over-broad scope at start" -- when
        # `_refuse_over_broad_scope_on_start` already existed.
        from frob.app.ticket_runner._new import _possible_enforcement_symbols

        repo_root = Path(__file__).resolve().parents[2]
        symbols = _possible_enforcement_symbols(
            repo_root,
            "nothing refuses an over-broad scope at start",
            "nothing refuses an over-broad declared scope when a ticket starts",
        )
        assert any("_refuse_over_broad_scope_on_start" in sym for sym in symbols)

    def test_no_cue_means_no_grep(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_new_related.py::TestPossibleEnforcementSymbolsCue.test_no_cue_means_no_grep  # noqa: E501
        from frob.app.ticket_runner._new import _possible_enforcement_symbols

        repo_root = Path(__file__).resolve().parents[2]
        symbols = _possible_enforcement_symbols(
            repo_root, "add a new dashboard widget", "purely additive UI work"
        )
        assert symbols == ()


# frob:ticket T-1995
class TestAckRelatedFlagReachesConfigThroughRealParsing:
    """T-1995 follow-up (TEST001 fix's own discovery): every other test in
    this file builds `AppConfig(ticket_ack_related=True, ...)` directly,
    which never exercises the real CLI path -- `AppConfig.from_args` goes
    through `from_external`'s `_build_external_config_kwargs`, which only
    copies fields listed in a STATIC allowlist
    (`frob.app._config_external`'s `_EXTERNAL_CONFIG_FIELDS`-shaped list).
    `--ack-related` parsed into `argparse.Namespace` correctly but was
    silently DROPPED at that allowlist boundary, so the real CLI command
    `frob ticket new --ack-related` never actually acknowledged anything --
    invisible to every test that constructs `AppConfig` by hand. This test
    goes through the real argparse parser + `AppConfig.from_args`, the
    only path that would have caught it."""

    def test_ack_related_flag_survives_real_arg_parsing(self) -> None:
        # frob:tests tests/unit/test_ticket_new_related.py::TestAckRelatedFlagReachesConfigThroughRealParsing.test_ack_related_flag_survives_real_arg_parsing  # noqa: E501
        from frob.__main__ import _build_parser

        parser = _build_parser()
        ns = parser.parse_args(
            ["ticket", "new", "--title", "x", "--kind", "bug", "--ack-related"]
        )
        assert ns.ticket_ack_related is True
        cfg = AppConfig.from_args(ns)
        assert cfg.ticket_ack_related is True

    def test_omitted_flag_defaults_false_through_real_parsing(self) -> None:
        # frob:tests tests/unit/test_ticket_new_related.py::TestAckRelatedFlagReachesConfigThroughRealParsing.test_omitted_flag_defaults_false_through_real_parsing  # noqa: E501
        from frob.__main__ import _build_parser

        parser = _build_parser()
        ns = parser.parse_args(["ticket", "new", "--title", "x", "--kind", "bug"])
        cfg = AppConfig.from_args(ns)
        assert cfg.ticket_ack_related is False
