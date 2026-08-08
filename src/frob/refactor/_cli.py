"""`frob refactor move`/`frob refactor rename` argparse wiring
(docs/design/refactor-verb.md's "New CLI verb" bullet, docs/commands/
refactor.md).

Exposes `add_refactor_parser`/`run_refactor_command` in the same shape as
every other `_add_*_parser` in `src/frob/_cli_parsers/**` -- T-1197 built
this module as the ready-to-wire surface; T-1483 connected it to the live
CLI. Because `run_refactor_command` takes a parsed `Namespace` and
returns a raw exit code directly rather than the uniform `run(AppConfig)`
shape every `Subcommand`-mapped runner shares, `frob.__main__._dispatch`
routes `frob refactor` the same way it already routes `bind`/`agent`/
`worktree` -- a direct dispatch before the main `argparse` parser tree is
even built, never a `Subcommand` enum member."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from frob.logging import get_logger
from frob.refactor._models import RefactorKind, SymbolRef
from frob.refactor._split import DEFAULT_CHUNK_SIZE, run_split
from frob.refactor._transaction import run_refactor
from frob.render import Renderer

_log = get_logger(__name__)

__all__ = ["add_refactor_parser", "run_refactor_command"]


def _parse_ref(text: str) -> SymbolRef:
    """Parse a `pkg.mod:qualname` CLI argument into a `SymbolRef`."""
    module, _, qualname = text.partition(":")
    if not qualname:
        raise argparse.ArgumentTypeError(f"expected MODULE:QUALNAME, got {text!r}")
    return SymbolRef(module=module, qualname=qualname)


# frob:doc docs/commands/refactor.md#cli
# frob:tests \
# tests/test_refactor.py::TestCli.test_add_refactor_parser_registers_move_and_rename
# frob:tests tests/test_refactor.py::TestCli.test_add_refactor_parser_registers_split
def add_refactor_parser(sub: argparse._SubParsersAction) -> None:
    """Register `frob refactor {move,rename,split}` on an argparse
    subparsers object, matching every other `_add_*_parser` builder's
    shape (`src/frob/_cli_parsers/**`'s existing convention) so wiring this
    in later is a one-line addition, not a rewrite."""
    p = sub.add_parser("refactor", help="transactional symbol move/rename/split")
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

    sp = refactor_sub.add_parser(
        "split",
        help="split N symbols out of one module into a new sibling module",
    )
    sp.add_argument("source", help="source dotted module (pkg.mod)")
    sp.add_argument(
        "--symbols", required=True, help="comma-separated symbol names to move"
    )
    sp.add_argument(
        "--into", dest="destination_module", required=True, help="new dotted module"
    )
    sp.add_argument(
        "--alias-conflict",
        choices=("error", "rename-dest"),
        default="error",
        help="policy when a moved symbol's name collides at a call site",
    )
    sp.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help="max symbols moved per apply-and-verify transaction",
    )
    sp.add_argument(
        "--skip-pytest-collect",
        action="store_true",
        help="skip the pytest --collect-only post-condition (fast local iteration)",
    )
    sp.add_argument(
        "--skip-check-delta",
        action="store_true",
        help=("skip the frob check --delta post-condition (for fast local iteration)"),
    )
    sp.set_defaults(_refactor_kind=None)


def _split_args_to_kwargs(args: argparse.Namespace) -> dict:
    """Translate a parsed `frob refactor split` namespace into `run_split`'s
    keyword arguments -- the comma-split `--symbols` parsing plus the
    skip-flag-to-run-flag inversions, isolated so `_run_split_command`
    stays pure dispatch."""
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    return dict(
        source_module=args.source,
        symbols=symbols,
        destination_module=args.destination_module,
        alias_conflict=args.alias_conflict,
        chunk_size=args.chunk_size,
        run_pytest_collect=not args.skip_pytest_collect,
        run_check_delta=not args.skip_check_delta,
    )


def _render_chunk_report(renderer: Renderer, chunk) -> None:
    """Render one `ChunkReport`'s status line plus its aliases, unresolved
    names, and verify outcomes -- the per-chunk block of `frob refactor
    split`'s report, factored out so `_render_split_report` stays a flat
    loop over chunks."""
    status = "PASS" if chunk.success else "FAIL"
    renderer.line(f"  [{status}] chunk {list(chunk.symbols)}")
    if chunk.error:
        renderer.line(f"    error: {chunk.error}")
    for alias in chunk.aliases:
        renderer.line(
            f"    alias: {alias.file_path}: {alias.original_name} -> {alias.alias_name}"
        )
    for item in chunk.unresolved:
        renderer.line(f"    unresolved: {item}")
    for outcome in chunk.verify_outcomes:
        v_status = "PASS" if outcome.passed else "FAIL"
        skip_note = f" ({len(outcome.skipped)} skipped)" if outcome.skipped else ""
        renderer.line(f"    [{v_status}] {outcome.name}{skip_note}")


def _render_split_report(renderer: Renderer, report) -> None:
    """Print a `SplitReport`'s full disclosed shape: the overall
    source->destination/success summary line, the moved-symbols list (if
    any), then each chunk's own block via `_render_chunk_report`."""
    renderer.line(
        f"refactor split: {report.source_module} -> {report.destination_module}: "
        f"success={report.success}"
    )
    if report.moved_symbols:
        renderer.line(f"  moved: {', '.join(report.moved_symbols)}")
    for chunk in report.chunks:
        _render_chunk_report(renderer, chunk)


def _run_split_command(args: argparse.Namespace) -> int:
    """Execute a parsed `frob refactor split` invocation and print the
    disclosed per-chunk report; returns the process exit code (0 every
    chunk committed, 1 otherwise)."""
    repo_root = Path.cwd()
    result = run_split(repo_root, **_split_args_to_kwargs(args))
    if result.is_err:
        print(f"refactor split refused: {result.danger_err.value}", file=sys.stderr)
        return 1

    report = result.danger_ok
    _render_split_report(Renderer.for_stream(sys.stdout), report)
    return 0 if report.success else 1


# frob:doc docs/commands/refactor.md#cli
# frob:tests \
# tests/test_refactor.py::TestCli.test_run_refactor_command_reports_refusal_exit_code
def run_refactor_command(args: argparse.Namespace) -> int:
    """Execute a parsed `frob refactor move`/`rename`/`split` invocation
    and print the disclosed report; returns the process exit code (0
    success, 1 refused/rolled-back)."""
    if getattr(args, "refactor_subcommand", None) == "split":
        return _run_split_command(args)

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
    renderer = Renderer.for_stream(sys.stdout)
    renderer.line(f"refactor {args._refactor_kind.value}: success={report.success}")
    for alias in report.plan.aliases:
        renderer.line(
            f"  alias: {alias.file_path}: {alias.original_name} -> {alias.alias_name}"
        )
    for item in report.plan.unresolved:
        renderer.line(f"  unresolved: {item}")
    for outcome in report.verify_outcomes:
        status = "PASS" if outcome.passed else "FAIL"
        skip_note = f" ({len(outcome.skipped)} skipped)" if outcome.skipped else ""
        renderer.line(f"  [{status}] {outcome.name}{skip_note}")
    if report.rolled_back:
        print(f"rolled back to {report.pre_sha}", file=sys.stderr)
        return 1
    return 0
