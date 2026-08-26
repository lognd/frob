from __future__ import annotations

import argparse
import difflib
import re
from pathlib import Path
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
from frob.app import App, AppConfig
from frob.app.config import stale_binary_warning, stale_install_warning
from frob.logging import get_logger

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
def _add_analysis_subparsers(sub) -> None:
    """Register the code-analysis subcommand group: scaffold through bind."""
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


# frob:doc docs/modules/app.md#entry-point
# frob:ticket T-0355
# frob:ticket T-0358
# frob:ticket T-2443
# frob:tests tests/unit/test_main_entry.py::TestMainSigint.test_keyboard_interrupt_prints_clean_message_and_exits_130  # noqa: E501
# frob:tests \
# tests/unit/test_main_entry.py::TestMainSigint.test_normal_dispatch_is_unaffected
# frob:tests tests/unit/test_main_entry.py::TestMainInstallsSigtermReaper.test_main_installs_the_reaper_before_dispatch  # noqa: E501
def main() -> None:
    """CLI entry point: parses argv and dispatches to `App`, or straight to
    `frob bind` (T-0355: SIGINT during a long-running command -- e.g. a
    synchronous pre-work sweep on a slow mount -- used to fall through to a
    bare `KeyboardInterrupt` traceback; that's noise for a deliberate Ctrl-C,
    not a crash, so it is caught here and reported as a clean one-line
    message with the conventional 128+SIGINT exit code instead).

    T-2443: `install_sigterm_reaper` runs FIRST, before any dispatch --
    every real invocation of this CLI is a fresh process, so this is the
    one place that reliably runs once per invocation regardless of which
    subcommand follows. See `frob.process._reap`'s module docstring for the
    leaked-forkserver defect this closes (a `frob check` killed by this
    fleet's routine `timeout 540 ...` wrapper used to leave its process-pool
    workers, and therefore the forkserver helper they keep alive, running
    forever reparented to init)."""
    import sys as _sys

    from frob.process import install_sigterm_reaper

    install_sigterm_reaper()
    try:
        _dispatch(_sys.argv[1:])
    except KeyboardInterrupt:
        print("frob: interrupted", file=_sys.stderr)
        _sys.exit(130)
    except Exception as exc:  # noqa: BLE001 -- top-level CLI boundary must not crash raw
        _log.error("main: unhandled exception during dispatch: %s", exc, exc_info=True)
        print(f"frob: {exc}", file=_sys.stderr)
        _sys.exit(1)


# frob:ticket T-1567
def _is_quality_bind(argv: list[str]) -> bool:
    """`True` for `frob quality bind ...` (T-1567) -- split out of
    `_dispatch` purely to keep that function under the ARCH001 line
    threshold; `bind_runner.run` takes raw argv, so this argv shape is
    dispatched directly rather than through `quality_runner.run`."""
    return bool(argv) and argv[0] == "quality" and len(argv) > 1 and argv[1] == "bind"


# frob:ticket T-2242
def _is_release_publish(argv: list[str]) -> bool:
    """`True` for `frob release publish ...` (T-2242) -- mirrors
    `_is_quality_bind` above; `frob.release._cli.run_release_publish_
    command` takes a parsed `argparse.Namespace` from its OWN dedicated
    parser (same shape as `refactor`'s special case below), not
    `frob.app.release_runner`'s existing `AppConfig`-routed `stamp`/
    `check`/`sync` dispatch -- see `frob.release._cli`'s own module
    docstring for why."""
    return (
        bool(argv) and argv[0] == "release" and len(argv) > 1 and argv[1] == "publish"
    )


# frob:ticket T-0574
def _dispatch_bind(argv: list[str]) -> None:
    """`frob bind ...` (and, via `_dispatch_quality_bind` below, `frob
    quality bind ...`): `bind_runner.run` takes raw argv, not an
    `AppConfig`, so it is dispatched directly rather than through
    `quality_runner.run`. Split out of `_dispatch` (T-2452/ARCH001) so the
    routing table itself stays a pure list of one-line calls."""
    from frob.app.bind_runner import run as _bind_run

    _bind_run(argv)


# frob:ticket T-1567
def _dispatch_quality_bind(argv: list[str]) -> None:
    """`frob quality bind ...` (T-1567) -- mirrors top-level `frob bind`'s
    own dispatch (`_dispatch_bind`) with the leading `quality` token
    stripped before forwarding to the same `bind_runner.run`."""
    _dispatch_bind(argv[1:])


# frob:ticket T-0574
def _dispatch_agent(argv: list[str]) -> None:
    """`frob agent ...` (T-0574) -- dispatched directly, mirroring `frob
    bind` -- see `frob.app.agent_runner`'s module docstring for why."""
    from frob.app.agent_runner import run as _agent_run

    _agent_run(argv)


# frob:ticket T-0836
def _dispatch_worktree(argv: list[str]) -> None:
    """`frob worktree ...` (T-0836) -- dispatched directly, mirroring
    `frob bind`/`agent` -- see `frob.app.worktree_runner`'s module
    docstring for why."""
    from frob.app.worktree_runner import run as _worktree_run

    _worktree_run(argv)


# frob:ticket T-2241
def _dispatch_sync_skills(argv: list[str]) -> None:
    """`frob sync-skills ...` (T-2241) -- dispatched directly, mirroring
    `frob bind`/`agent`/`worktree` -- see
    `frob.scaffold._skills_sync.run`'s own docstring for why."""
    from frob.scaffold._skills_sync import run as _sync_skills_run

    _sync_skills_run(argv)


# frob:ticket T-2242
def _dispatch_release_publish(argv: list[str]) -> None:
    """`frob release publish ...` (T-2242) -- dispatched directly,
    mirroring `_dispatch_refactor` below -- own dedicated parser,
    `argparse.Namespace` in, exit code out. See `frob.release._cli`'s own
    module docstring for why this bypasses `release_runner.py`'s existing
    `stamp`/`check`/`sync` dispatch."""
    import sys as _sys

    from frob.release._cli import (
        add_release_publish_parser,
        run_release_publish_command,
    )

    release_parser = argparse.ArgumentParser(prog="frob")
    release_sub = release_parser.add_subparsers(dest="subcommand")
    add_release_publish_parser(release_sub)
    release_args = release_parser.parse_args(argv)
    _sys.exit(run_release_publish_command(release_args))


# frob:ticket T-1483
# frob:tests \
# tests/unit/test_main_entry.py::TestRefactorDispatch.test_refactor_subcommand_dispatch\
# es_to_run_refactor_command kind="unit"  # noqa: E501
# frob:tests \
# tests/unit/test_main_entry.py::TestRefactorDispatch.test_refactor_exit_code_propagate\
# s kind="unit"  # noqa: E501
def _dispatch_refactor(argv: list[str]) -> None:
    """`frob refactor ...` (T-1483) -- dispatched directly, mirroring
    `frob bind`/`agent`/`worktree` -- `frob.refactor._cli.
    run_refactor_command` takes a parsed `argparse.Namespace` and returns
    an exit code directly (T-1197's own shape, matching every other
    `_add_*_parser` builder for a later single-line wire-in), not the
    uniform `run(AppConfig)` entry point every subcommand in
    `_SUBCOMMAND_RUNNER_NAMES` (`frob.app.app`) shares -- so this
    subcommand is routed the same way as the other direct-dispatch verbs
    rather than added to that dict."""
    import sys as _sys

    from frob.refactor._cli import add_refactor_parser, run_refactor_command

    refactor_parser = argparse.ArgumentParser(prog="frob")
    refactor_sub = refactor_parser.add_subparsers(dest="subcommand")
    add_refactor_parser(refactor_sub)
    refactor_args = refactor_parser.parse_args(argv)
    _sys.exit(run_refactor_command(refactor_args))


# frob:ticket T-2443
def _dispatch_default(argv: list[str]) -> None:
    """Every subcommand NOT special-cased ahead of `_build_parser` in
    `_dispatch`: builds the full argparse tree, parses `argv` against it,
    and routes into `App` via `AppConfig.from_external` -- the normal,
    uniform path every `Subcommand`-mapped runner shares. Split out of
    `_dispatch` (T-2452/ARCH001) so the routing table itself stays a pure
    list of one-line calls."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    pyproject = Path("pyproject.toml")
    _print_startup_warnings(pyproject.parent.resolve())
    if argv and argv[0] == "check":
        _reap_orphaned_forkservers_best_effort()
        # T-2484: `--json` makes stdout the machine-readable payload, so
        # this advisory must land on stderr ONLY in that mode -- see
        # `_report_concurrent_check_advisory_best_effort`'s own docstring
        # for why routing this through the normal INFO/WARNING level
        # split is not enough on its own.
        _report_concurrent_check_advisory_best_effort(
            force_stderr=getattr(args, "check_json", False)
        )
    cfg = AppConfig.from_external(args, pyproject)
    App(cfg)()


# frob:ticket T-0355
# frob:ticket T-1218
# frob:ticket T-1483
# frob:ticket T-1567
# frob:ticket T-1808
# frob:ticket T-2443
# frob:ticket T-2452
def _dispatch(argv: list[str]) -> None:
    """`main`'s actual argv-to-`App` dispatch, split out so `main` can wrap
    only this in the `KeyboardInterrupt` handler (T-0355) without also
    catching interrupts raised by argument parsing itself. T-2452: the
    body itself is now a pure argv-routing table -- each special case's
    real work lives in its own `_dispatch_*` helper (ARCH001)."""
    if argv and argv[0] == "bind":
        _dispatch_bind(argv[1:])
    elif _is_quality_bind(argv):
        _dispatch_quality_bind(argv[1:])
    elif argv and argv[0] == "agent":
        _dispatch_agent(argv[1:])
    elif argv and argv[0] == "worktree":
        _dispatch_worktree(argv[1:])
    elif argv and argv[0] == "sync-skills":
        _dispatch_sync_skills(argv[1:])
    elif _is_release_publish(argv):
        _dispatch_release_publish(argv)
    elif argv and argv[0] == "refactor":
        _dispatch_refactor(argv)
    else:
        _dispatch_default(argv)


# frob:ticket T-2443
def _reap_orphaned_forkservers_best_effort() -> None:
    """`frob check` startup call into `reap_orphaned_forkservers` -- best-
    effort and NEVER fatal to the real command that follows: an exception
    here (an unreadable `/proc` entry the function's own defenses did not
    anticipate, e.g.) is logged and swallowed rather than allowed to crash
    a `frob check` invocation that has nothing to do with this cleanup.
    Split out of `_dispatch` so that function's own body stays the pure
    argv-routing table its docstring claims (ARCH001 precedent, same
    reasoning as `_print_startup_warnings`'s own split)."""
    from frob.process import reap_orphaned_forkservers

    try:
        reap_orphaned_forkservers()
    except Exception as exc:  # noqa: BLE001 -- best-effort cleanup, never fatal
        _log.debug("_reap_orphaned_forkservers_best_effort: %s", exc, exc_info=True)


# frob:ticket T-2473
# frob:ticket T-2484
def _report_concurrent_check_advisory_best_effort(
    *, force_stderr: bool = False
) -> None:
    """`frob check` startup advisory (T-2473): logs how many OTHER `frob
    check` processes are already running on this host, plus available
    memory, so an agent/coordinator watching logs can see fleet-wide
    check pressure without deriving it by hand from `ps` (T-2473's own
    filed measurement: 12 concurrent checks, 7.8GB swap, throughput DOWN
    as agent count went up). ADVISORY ONLY -- never blocks, queues, or
    refuses this check; the coordinator's own chosen direction over an
    enforced concurrency limit (a busy fleet risks becoming a queue of
    stalled agents if the limit is chosen badly). Best-effort and NEVER
    fatal to the real check that follows, same posture as `_reap_
    orphaned_forkservers_best_effort` immediately above -- an unreadable
    `/proc` entry here must never crash a `frob check` invocation that
    has nothing to do with this reporting. Logged at INFO when other
    checks ARE running (the actionable case) so it surfaces in a normal
    log-level run without needing `-v`, WARNING when 4 or more are
    running (this host's own measured degradation point), and skipped
    silently (not even at DEBUG) when the count is 0 -- an idle machine's
    check gets no extra log noise, matching the must-not-stall
    acceptance's spirit even though this function itself never adds
    latency.

    T-2484: `force_stderr=True` (passed by `_dispatch` exactly when
    `--json` was requested) bypasses the logger entirely and `print`s
    straight to `sys.stderr` instead. The INFO/WARNING split above is a
    LOG LEVEL, and `frob.logging.config.toml`'s `below_warning` filter
    routes INFO to the STDOUT handler by default -- under `--json`,
    stdout is the machine-readable `CheckResult` payload, so an INFO-
    level advisory landing ahead of it corrupts every parser that does
    not know to strip a prefix (this was T-2484 itself: `scripts/check_
    summary.py` and the land-path's `_parse_check_json` both broke this
    way). Raising the stdout handler's level for the call (`frob.logging.
    quiet.quiet_stdout_logs`) was the first fix attempted here and is
    WRONG: it also silences the WARNING-vs-INFO threshold check itself
    only for records at/above the raised level, but for an INFO record
    specifically it makes the advisory vanish from BOTH streams --
    stdout because the handler is quieted, stderr because INFO never
    routed there in the first place (`config.toml`'s stderr handler is
    `level = "WARNING"`). A direct `print(..., file=sys.stderr)`, mirroring
    `_print_startup_warnings`'s own established idiom in this same file,
    is the only way to guarantee the message reaches stderr regardless of
    which of the two severities fired -- so the non-`--json` path keeps
    the existing level-based logger call (preserving `caplog`-based
    introspection and the INFO/WARNING split for normal log-watching
    tooling) while `--json` switches to the guaranteed-stderr print."""
    from frob.process._reap import count_running_checks

    try:
        others = count_running_checks()
    except Exception as exc:  # noqa: BLE001 -- best-effort, never fatal
        _log.debug(
            "_report_concurrent_check_advisory_best_effort: %s", exc, exc_info=True
        )
        return
    if not others:
        return
    message = (
        "frob check: %d other check(s) already running on this host -- "
        "see `scripts/fleet_status.py` for swap/load before dispatching "
        "more (T-2473, advisory only -- this check is not deferred)"
    )
    if force_stderr:
        import sys as _sys

        print(message % others, file=_sys.stderr)
        return
    level = _log.warning if others >= 4 else _log.info
    level(message, others)


# frob:ticket T-1808
def _print_startup_warnings(repo_root: Path) -> None:
    """Every loud, best-effort, read-only stderr warning `_dispatch` prints
    ahead of a real subcommand run -- stale global/floor binary skew
    (`stale_install_warning`/`stale_binary_warning`), plus (T-1808) Claude-
    config drift (`frob.app.claude_runner.drift_warning`): detection only,
    surfaced where an operator already looks, never a write. Split out of
    `_dispatch` (ARCH001) so that dispatch function stays the pure argv
    routing table its own docstring claims to be."""
    import sys as _sys

    warning = stale_install_warning(repo_root)
    if warning is not None:
        print(warning, file=_sys.stderr)
    # T-1218: floor check, distinct from the exact-match check above --
    # applies to any repo declaring frob.toml's min_frob_version, not
    # just frob's own checkout.
    floor_warning = stale_binary_warning(repo_root)
    if floor_warning is not None:
        print(floor_warning, file=_sys.stderr)
    # T-1808: surfaced automatically on every invocation, where an
    # operator already looks -- detection only, never a write (the write
    # stays the explicit `frob claude sync` call).
    from frob.app.claude_runner import drift_warning

    claude_warning = drift_warning(repo_root)
    if claude_warning is not None:
        print(claude_warning, file=_sys.stderr)


if __name__ == "__main__":
    main()
