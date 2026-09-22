# frob:ticket T-1238
# frob:ticket T-4690
"""CLI parser builder for the `frob explore` verb group (T-1238): regroups
the navigation porcelain (`map`/`outline`/`xref`/`docs-search`) under one
intent-named subcommand, per `docs/design/cli-regrouping.md`.

T-4690 (CLI-surface reduction, coordinator amendment 2026-09-19): `explore`
is the SURVIVING verb -- its four standalone top-level mirrors (`map`,
`outline`, `xref`, `docs-search`) are the ones being deleted (deprecation
shims, sunset 2026-12-01), not `explore` itself. Previously `_add_explore_
parser` reused the flat parsers' already-built `ArgumentParser` objects
via `_mirror_subparser` (T-4520) so a flag added to a flat twin was
visible through the group automatically. Now that the flat twins are
themselves deprecated (suppressed from `--help`, on a sunset clock), that
object-sharing would also suppress `explore`'s own leaves and route them
through the flat-verb deprecation shim -- exactly backwards, since
`explore` is the survivor. Each leaf now calls the SAME `_populate_*_args`
helper the flat (deprecated) parser calls (`_core._populate_outline_args`/
`_populate_map_args`/`_populate_xref_args`, this module's own
`_populate_docs_search_args`), so the flag list is still declared exactly
once -- just no longer via runtime object reuse. `_mirror_subparser`
itself has no callers left and is deleted (T-4690's own instruction: once
it has no callers, delete it)."""

from __future__ import annotations


# frob:ticket T-1238
# frob:ticket T-4690
def _add_explore_parser(sub) -> None:
    """Register the `frob explore` subcommand group and its four
    subcommands (`map`, `outline`, `xref`, `docs-search`) -- `explore` is
    the surviving spelling (T-4690 coordinator amendment); each leaf
    populates its arguments via the same `_populate_*_args` helper its
    now-deprecated flat twin uses, so the flag list is declared once."""
    from frob._cli_parsers._core import (
        _populate_map_args,
        _populate_outline_args,
        _populate_xref_args,
    )

    explore_p = sub.add_parser(
        "explore",
        help="navigation: map/outline/xref/docs-search grouped under one verb (T-1238)",
    )
    explore_sub = explore_p.add_subparsers(dest="explore_command")

    outline_p = explore_sub.add_parser(
        "outline",
        help="show structural skeleton of a file (classes, functions, line numbers)",
    )
    _populate_outline_args(outline_p)

    map_p = explore_sub.add_parser(
        "map", help="show whole-project structural map (symbols + line counts)"
    )
    _populate_map_args(map_p)

    xref_p = explore_sub.add_parser(
        "xref", help="find where a symbol is defined and every file that uses it"
    )
    _populate_xref_args(xref_p)

    docs_search_p = explore_sub.add_parser(
        "docs-search", help="full-text search through docs/"
    )
    _populate_docs_search_args(docs_search_p)


# frob:ticket T-4520
def _populate_docs_search_args(search_p) -> None:
    """Add `docs-search`'s arguments onto `search_p` (T-4520) -- the
    `frob explore docs-search` group leaf's own argument list. T-4690:
    the standalone flat `frob docs-search` verb this helper used to also
    serve is deleted outright (it predated a working `Subcommand` entry
    and was never dispatchable -- `'docs-search' is not a valid
    Subcommand`, confirmed by execution -- so it carried no shim-worthy
    behavior to preserve)."""
    search_p.add_argument("docs_path", metavar="path")
    search_p.add_argument("docs_search", metavar="query")
    search_p.add_argument("--json", dest="docs_json", action="store_true")
