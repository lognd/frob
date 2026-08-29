# frob:ticket T-3059
"""Root argparse parser construction for the `frob` CLI (T-3059 split out of
`frob.__main__`, which re-imports every public name here so existing call
sites -- `from frob.__main__ import _build_parser`, `frob.toml`'s
`parser = "frob.__main__:_build_parser"` entrypoint, `frob.gates._wire`'s
callgraph seed -- keep working unchanged). Owns the did-you-mean suggestion
machinery (T-0578/T-2107), the grouped `--help` formatter (T-1571), and the
subcommand-group registration (`_add_analysis_subparsers`/
`_add_workflow_subparsers`) that fans out to every `frob._cli_parsers`
builder. `frob.__main__` keeps only runtime dispatch (`main`/`_dispatch*`),
which is a different concern from parser construction."""

from __future__ import annotations

import argparse
import difflib
import re
from typing import NoReturn

from frob._cli_parsers import (
    _add_ack_parser,
    _add_agent_parser,
    _add_arch_parser,
    _add_bind_parser,
    _add_check_parser,
    _add_claude_parser,
    _add_clean_parser,
    _add_coverage_parser,
    _add_cycle_parser,
    _add_debt_parser,
    _add_deploy_parser,
    _add_deprecated_parser,
    _add_design_parser,
    _add_docs_parser,
    _add_doctor_parser,
    _add_dup_parser,
    _add_explore_parser,
    _add_exports_parser,
    _add_fleet_parser,
    _add_fmt_parser,
    _add_format_parser,
    _add_gitlog_parser,
    _add_graph_parser,
    _add_map_parser,
    _add_mutate_parser,
    _add_natives_parser,
    _add_ops_parser,
    _add_outline_parser,
    _add_parse_parser,
    _add_perf_parser,
    _add_pool_parser,
    _add_profile_parser,
    _add_quality_parser,
    _add_registry_parser,
    _add_release_parser,
    _add_scaffold_parser,
    _add_serve_parser,
    _add_stats_parser,
    _add_status_parser,
    _add_sync_skills_parser,
    _add_sys_parser,
    _add_test_parser,
    _add_ticket_parser,
    _add_verify_parser,
    _add_vet_parser,
    _add_worktree_parser,
    _add_xref_parser,
)
from frob.logging import get_logger
from frob.narrative._cli import add_narrative_parser
from frob.refactor._cli import add_refactor_parser

_log = get_logger(__name__)

# frob:ticket T-0578
_INVALID_CHOICE_RE = re.compile(
    r"^argument [^:]+: invalid choice: '([^']+)' \(choose from ((?:'[^']*'(?:, )?)+)\)$"
)
# frob:ticket T-0578
_UNRECOGNIZED_RE = re.compile(r"^unrecognized arguments: (.+)$")
# frob:ticket T-0578
# Populated once by `_build_parser` after the whole subcommand tree exists:
# every `--flag` string registered anywhere in the CLI. Used only as the
# LAST-RESORT candidate pool (T-2107) when no more specific subparser could
# be identified as the one actually invoked -- see `_INVOKED_PARSERS` and
# `_option_pool_for` below for the normal, scoped case.
_ALL_OPTION_STRINGS: frozenset[str] = frozenset()

# frob:ticket T-2107
# The chain of `_SuggestingArgumentParser` instances argparse has recursed
# into during the CURRENT `parse_args`/`parse_known_args` call, root first,
# most-specific-subcommand-reached last. argparse's own `parse_args` always
# invokes `self.error(...)` on the ROOT parser for a leftover-arguments
# ("unrecognized arguments: ...") failure -- even when the actual mistake
# was made three levels down (`frob ticket doable --limit`) -- so without
# this, both the suggestion pool and the printed usage block default to the
# root's, not the invoked subcommand's (T-2107's own bug). Reset per
# top-level parse by `_build_parser` so state never leaks between separate
# CLI invocations inside one process (tests build a fresh parser per case).
_INVOKED_PARSERS: list["_SuggestingArgumentParser"] = []


# frob:ticket T-0578
# frob:ticket T-2107
class _SuggestingArgumentParser(argparse.ArgumentParser):
    """`ArgumentParser` subclass that appends a "did you mean" suggestion to
    argparse's own error message for an unknown subcommand/choice or an
    unrecognized flag (T-0578), instead of leaving the operator to grep
    `--help`. The root parser is built as this class and `add_subparsers`
    defaults `parser_class` to `type(self)`, so every nested subparser
    (`frob ticket <cmd>`, `frob perf <cmd>`, ...) inherits the behavior with
    no per-parser wiring. T-2107: both the suggestion candidates and the
    usage block printed on error are scoped to the actually-invoked
    subcommand (`_INVOKED_PARSERS[-1]`), never the whole CLI tree -- a
    flag that exists only on a DIFFERENT subcommand is neither suggested
    nor implied by the shown usage."""

    # frob:ticket T-2107
    # frob:doc docs/commands/cli-vocabulary.md#did-you-mean
    # frob:tests tests/unit/test_main_entry.py::TestDidYouMean.test_unrecognized_flag_suggestion_scoped_to_invoked_subcommand kind="unit"  # noqa: E501
    # frob:tests tests/unit/test_main_entry.py::TestDidYouMean.test_unrecognized_flag_error_shows_invoked_subcommand_usage kind="unit"  # noqa: E501
    def parse_known_args(self, args=None, namespace=None):  # noqa: ANN001,ANN201
        """Records `self` onto `_INVOKED_PARSERS` before delegating (T-2107)
        -- argparse recurses into a chosen subparser's own
        `parse_known_args`, so by the time a leftover-arguments error
        reaches the root's `error()`, this chain's last entry is the most
        specific subcommand parser actually reached."""
        _INVOKED_PARSERS.append(self)
        return super().parse_known_args(args, namespace)

    # frob:doc docs/commands/cli-vocabulary.md#did-you-mean
    # frob:ticket T-0578
    # frob:ticket T-2107
    # frob:tests tests/unit/test_main_entry.py::TestDidYouMean.test_unrecognized_flag_suggestion_scoped_to_invoked_subcommand kind="unit"  # noqa: E501
    # frob:tests tests/unit/test_main_entry.py::TestDidYouMean.test_unrecognized_flag_error_shows_invoked_subcommand_usage kind="unit"  # noqa: E501
    def error(self, message: str) -> NoReturn:
        """Append `(did you mean: X?)` to `message` when a suggestion is
        found, scoped to the actually-invoked subcommand (T-2107), then
        print THAT subcommand's own usage (not necessarily `self`'s, since
        argparse always calls this on the root for a leftover-arguments
        error) and exit nonzero -- never swallows or downgrades the
        original error."""
        import sys as _sys

        target = _INVOKED_PARSERS[-1] if _INVOKED_PARSERS else self
        suggestion = _did_you_mean(message, target)
        if suggestion is not None:
            message = f"{message} (did you mean: {suggestion}?)"
        if target is self:
            super().error(message)
        # T-2107: replicate argparse.ArgumentParser.error's own body, but
        # against `target`'s usage/prog instead of `self`'s (the root) --
        # `error()` always exits, so this mirrors that contract exactly.
        target.print_usage(_sys.stderr)
        self.exit(2, f"{target.prog}: error: {message}\n")


# frob:ticket T-0578
# frob:ticket T-2107
def _did_you_mean(
    message: str, target: argparse.ArgumentParser | None = None
) -> str | None:
    """Best-effort suggestion for two argparse error shapes (T-0578): an
    invalid subcommand/choice (candidates come straight out of argparse's
    own message text) and an unrecognized optional flag (candidates are
    `target`'s own `--flag`s, T-2107 -- falls back to the global
    `_ALL_OPTION_STRINGS` pool only when no `target` is known). `None` if
    neither shape matches or no candidate is close enough
    (`difflib.get_close_matches`' default-ish 0.6 cutoff)."""
    choice_match = _INVALID_CHOICE_RE.match(message)
    if choice_match is not None:
        bad, choices_blob = choice_match.groups()
        choices = re.findall(r"'([^']*)'", choices_blob)
        return _closest(bad, choices)

    unrecognized_match = _UNRECOGNIZED_RE.match(message)
    if unrecognized_match is not None:
        bad_tokens = [
            tok for tok in unrecognized_match.group(1).split() if tok.startswith("-")
        ]
        if not bad_tokens:
            return None
        if target is not None:
            pool = _collect_option_strings(target)
        else:
            pool = _ALL_OPTION_STRINGS
        return _closest(bad_tokens[0], sorted(pool))
    return None


# frob:ticket T-0578
def _closest(bad: str, candidates: list[str]) -> str | None:
    """The single closest candidate to `bad` (`difflib`, cutoff 0.6), or
    `None` if nothing is close enough to be worth suggesting."""
    matches = difflib.get_close_matches(bad, candidates, n=1, cutoff=0.6)
    return matches[0] if matches else None


# frob:ticket T-0578
# frob:invariant terminates reason="_collect_option_strings only recurses into a \
# subparser's own choices, and argparse subparser trees are built once at module load \
# as a finite, non-self-referential tree (a subcommand can never register itself or an \
# ancestor as one of its own subparsers)" measure="depth of the argparse subparser \
# tree strictly decreases with each recursive call"
def _collect_option_strings(parser: argparse.ArgumentParser) -> set[str]:
    """Recursively collect every `--flag` string registered anywhere under
    `parser` (root + every subparser, T-0578) -- argparse exposes no public
    walk API for this, so `_actions`/`_SubParsersAction.choices` (stable
    private attributes used the same way argparse's own `format_help` does)
    are read directly."""
    strings: set[str] = set()
    for action in parser._actions:  # noqa: SLF001
        strings.update(s for s in action.option_strings if s.startswith("--"))
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            for sub in action.choices.values():
                strings.update(_collect_option_strings(sub))
    return strings


# frob:ticket T-0030
# frob:ticket T-0736
# frob:ticket T-0877
def _frob_version() -> str:
    """Resolve the installed `frob` package version from metadata (falls
    back to 'unknown' if run from an environment where the distribution
    is not registered, e.g. a raw source checkout)."""
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("frob")
    except PackageNotFoundError:
        return "unknown"
    except Exception as exc:  # noqa: BLE001 -- best-effort version probe, never fatal
        _log.debug("_frob_version: unresolvable metadata lookup failed: %s", exc)
        return "unknown"


# frob:ticket T-1571
# The small set of intent-named verb groups (explore/quality/design/ops,
# T-1238/T-1567/T-1568/T-1569) plus the pre-existing "already atomic, no
# regrouping needed" verbs docs/design/cli-regrouping.md names alongside
# them (ticket/vet/serve) -- presented FIRST in `frob --help`'s top-level
# listing, ahead of every other still-supported flat command.
_VERB_GROUP_NAMES = frozenset(
    {"explore", "quality", "design", "ops", "ticket", "vet", "serve"}
)


# frob:ticket T-1571
# frob:doc docs/design/cli-regrouping.md#help-surface-rework-t-1571-implemented
# frob:waive AFFECT001 reason="T-3059 code-move split: relocated verbatim out of \
# frob.__main__ (same file the doc's own describes-target already named as \
# _build_parser's home) -- behavior and docstring content are unchanged, so \
# docs/design/cli-regrouping.md's help-surface-rework section is still accurate \
# without an edit; re-verified via frob ack"
# frob:waive COV007 reason="docs/design/cli-regrouping.md's help-surface-rework \
# section (T-1571) is a deliberate architecture doc walking through this exact private \
# formatter's own design, same T-0524/T-0529 per-function architecture-doc precedent \
# every other COV007 waiver in this repo already carries -- not accidental drift onto \
# a private helper"
# frob:tests tests/unit/test_main_entry.py::TestGroupedHelpFormatter.test_verb_groups_listed_before_also_available_directly_section  # noqa: E501
# frob:tests tests/unit/test_main_entry.py::TestGroupedHelpFormatter.test_non_group_verb_listed_after_also_available_directly  # noqa: E501
# frob:tests tests/unit/test_main_entry.py::TestGroupedHelpFormatter.test_nested_subparser_help_is_unaffected  # noqa: E501
# frob:tests tests/unit/test_main_entry.py::TestGroupedHelpFormatter.test_section_headers_indent_strictly_less_than_entries  # noqa: E501
# frob:tests tests/unit/test_main_entry.py::TestGroupedHelpFormatter.test_no_help_text_breaks_inside_a_word  # noqa: E501
# frob:waive WIRE001 follow_up="T-1831" reason="genuinely wired -- passed as \
# formatter_class=_GroupedHelpFormatter to the root argparse parser (_build_parser) \
# and invoked internally by argparse's own help-rendering machinery -- but the \
# best-effort callgraph cannot trace a class passed as a constructor kwarg as a \
# caller, same class of gap as this repo's cross-package DEAD001 waivers (T-1024 \
# precedent) T-1831 carries the T-1856 anchor=True marker: it is a WIRE001 follow_up \
# ANCHOR, not deferred work -- it stays queued/open forever on purpose so WIRE002's \
# follow_up-must-be-open check keeps passing, and it must never be closed."
class _GroupedHelpFormatter(argparse.HelpFormatter):
    """Root `frob --help` formatter (T-1571, acceptance[0] on T-1238):
    presents `_VERB_GROUP_NAMES` first under a "verb groups" heading, then
    every other still-supported top-level command under an "also
    available directly" heading, instead of one flat alphabetical list --
    docs/design/cli-regrouping.md's help-surface-rework section. Only the
    ROOT parser is built with this formatter (see `_build_parser`) --
    `add_parser()`-created nested subparsers (`frob quality --help`, ...)
    do NOT inherit `formatter_class`, so their own `--help` stays the
    ordinary flat argparse listing, unaffected."""

    # frob:ticket T-1571
    # frob:waive WIRE001 follow_up="T-1831" reason="genuinely wired -- invoked \
    # internally by argparse's own help-rendering machinery via \
    # formatter_class=_GroupedHelpFormatter, but the best-effort callgraph cannot \
    # trace a class-constructor-kwarg-then-internal-callback chain, same class of gap \
    # as this repo's cross-package DEAD001 waivers (T-1024 precedent). T-1831 carries \
    # the T-1856 anchor=True marker: it is a WIRE001 follow_up ANCHOR, not deferred \
    # work -- it stays queued/open forever on purpose so WIRE002's \
    # follow_up-must-be-open check keeps passing, and it must never be closed."
    def _format_action(self, action: argparse.Action) -> str:
        """Intercept only the ROOT subparsers pseudo-action; every other
        action (flags, the positional itself) renders exactly as the
        base `HelpFormatter` would."""
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            return self._format_grouped_subparsers(action)
        return super()._format_action(action)

    # frob:ticket T-1571
    # frob:waive WIRE001 follow_up="T-1831" reason="genuinely wired -- called by this \
    # class's own _format_action, itself invoked internally by argparse's \
    # help-rendering machinery via formatter_class=_GroupedHelpFormatter -- the \
    # best-effort callgraph cannot trace that chain, same class of gap as this repo's \
    # cross-package DEAD001 waivers (T-1024 precedent) T-1831 carries the T-1856 \
    # anchor=True marker: it is a WIRE001 follow_up ANCHOR, not deferred work -- it \
    # stays queued/open forever on purpose so WIRE002's follow_up-must-be-open check \
    # keeps passing, and it must never be closed."
    def _format_grouped_subparsers(self, action: argparse._SubParsersAction) -> str:  # noqa: SLF001
        """Render `action`'s choice pseudo-actions in two labeled
        sections instead of argparse's default single flat block."""
        # T-1571: zero-arg `super()` cannot be used inside a generator/
        # comprehension (it loses the compiler-injected `__class__` cell) --
        # bind the bound method once in this frame instead.
        base_format_action = argparse.HelpFormatter._format_action
        subactions = list(action._get_subactions())  # noqa: SLF001
        group_acts = [a for a in subactions if a.dest in _VERB_GROUP_NAMES]
        rest_acts = [a for a in subactions if a.dest not in _VERB_GROUP_NAMES]
        parts: list[str] = []
        # T-2385: emit each section header at the formatter's OWN current
        # indent, then render that section's entries one level DEEPER via
        # _indent()/_dedent() -- a hardcoded two-space header prefix used to
        # match the entry indent exactly, so headers rendered indistinguishable
        # from the commands they label. argparse recomputes the description
        # column from the deeper indent automatically.
        for header, acts in (
            ("verb groups (each also usable standalone):", group_acts),
            ("also available directly:", rest_acts),
        ):
            if not acts:
                continue
            parts.append("%*s%s\n" % (self._current_indent, "", header))
            self._indent()
            parts.extend(base_format_action(self, a) for a in acts)
            self._dedent()
        return "".join(parts)


# frob:ticket T-0578
def _build_parser() -> argparse.ArgumentParser:
    # frob:ticket T-0021
    # frob:ticket T-0231
    # frob:ticket T-2107
    global _ALL_OPTION_STRINGS
    # T-2107: a fresh parser tree means any prior parse's invocation chain
    # is stale -- clear it so an earlier CLI call (or an earlier test's
    # `_build_parser()`) can never leak its target parser into this one.
    _INVOKED_PARSERS.clear()
    p = _SuggestingArgumentParser(
        prog="frob",
        description="Developer workflow tools -- optimized for agentic use",
        # frob:ticket T-1571
        formatter_class=_GroupedHelpFormatter,
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"frob {_frob_version()}",
        help="print the installed frob version and exit",
    )
    # T-0448: global output-layer flags, resolved once per invocation by
    # `frob.render.resolve_color` -- every subcommand inherits these rather
    # than declaring its own copy.
    p.add_argument(
        "--color",
        choices=["auto", "always", "never"],
        default=None,
        help="force/disable ANSI color regardless of TTY detection",
    )
    p.add_argument(
        "--no-color",
        dest="no_color",
        action="store_true",
        help="disable ANSI color (shorthand for --color=never)",
    )
    # T-2979: global verbosity flag -- default output shows the result plus
    # warnings/errors only; -v/--verbose (or FROB_LOG_LEVEL=DEBUG) restores
    # the full gitio/process spawn-trace and cache-hit diagnostic stream.
    # The actual effect is applied by `_apply_verbose_env_override` before
    # `main` dispatches (so it reaches every subcommand, including the
    # direct-dispatch ones below that never build this parser) -- this
    # registration exists so `-v`/`--verbose` shows up in `--help` and so
    # argparse does not reject it as an unrecognized option.
    p.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="show internal diagnostic logging (gitio/process spawn traces, "
        "cache-hit notices) normally kept at DEBUG; same effect as "
        "FROB_VERBOSE=1 (or FROB_LOG_LEVEL=<name> for a specific level)",
    )
    sub = p.add_subparsers(dest="subcommand")
    _add_analysis_subparsers(sub)
    _add_workflow_subparsers(sub)
    # T-0578: populate the did-you-mean candidate pool now that the whole
    # subcommand tree exists -- must run after every `add_parser`/
    # `add_argument` call above, not before.
    _ALL_OPTION_STRINGS = frozenset(_collect_option_strings(p))
    return p


# frob:ticket T-1567
# frob:ticket T-1568
# frob:ticket T-1569
# frob:ticket T-3125
# frob:tests tests/unit/test_main_entry.py::TestHelpListsDirectDispatchVerbs.test_help_lists_refactor_and_narrative  # noqa: E501
def _add_analysis_subparsers(sub) -> None:
    """Register the code-analysis subcommand group: scaffold through bind.

    T-3125: `refactor`/`narrative` are also registered here purely for
    `--help`/discoverability -- `_dispatch` still routes both by a raw
    argv[0] scan BEFORE this tree is ever parsed (see `_dispatch` and
    `_dispatch_refactor`/`_dispatch_narrative`), so this addition is
    additive only and does not change actual execution routing.
    """
    _add_scaffold_parser(sub)
    _add_cycle_parser(sub)
    _add_explore_parser(sub)
    _add_quality_parser(sub)
    _add_design_parser(sub)
    _add_ops_parser(sub)
    _add_outline_parser(sub)
    _add_map_parser(sub)
    _add_xref_parser(sub)
    _add_parse_parser(sub)
    _add_dup_parser(sub)
    _add_arch_parser(sub)
    _add_docs_parser(sub)
    _add_exports_parser(sub)
    _add_bind_parser(sub)
    _add_agent_parser(sub)
    _add_worktree_parser(sub)
    # T-3125: registered here for `--help`/discoverability only, mirroring
    # `agent`/`worktree` above -- `_dispatch` still routes `refactor`/
    # `narrative` by a raw argv[0] scan BEFORE this tree is ever parsed
    # (see `_dispatch`, `_dispatch_refactor`, `_dispatch_narrative`), so
    # this call is additive and does not change actual execution routing.
    add_refactor_parser(sub)
    add_narrative_parser(sub)


# frob:ticket T-0441
# frob:ticket T-1525
# frob:ticket T-1697
# frob:ticket T-1808
# frob:ticket T-2911
def _add_workflow_subparsers(sub) -> None:
    """Register the workflow/CI subcommand group: check through deploy."""
    _add_check_parser(sub)
    _add_gitlog_parser(sub)
    _add_graph_parser(sub)
    _add_ack_parser(sub)
    _add_debt_parser(sub)
    _add_deprecated_parser(sub)
    _add_pool_parser(sub)
    _add_profile_parser(sub)
    _add_registry_parser(sub)
    _add_ticket_parser(sub)
    _add_test_parser(sub)
    _add_vet_parser(sub)
    _add_perf_parser(sub)
    _add_release_parser(sub)
    _add_mutate_parser(sub)
    _add_stats_parser(sub)
    _add_serve_parser(sub)
    _add_sys_parser(sub)
    _add_deploy_parser(sub)
    _add_fleet_parser(sub)
    _add_doctor_parser(sub)
    _add_clean_parser(sub)
    _add_fmt_parser(sub)
    _add_format_parser(sub)
    _add_claude_parser(sub)
    _add_natives_parser(sub)
    _add_coverage_parser(sub)
    _add_status_parser(sub)
    _add_verify_parser(sub)
    _add_sync_skills_parser(sub)
