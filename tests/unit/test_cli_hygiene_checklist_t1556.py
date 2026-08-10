"""T-1556 (cli-hygiene Principle 1, docs/design/cli-hygiene.md): a
checklist regression lock for the concrete `frob ticket renumber`
positional-contract incident the doc documents -- its zero-args
whole-ledger fallback must be named in `--help`, not just described in a
design doc nobody reads at the command line."""

from __future__ import annotations

from frob.__main__ import _build_parser


def _renumber_subparser():
    """The real, registered `frob ticket renumber` subparser -- exercised
    through the actual `_build_parser()` tree, not a re-implementation, so
    this test fails the moment the real CLI surface drifts from the
    checklist it locks.

    `argparse._SubParsersAction.choices` and `ArgumentParser.
    _subparsers`/`_group_actions` are all typed loosely (`dict | None`,
    `_ArgumentGroup | None`) at the stub level even though they are always
    populated once `add_subparsers()`/`add_parser()` have actually run --
    `assert ... is not None` narrows for `ty` without changing runtime
    behavior (T-1556)."""
    root = _build_parser()
    assert root._subparsers is not None
    ticket_action = next(
        action
        for action in root._subparsers._group_actions
        if action.choices is not None and "ticket" in action.choices
    )
    assert ticket_action.choices is not None
    ticket_parser = dict(ticket_action.choices)["ticket"]
    assert ticket_parser._subparsers is not None
    renumber_action = next(
        action
        for action in ticket_parser._subparsers._group_actions
        if action.choices is not None and "renumber" in action.choices
    )
    assert renumber_action.choices is not None
    return renumber_action.choices["renumber"]


class TestRenumberPositionalContractDocumented:
    def test_old_positional_help_names_the_whole_ledger_fallback(self) -> None:
        renumber_p = _renumber_subparser()
        old_action = next(
            a for a in renumber_p._actions if a.dest == "ticket_old_id"
        )
        assert old_action.help, (
            "frob ticket renumber's <old> positional has no --help text "
            "at all -- the zero-args whole-ledger fallback (T-1556's "
            "cli-hygiene Principle 1) is invisible at the command line"
        )
        assert "T-0001" in old_action.help or "whole-ledger" in old_action.help, (
            "frob ticket renumber's <old> positional --help text no "
            "longer names the destructive whole-ledger fallback -- "
            "re-add the warning docs/design/cli-hygiene.md's Principle 1 "
            "requires"
        )

    def test_dry_run_help_states_its_default(self) -> None:
        renumber_p = _renumber_subparser()
        dry_run_action = next(
            a for a in renumber_p._actions if a.dest == "ticket_dry_run"
        )
        assert dry_run_action.help and "default" in dry_run_action.help.lower()
