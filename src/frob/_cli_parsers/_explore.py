# frob:waive INV006 reason="argparse --help text copied verbatim from _core.py's own \
# xref parser (which already carries the same T-1076/T-0585 INV006 file-level waiver) \
# -- incidental exclusivity-flavored wording in a --help string, not a new normative \
# contract"
# frob:ticket T-1238
"""CLI parser builder for the `frob explore` verb group (T-1238): regroups
the navigation porcelain (`map`/`outline`/`xref`/`docs --search`) under one
intent-named subcommand instead of four top-level entries, per the
`docs/design/cli-regrouping.md` taxonomy. The four members' standalone
top-level forms keep working unchanged (see `outline_runner`/`map_runner`/
`xref_runner`/`docs_runner`'s own T-1238 notes) -- this is a second
entry point onto the same argument dests, not a replacement.
"""

from __future__ import annotations


# frob:ticket T-1238
def _add_explore_parser(sub) -> None:
    """Register the `frob explore` subcommand group and its four
    subcommands (`map`, `outline`, `xref`, `docs-search`), each reusing the
    same `AppConfig` dests as its standalone top-level counterpart so
    `explore_runner.run` can delegate straight into the existing runner
    logic."""
    explore_p = sub.add_parser(
        "explore",
        help="navigation: map/outline/xref/docs-search grouped under one "
        "verb (T-1238)",
    )
    explore_sub = explore_p.add_subparsers(dest="explore_command")

    map_p = explore_sub.add_parser(
        "map", help="show whole-project structural map (symbols + line counts)"
    )
    map_p.add_argument("map_path", metavar="path", nargs="?", default=".")
    map_p.add_argument("--json", dest="map_json", action="store_true")
    map_p.add_argument("--depth", dest="map_depth", type=int, metavar="N")
    map_p.add_argument(
        "--all", dest="map_all", action="store_true", help="include private symbols"
    )

    outline_p = explore_sub.add_parser(
        "outline",
        help="show structural skeleton of a file (classes, functions, line numbers)",
    )
    outline_p.add_argument("outline_file", metavar="file")
    outline_p.add_argument("--json", dest="outline_json", action="store_true")
    outline_p.add_argument(
        "--all", dest="outline_all", action="store_true", help="include private symbols"
    )

    xref_p = explore_sub.add_parser(
        "xref", help="find where a symbol is defined and every file that uses it"
    )
    xref_p.add_argument("xref_symbol", metavar="symbol")
    xref_p.add_argument("xref_path", metavar="path", nargs="?", default=".")
    xref_p.add_argument("--lang", dest="xref_lang", choices=["python", "cpp", "c"])
    xref_p.add_argument("--json", dest="xref_json", action="store_true")
    xref_p.add_argument(
        "--cross-file",
        dest="xref_cross_file",
        action="store_true",
        help="hide same-file usages (show only cross-file references)",
    )

    search_p = explore_sub.add_parser(
        "docs-search", help="full-text search through docs/"
    )
    search_p.add_argument("docs_path", metavar="path")
    search_p.add_argument("docs_search", metavar="query")
    search_p.add_argument("--json", dest="docs_json", action="store_true")
