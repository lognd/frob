# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: src/frob/__main__.py's \
# exclusivity-vocabulary hit is source-level design-rationale/scope-cut prose (a \
# docstring or comment describing already-implemented internal behavior, verifiable by \
# reading the code it annotates) rather than a separate cross-module contract needing \
# its own tracked invariant; disposed as a calibration batch, not claim-by-claim"
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
    _add_clean_parser,
    _add_cycle_parser,
    _add_debt_parser,
    _add_deploy_parser,
    _add_deprecated_parser,
    _add_docs_parser,
    _add_doctor_parser,
    _add_dup_parser,
    _add_exports_parser,
    _add_fleet_parser,
    _add_fmt_parser,
    _add_gitlog_parser,
    _add_graph_parser,
    _add_map_parser,
    _add_mutate_parser,
    _add_natives_parser,
    _add_outline_parser,
    _add_parse_parser,
    _add_perf_parser,
    _add_pool_parser,
    _add_registry_parser,
    _add_release_parser,
    _add_scaffold_parser,
    _add_serve_parser,
    _add_stats_parser,
    _add_sys_parser,
    _add_test_parser,
    _add_ticket_parser,
    _add_vet_parser,
    _add_worktree_parser,
    _add_xref_parser,
)
from frob.app import App, AppConfig
from frob.app.config import stale_install_warning
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
# every `--flag` string registered anywhere in the CLI, the candidate pool
# an unrecognized-flag suggestion draws from. Deliberately global rather
# than per-subcommand -- T-0578's own point is one flag name per concept
# across subcommands, so a cross-subcommand suggestion is not a false
# positive, it is the intended behavior.
_ALL_OPTION_STRINGS: frozenset[str] = frozenset()


# frob:ticket T-0578
class _SuggestingArgumentParser(argparse.ArgumentParser):
    """`ArgumentParser` subclass that appends a "did you mean" suggestion to
    argparse's own error message for an unknown subcommand/choice or an
    unrecognized flag (T-0578), instead of leaving the operator to grep
    `--help`. The root parser is built as this class and `add_subparsers`
    defaults `parser_class` to `type(self)`, so every nested subparser
    (`frob ticket <cmd>`, `frob perf <cmd>`, ...) inherits the behavior with
    no per-parser wiring."""

    # frob:doc docs/commands/cli-vocabulary.md#did-you-mean
    # frob:ticket T-0578
    def error(self, message: str) -> NoReturn:
        """Append `(did you mean: X?)` to `message` when a suggestion is
        found, then defer to the base class (which prints and exits
        nonzero) -- never swallows or downgrades the original error."""
        suggestion = _did_you_mean(message)
        if suggestion is not None:
            message = f"{message} (did you mean: {suggestion}?)"
        super().error(message)


# frob:ticket T-0578
def _did_you_mean(message: str) -> str | None:
    """Best-effort suggestion for two argparse error shapes (T-0578): an
    invalid subcommand/choice (candidates come straight out of argparse's
    own message text) and an unrecognized optional flag (candidates are
    `_ALL_OPTION_STRINGS`). `None` if neither shape matches or no candidate
    is close enough (`difflib.get_close_matches`' default-ish 0.6 cutoff)."""
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
        return _closest(bad_tokens[0], sorted(_ALL_OPTION_STRINGS))
    return None


# frob:ticket T-0578
def _closest(bad: str, candidates: list[str]) -> str | None:
    """The single closest candidate to `bad` (`difflib`, cutoff 0.6), or
    `None` if nothing is close enough to be worth suggesting."""
    matches = difflib.get_close_matches(bad, candidates, n=1, cutoff=0.6)
    return matches[0] if matches else None


# frob:ticket T-0578
# frob:invariant terminates reason="_collect_option_strings only recurses into a subparser's own choices, and argparse subparser trees are built once at module load as a finite, non-self-referential tree (a subcommand can never register itself or an ancestor as one of its own subparsers)" measure="depth of the argparse subparser tree strictly decreases with each recursive call"  # noqa: E501
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


# frob:ticket T-0578
def _build_parser() -> argparse.ArgumentParser:
    # frob:ticket T-0021
    # frob:ticket T-0231
    global _ALL_OPTION_STRINGS
    p = _SuggestingArgumentParser(
        prog="frob",
        description="Developer workflow tools -- optimized for agentic use",
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


def _add_analysis_subparsers(sub) -> None:
    """Register the code-analysis subcommand group: scaffold through bind."""
    _add_scaffold_parser(sub)
    _add_cycle_parser(sub)
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
def _add_workflow_subparsers(sub) -> None:
    """Register the workflow/CI subcommand group: check through deploy."""
    _add_check_parser(sub)
    _add_gitlog_parser(sub)
    _add_graph_parser(sub)
    _add_ack_parser(sub)
    _add_debt_parser(sub)
    _add_deprecated_parser(sub)
    _add_pool_parser(sub)
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
    _add_natives_parser(sub)


# frob:doc docs/modules/app.md#entry-point
# frob:ticket T-0355
# frob:ticket T-0358
# frob:tests tests/unit/test_main_entry.py::TestMainSigint.test_keyboard_interrupt_prints_clean_message_and_exits_130  # noqa: E501
# frob:tests tests/unit/test_main_entry.py::TestMainSigint.test_normal_dispatch_is_unaffected  # noqa: E501
def main() -> None:
    """CLI entry point: parses argv and dispatches to `App`, or straight to
    `frob bind` (T-0355: SIGINT during a long-running command -- e.g. a
    synchronous pre-work sweep on a slow mount -- used to fall through to a
    bare `KeyboardInterrupt` traceback; that's noise for a deliberate Ctrl-C,
    not a crash, so it is caught here and reported as a clean one-line
    message with the conventional 128+SIGINT exit code instead)."""
    import sys as _sys

    try:
        _dispatch(_sys.argv[1:])
    except KeyboardInterrupt:
        print("frob: interrupted", file=_sys.stderr)
        _sys.exit(130)
    except Exception as exc:  # noqa: BLE001 -- top-level CLI boundary must not crash raw
        _log.error("main: unhandled exception during dispatch: %s", exc, exc_info=True)
        print(f"frob: {exc}", file=_sys.stderr)
        _sys.exit(1)


# frob:ticket T-0355
def _dispatch(argv: list[str]) -> None:
    """`main`'s actual argv-to-`App` dispatch, split out so `main` can wrap
    only this in the `KeyboardInterrupt` handler (T-0355) without also
    catching interrupts raised by argument parsing itself."""
    import sys as _sys

    if argv and argv[0] == "bind":
        from frob.app.bind_runner import run as _bind_run

        _bind_run(argv[1:])
    elif argv and argv[0] == "agent":
        # T-0574: `frob agent` is dispatched directly, mirroring `bind`
        # above -- see `frob.app.agent_runner`'s module docstring for why.
        from frob.app.agent_runner import run as _agent_run

        _agent_run(argv[1:])
    elif argv and argv[0] == "worktree":
        # T-0836: `frob worktree` is dispatched directly, mirroring
        # `bind`/`agent` above -- see `frob.app.worktree_runner`'s module
        # docstring for why.
        from frob.app.worktree_runner import run as _worktree_run

        _worktree_run(argv[1:])
    else:
        parser = _build_parser()
        args = parser.parse_args(argv)
        pyproject = Path("pyproject.toml")
        warning = stale_install_warning(pyproject.parent.resolve())
        if warning is not None:
            print(warning, file=_sys.stderr)
        cfg = AppConfig.from_external(args, pyproject)
        App(cfg)()


if __name__ == "__main__":
    main()
