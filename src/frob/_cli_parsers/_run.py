"""CLI parser builders for `frob run`/`frob build` (T-4759).

Registered here for `--help`/discoverability -- `frob.app.run_runner.run`/
`run_build` own their real parsing and are dispatched directly (mirroring
`bind`/`agent`/`worktree`, see `frob.app.run_runner`'s module docstring),
so these builders exist purely so the flags show up in `--help`.

Not yet wired into `frob._cli_parsers._root._build_parser`'s subcommand
tree: that file is leased by T-4546 at the time this ticket landed, so
`frob run`/`frob build` do not appear in top-level `--help` yet even
though dispatch (`frob.__main__._dispatch`) already routes them -- T-4811
tracks wiring `_add_run_parser`/`_add_build_parser` into
`_add_analysis_subparsers` once that lease clears.
"""

# frob:ticket T-5134
from __future__ import annotations


# frob:ticket T-4759
# frob:debt DEAD001 reason="not invoked from _root's registration tree until T-4811 \
# wires it into _add_analysis_subparsers (that file is leased by a different, \
# in-progress ticket) -- frob run is fully functional without it, dispatched directly \
# via frob.__main__._dispatch (same as bind/agent/worktree's own --help-only \
# registration)" ticket="T-4811"
def _add_run_parser(sub) -> None:
    """Register the `frob run <name> [--dry-run]` subcommand for `--help`
    discovery only -- actual dispatch bypasses this parser entirely (see
    `frob.__main__._dispatch` and `frob.app.run_runner`'s module
    docstring)."""
    run_p = sub.add_parser("run", help="execute one [commands] entry by name")
    run_p.add_argument("name", help="a [commands] entry name, or a native default")
    run_p.add_argument(
        "--dry-run",
        action="store_true",
        help="print the resolved sequence without running anything",
    )


# frob:ticket T-4759
# frob:debt DEAD001 reason="not invoked from _root's registration tree until T-4811 \
# wires it into _add_analysis_subparsers (that file is leased by a different, \
# in-progress ticket) -- frob build is fully functional without it, dispatched \
# directly via frob.__main__._dispatch (same as bind/agent/worktree's own --help-only \
# registration)" ticket="T-4811"
def _add_build_parser(sub) -> None:
    """Register the `frob build [--dry-run]` subcommand for `--help`
    discovery only -- actual dispatch bypasses this parser entirely (see
    `frob.__main__._dispatch` and `frob.app.run_runner`'s module
    docstring)."""
    build_p = sub.add_parser("build", help="delegate to the [commands] 'build' entry")
    build_p.add_argument(
        "--dry-run",
        action="store_true",
        help="print the resolved sequence without running anything",
    )
