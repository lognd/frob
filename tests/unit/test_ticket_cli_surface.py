"""CLI-surface tests for T-4521: the `frob ticket` verb-family cleanup.

Covers the four acceptance criteria against the argparse tree and the
dispatch-table handlers directly -- no subprocess, no git repo, no file
I/O -- since the behaviors under test (help visibility, exit codes,
argument parsing) are all reachable at the parser/handler level.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import pytest

from frob._cli_parsers._ticket import _add_ticket_parser
from frob.app.config import AppConfig
from frob.app.ticket_runner import _debt, _deprecated, _migrate_removed

_UNUSED_ROOT = Path(".")
_UNUSED_CFG = AppConfig()


def _subcommand_detail_section(parser: argparse.ArgumentParser) -> str:
    """The per-entry subcommand detail lines of `parser.format_help()`
    (e.g. `    new    create a new ticket`), excluding BOTH the `usage:`
    line's `{a,b,c}` brace group AND the identical brace-group metavar
    argparse repeats as the whole subparsers action's own invocation
    line directly under the `positional arguments:` header -- both
    enumerate every registered choice regardless of hiding, so a
    hidden-from-help assertion must look only at the indented per-entry
    lines below them, where a hidden choice has no line at all (see
    `_suppress_subparser_alias`)."""
    help_text = parser.format_help()
    _usage, _sep, rest = help_text.partition("positional arguments:")
    # the `{a,b,c,...}` metavar itself can line-wrap across several
    # physical lines when the choice list is long (as `frob ticket`'s
    # is) -- skip past its closing brace rather than just one newline.
    _metavar_block, _sep2, entries = rest.partition("}")
    return entries


def _has_subcommand_entry(detail_section: str, name: str) -> bool:
    """Whether `detail_section` (from `_subcommand_detail_section`) has an
    actual per-entry line for subcommand `name` -- anchored to the
    line-start indent so it does not false-positive on the substring
    appearing inside some OTHER flag's help prose (e.g. `-v/--verbose`'s
    help text contains the word "restore")."""
    return re.search(rf"(?m)^\s+{re.escape(name)}\b", detail_section) is not None


def _build_ticket_parser() -> tuple[argparse.ArgumentParser, argparse.ArgumentParser]:
    """Build a standalone `frob ticket ...` parser tree (no other `frob`
    subcommands) and return `(root_parser, ticket_parser)` -- the latter
    is what `--help` renders for `frob ticket --help`."""
    root = argparse.ArgumentParser(prog="frob")
    sub = root.add_subparsers(dest="command")
    _add_ticket_parser(sub)
    ticket_p = sub.choices["ticket"]
    return root, ticket_p


class TestHiddenInternalCallbacks:
    """merge-driver and sweep-async: absent from `--help`, still wired."""

    def test_merge_driver_absent_from_help(self) -> None:
        _root, ticket_p = _build_ticket_parser()
        assert not _has_subcommand_entry(
            _subcommand_detail_section(ticket_p), "merge-driver"
        )

    def test_sweep_async_absent_from_help(self) -> None:
        _root, ticket_p = _build_ticket_parser()
        assert not _has_subcommand_entry(
            _subcommand_detail_section(ticket_p), "sweep-async"
        )

    def test_merge_driver_still_dispatches(self) -> None:
        root, _ticket_p = _build_ticket_parser()
        args = root.parse_args(["ticket", "merge-driver", "BASE", "OURS", "THEIRS"])
        assert args.ticket_command == "merge-driver"
        assert args.ticket_merge_base == "BASE"
        assert args.ticket_merge_ours == "OURS"
        assert args.ticket_merge_theirs == "THEIRS"

    def test_sweep_async_still_dispatches(self) -> None:
        root, _ticket_p = _build_ticket_parser()
        args = root.parse_args(
            ["ticket", "sweep-async", "T-0001", "--commit", "abc123"]
        )
        assert args.ticket_command == "sweep-async"
        assert args.ticket_id == "T-0001"


class TestRemovedVerbsExitTwo:
    """migrate/debt/deprecated: one-line removal notice, exit 2."""

    def test_migrate_removed_notice_names_replacement(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc_info:
            _migrate_removed(_UNUSED_ROOT, _UNUSED_CFG)
        assert exc_info.value.code == 2
        assert "admin reconcile" in caplog.text

    def test_debt_removed_notice_names_replacement(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc_info:
            _debt(_UNUSED_ROOT, _UNUSED_CFG)
        assert exc_info.value.code == 2
        assert "frob debt" in caplog.text

    def test_deprecated_removed_notice_names_replacement(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level("ERROR"), pytest.raises(SystemExit) as exc_info:
            _deprecated(_UNUSED_ROOT, _UNUSED_CFG)
        assert exc_info.value.code == 2
        assert "frob deprecated" in caplog.text


class TestAdminGroup:
    """admin renumber|restore|reconcile: byte-for-byte the old top-level
    verbs, with the old spellings kept as hidden aliases."""

    def test_admin_renumber_matches_hidden_top_level_alias(self) -> None:
        root, _ticket_p = _build_ticket_parser()
        admin_args = root.parse_args(
            ["ticket", "admin", "renumber", "T-0001", "T-0002", "--dry-run"]
        )
        alias_args = root.parse_args(
            ["ticket", "renumber", "T-0001", "T-0002", "--dry-run"]
        )
        assert admin_args.ticket_command == "renumber"
        assert alias_args.ticket_command == "renumber"
        assert admin_args.ticket_old_id == alias_args.ticket_old_id == "T-0001"
        assert admin_args.ticket_new_id == alias_args.ticket_new_id == "T-0002"
        assert admin_args.ticket_dry_run is alias_args.ticket_dry_run is True

    def test_admin_reconcile_matches_hidden_top_level_alias(self) -> None:
        root, _ticket_p = _build_ticket_parser()
        admin_args = root.parse_args(["ticket", "admin", "reconcile", "--apply"])
        alias_args = root.parse_args(["ticket", "reconcile", "--apply"])
        assert admin_args.ticket_command == "reconcile"
        assert alias_args.ticket_command == "reconcile"
        assert admin_args.ticket_reconcile_apply is alias_args.ticket_reconcile_apply
        assert admin_args.ticket_reconcile_apply is True

    def test_admin_restore_matches_hidden_top_level_alias(self) -> None:
        root, _ticket_p = _build_ticket_parser()
        admin_args = root.parse_args(
            ["ticket", "admin", "restore", "T-0001", "--reason", "repair"]
        )
        alias_args = root.parse_args(
            ["ticket", "restore", "T-0001", "--reason", "repair"]
        )
        assert admin_args.ticket_command == "restore"
        assert alias_args.ticket_command == "restore"
        assert admin_args.ticket_id == alias_args.ticket_id == "T-0001"
        assert admin_args.ticket_reason == alias_args.ticket_reason == "repair"

    def test_old_top_level_renumber_restore_reconcile_hidden_from_help(self) -> None:
        _root, ticket_p = _build_ticket_parser()
        detail = _subcommand_detail_section(ticket_p)
        assert not _has_subcommand_entry(detail, "renumber")
        assert not _has_subcommand_entry(detail, "reconcile")
        assert not _has_subcommand_entry(detail, "restore")

    def test_admin_group_lists_renumber_restore_reconcile_in_its_own_help(
        self,
    ) -> None:
        _root, ticket_p = _build_ticket_parser()
        ticket_sub_action = next(
            a for a in ticket_p._actions if isinstance(a, argparse._SubParsersAction)
        )
        admin_p = ticket_sub_action.choices["admin"]
        admin_help = admin_p.format_help()
        assert "renumber" in admin_help
        assert "restore" in admin_help
        assert "reconcile" in admin_help
