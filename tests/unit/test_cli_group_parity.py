# frob:ticket T-4520
"""Parity tests for the `frob explore`/`quality`/`design`/`ops` verb groups
(T-4520): walks `_root._build_parser()`'s live tree and asserts every group
leaf is IDENTICAL to its flat twin -- same subverb set, same option
strings -- so a subverb or flag added to a flat verb and forgotten in its
group wrapper is a test failure, not a silent drift the way `design sys`
diverged (measured 2026-09-16: 4 of 9 counted subverbs) before this ticket.
`frob design docs` is the one documented, deliberate exception (it omits
`--search`, docs/design/cli-regrouping.md's bucket split) and is asserted
as a subset rather than an equal set."""

from __future__ import annotations

import argparse

import pytest

from frob._cli_parsers._root import _build_parser


def _subparsers_action(
    parser: argparse.ArgumentParser,
) -> argparse._SubParsersAction:  # noqa: SLF001
    """The single `_SubParsersAction` directly under `parser` (every
    parser in this tree has at most one `add_subparsers()` call) or raise
    if `parser` has none -- a small helper so every test below can walk
    the tree by plain subcommand-name lookups instead of repeating
    argparse's private `_actions` scan."""
    for action in parser._actions:  # noqa: SLF001
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            return action
    raise AssertionError(f"{parser.prog!r} has no subparsers")


def _leaf(parser: argparse.ArgumentParser, *path: str) -> argparse.ArgumentParser:
    """Walk `path` (a chain of subcommand names) from `parser` down to the
    named leaf `ArgumentParser`, failing loudly if any hop is missing."""
    node = parser
    for name in path:
        action = _subparsers_action(node)
        assert name in action.choices, (
            f"{node.prog!r} has no {name!r} subcommand (has: {sorted(action.choices)})"
        )
        node = action.choices[name]
    return node


def _option_strings(parser: argparse.ArgumentParser) -> set[str]:
    """Every `--flag`/`-x` option string declared directly on `parser`
    (not descending into its own subparsers, if any) -- what
    `_root._collect_option_strings` collects recursively, one level."""
    strings: set[str] = set()
    for action in parser._actions:  # noqa: SLF001
        strings.update(action.option_strings)
    return strings


def _subcommand_names(parser: argparse.ArgumentParser) -> set[str]:
    """The set of subcommand names directly under `parser`, or the empty
    set if it has no `add_subparsers()` (a leaf with only flags/
    positionals, e.g. `frob map`)."""
    for action in parser._actions:  # noqa: SLF001
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            return set(action.choices)
    return set()


def _assert_identical_twins(
    group_leaf: argparse.ArgumentParser, flat_leaf: argparse.ArgumentParser
) -> None:
    """The two parsers must have the same option strings and, if either
    nests further subcommands, the same subcommand set -- recursing into
    matching children so a divergence three levels down (e.g. `frob sys
    init` vs `frob design sys init`) is caught too, not just at the top."""
    assert _option_strings(group_leaf) == _option_strings(flat_leaf), (
        f"{group_leaf.prog!r} vs {flat_leaf.prog!r}: option strings differ"
    )
    group_children = _subcommand_names(group_leaf)
    flat_children = _subcommand_names(flat_leaf)
    assert group_children == flat_children, (
        f"{group_leaf.prog!r} vs {flat_leaf.prog!r}: subcommand sets differ "
        f"(group={sorted(group_children)}, flat={sorted(flat_children)})"
    )
    if not group_children:
        return
    group_action = _subparsers_action(group_leaf)
    flat_action = _subparsers_action(flat_leaf)
    for name in group_children:
        _assert_identical_twins(group_action.choices[name], flat_action.choices[name])


# frob:ticket T-4520
# frob:tests tests/unit/test_cli_group_parity.py::TestExploreGroupParity.test_every_explore_leaf_matches_its_flat_twin  # noqa: E501
class TestExploreGroupParity:
    """`frob explore`'s four members (T-1238) against their flat twins."""

    # frob:ticket T-4690
    # T-4690: `map`/`outline`/`xref` keep a DEPRECATED flat twin (sunset
    # 2026-12-01, `App.__call__`'s shim) -- still parity-checked here.
    # `docs-search` does not: its flat mirror was deleted outright (it
    # predated a working `Subcommand` entry and was never dispatchable,
    # confirmed by execution: `'docs-search' is not a valid Subcommand`),
    # so there is nothing left to compare it against -- see
    # `test_docs_search_has_no_flat_twin` below, this test's replacement.
    @pytest.mark.parametrize("name", ["map", "outline", "xref"])
    def test_every_explore_leaf_matches_its_flat_twin(self, name: str) -> None:
        """Each `frob explore <name>` leaf must be option-for-option and
        subcommand-for-subcommand identical to standalone `frob <name>`."""
        parser = _build_parser()
        group_leaf = _leaf(parser, "explore", name)
        flat_leaf = _leaf(parser, name)
        _assert_identical_twins(group_leaf, flat_leaf)

    # frob:ticket T-4690
    def test_docs_search_has_no_flat_twin(self) -> None:
        """T-4690: the flat `frob docs-search` mirror T-4520 added is
        deleted outright (not deprecated -- it was never dispatchable in
        the first place, confirmed by execution before this ticket:
        `'docs-search' is not a valid Subcommand`) -- `frob explore
        docs-search` is the one surviving spelling."""
        parser = _build_parser()
        action = _subparsers_action(parser)
        assert "docs-search" not in action.choices
        _leaf(parser, "explore", "docs-search")  # the surviving spelling still works


# frob:ticket T-4520
# frob:tests tests/unit/test_cli_group_parity.py::TestQualityGroupParity.test_every_quality_leaf_matches_its_flat_twin  # noqa: E501
class TestQualityGroupParity:
    """`frob quality`'s eight members (T-1567) against their flat twins."""

    @pytest.mark.parametrize(
        "name",
        ["check", "test", "dup", "arch", "bind", "cycle", "mutate", "perf"],
    )
    def test_every_quality_leaf_matches_its_flat_twin(self, name: str) -> None:
        """Each `frob quality <name>` leaf must be identical to standalone
        `frob <name>`."""
        parser = _build_parser()
        group_leaf = _leaf(parser, "quality", name)
        flat_leaf = _leaf(parser, name)
        _assert_identical_twins(group_leaf, flat_leaf)


# frob:ticket T-4520
# frob:tests tests/unit/test_cli_group_parity.py::TestDesignGroupParity.test_full_member_matches_its_flat_twin  # noqa: E501
class TestDesignGroupParity:
    """`frob design`'s five members (T-1568) against their flat twins --
    the group this ticket's owner decision names as the measured
    divergence (`sys`: 4 of 9 counted subverbs mirrored)."""

    @pytest.mark.parametrize("name", ["sys", "registry", "graph", "exports"])
    def test_full_member_matches_its_flat_twin(self, name: str) -> None:
        """`sys`/`registry`/`graph`/`exports` carry the same flags/
        subcommands under `design` as standalone -- no `--search`-style
        deliberate subset among these four."""
        parser = _build_parser()
        group_leaf = _leaf(parser, "design", name)
        flat_leaf = _leaf(parser, name)
        _assert_identical_twins(group_leaf, flat_leaf)

    def test_sys_carries_every_flat_subverb(self) -> None:
        """The specific regression this ticket was filed over: `design
        sys` must expose every one of flat `sys`'s subverbs (plan, doc,
        export, audit, trace, threats, capacity, shrink, init), not just
        the first four `_add_design_parser` used to wire."""
        parser = _build_parser()
        design_sys = _leaf(parser, "design", "sys")
        flat_sys = _leaf(parser, "sys")
        assert _subcommand_names(design_sys) == _subcommand_names(flat_sys)
        assert _subcommand_names(flat_sys) == {
            "plan",
            "export",
            "doc",
            "audit",
            "trace",
            "threats",
            "capacity",
            "shrink",
            "init",
        }

    def test_docs_deliberately_omits_search(self) -> None:
        """`frob design docs` is the one documented exception
        (docs/design/cli-regrouping.md): it must have every flag `frob
        docs` has EXCEPT `--search`, which stays exclusive to `frob
        explore docs-search` -- a subset assertion, not an equality one,
        so this test (not a silent parity-test skip) is what records the
        exception."""
        parser = _build_parser()
        design_docs = _leaf(parser, "design", "docs")
        flat_docs = _leaf(parser, "docs")
        design_opts = _option_strings(design_docs)
        flat_opts = _option_strings(flat_docs)
        assert "--search" not in design_opts
        assert "--search" in flat_opts
        assert design_opts == flat_opts - {"--search"}


# frob:ticket T-4520
# frob:tests tests/unit/test_cli_group_parity.py::TestOpsGroupParity.test_every_ops_leaf_matches_its_flat_twin  # noqa: E501
class TestOpsGroupParity:
    """`frob ops`'s ten members (T-1569) against their flat twins."""

    @pytest.mark.parametrize(
        "name",
        [
            "release",
            "natives",
            "doctor",
            "clean",
            "fleet",
            "deploy",
            "scaffold",
            "gitlog",
            "stats",
            "process",
        ],
    )
    def test_every_ops_leaf_matches_its_flat_twin(self, name: str) -> None:
        """Each `frob ops <name>` leaf must be identical to standalone
        `frob <name>`."""
        parser = _build_parser()
        group_leaf = _leaf(parser, "ops", name)
        flat_leaf = _leaf(parser, name)
        _assert_identical_twins(group_leaf, flat_leaf)

    def test_process_reap_has_a_flat_twin(self) -> None:
        """T-4520: `process` used to be the one `ops` member with no
        standalone top-level form -- `frob process reap` must now exist
        so the group-to-flat mapping is total."""
        parser = _build_parser()
        _leaf(parser, "process", "reap")  # raises AssertionError if missing
