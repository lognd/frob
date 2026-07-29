"""`frob refactor move`/`frob refactor rename` argparse wiring
(docs/design/refactor-verb.md's "New CLI verb" bullet, docs/commands/
refactor.md).

Exposes `add_refactor_parser`/`run_refactor_command` in the same shape as
every other `_add_*_parser` in `src/frob/_cli_parsers/**` so a sibling
ticket can wire this into `frob.__main__`'s subcommand tree with a single
import + one `_add_refactor_parser(sub)` call -- that wiring itself is
outside T-1197's declared scope (`src/frob/_cli_parsers/**` and
`src/frob/__main__.py` are not in this ticket's `scope` globs), so this
module is the ready-to-wire surface, not yet connected to the live CLI.
See the Done report for the filed follow-up ticket that does the wiring.
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from frob.logging import get_logger
from frob.refactor._models import RefactorKind, SymbolRef
from frob.refactor._transaction import run_refactor

_log = get_logger(__name__)

__all__ = ["add_refactor_parser", "run_refactor_command"]


def _parse_ref(text: str) -> SymbolRef:
    """Parse a `pkg.mod:qualname` CLI argument into a `SymbolRef`."""
    module, _, qualname = text.partition(":")
    if not qualname:
        raise argparse.ArgumentTypeError(f"expected MODULE:QUALNAME, got {text!r}")
    return SymbolRef(module=module, qualname=qualname)


# frob:doc docs/commands/refactor.md#cli
# frob:tests tests/test_refactor.py::TestCli.test_add_refactor_parser_registers_move_and_rename  # noqa: E501
def add_refactor_parser(sub: argparse._SubParsersAction) -> None:
    """Register `frob refactor {move,rename}` on an argparse subparsers
    object, matching every other `_add_*_parser` builder's shape
    (`src/frob/_cli_parsers/**`'s existing convention) so wiring this in
    later is a one-line addition, not a rewrite."""
    p = sub.add_parser("refactor", help="transactional symbol move/rename")
    refactor_sub = p.add_subparsers(dest="refactor_subcommand", required=True)

    for kind in (RefactorKind.MOVE, RefactorKind.RENAME):
        rp = refactor_sub.add_parser(
            kind.value, help=f"{kind.value} a Python symbol, rewriting all references"
        )
        rp.add_argument("source", type=_parse_ref, help="MODULE:QUALNAME")
        rp.add_argument("destination", type=_parse_ref, help="MODULE:QUALNAME")
        rp.add_argument(
            "--alias-conflict",
            choices=("error", "rename-dest"),
            default="error",
            help="policy when the destination name collides at a call site",
        )
        rp.add_argument(
            "--full-repo-collect",
            action="store_true",
            help=(
                "run pytest --collect-only over the whole repo, not just touched files"
            ),
        )
        rp.add_argument(
            "--skip-check-delta",
            action="store_true",
            help=(
                "skip the frob check --delta post-condition (for fast local iteration)"
            ),
        )
        rp.set_defaults(_refactor_kind=kind)


# frob:doc docs/commands/refactor.md#cli
# frob:tests tests/test_refactor.py::TestCli.test_run_refactor_command_reports_refusal_exit_code  # noqa: E501
def run_refactor_command(args: argparse.Namespace) -> int:
    """Execute a parsed `frob refactor move`/`rename` invocation and print
    the disclosed report; returns the process exit code (0 success, 1
    refused/rolled-back)."""
    repo_root = Path.cwd()
    result = run_refactor(
        repo_root,
        kind=args._refactor_kind,
        source=args.source,
        destination=args.destination,
        alias_conflict=args.alias_conflict,
        run_pytest_collect=True,
        run_check_delta=not args.skip_check_delta,
        pytest_scope_touched_only=not args.full_repo_collect,
    )
    if result.is_err:
        print(f"refactor refused: {result.danger_err.value}", file=sys.stderr)
        return 1

    report = result.danger_ok
    print(f"refactor {args._refactor_kind.value}: success={report.success}")
    for alias in report.plan.aliases:
        print(
            f"  alias: {alias.file_path}: {alias.original_name} -> {alias.alias_name}"
        )
    for item in report.plan.unresolved:
        print(f"  unresolved: {item}")
    for outcome in report.verify_outcomes:
        status = "PASS" if outcome.passed else "FAIL"
        print(f"  [{status}] {outcome.name}")
    if report.rolled_back:
        print(f"rolled back to {report.pre_sha}", file=sys.stderr)
        return 1
    return 0
