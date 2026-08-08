# frob:ticket T-1568
"""CLI parser builder for the `frob design` verb group (T-1568): regroups
the design-knowledge porcelain (`sys`/`registry`/`docs`/`graph`/`exports`)
under one intent-named subcommand instead of five top-level entries, per
the `docs/design/cli-regrouping.md` taxonomy and the `frob explore`/`frob
quality` precedent (T-1238/T-1567). Every member's standalone top-level
form keeps working unchanged -- this is a second entry point onto the
same argument dests (reusing each member's own `_populate_*`/`_add_*_sub_
parser` helper so the flag list is declared exactly once), not a
replacement. `frob design docs` omits `--search` (stays exclusive to
`frob explore docs-search`), matching the design doc's own bucket split."""

from __future__ import annotations

import argparse

from frob._cli_parsers._core import (
    _populate_docs_args,
    _populate_exports_args,
)
from frob._cli_parsers._misc import (
    _SYS_EPILOG,
    _add_sys_doc_and_audit_parsers,
    _add_sys_plan_and_export_parsers,
    _add_sys_sync_interface_parser,
)
from frob._cli_parsers._reporting import (
    _populate_graph_actions,
    _populate_registry_actions,
)


# frob:ticket T-1568
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_design_parser(sub) -> None:
    """Register the `frob design` subcommand group and its five
    subcommands (`sys`, `registry`, `docs`, `graph`, `exports`), each
    reusing the same `AppConfig` dests as its standalone top-level
    counterpart so `design_runner.run` can delegate straight into the
    existing runner logic."""
    design_p = sub.add_parser(
        "design",
        help="design-knowledge surfaces: sys/registry/docs/graph/exports "
        "grouped under one verb (T-1568)",
    )
    design_sub = design_p.add_subparsers(dest="design_command")

    sys_p = design_sub.add_parser(
        "sys",
        help="strata design-model applications (plan, doc, export, ...)",
        epilog=_SYS_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sys_sub = sys_p.add_subparsers(dest="sys_command")
    _add_sys_plan_and_export_parsers(sys_sub)
    _add_sys_doc_and_audit_parsers(sys_sub)
    _add_sys_sync_interface_parser(sys_sub)

    registry_p = design_sub.add_parser(
        "registry", help="unified design-knowledge registry (T-0407)"
    )
    registry_sub = registry_p.add_subparsers(dest="registry_command")
    _populate_registry_actions(registry_sub)

    docs_p = design_sub.add_parser(
        "docs",
        help="extract docstrings from a file/symbol (--overview only -- "
        "for full-text search see `frob explore docs-search`)",
    )
    _populate_docs_args(docs_p, include_search=False)

    graph_p = design_sub.add_parser(
        "graph", help="obligation graph: build cache, query symbols, explain drift"
    )
    graph_sub = graph_p.add_subparsers(dest="graph_command")
    _populate_graph_actions(graph_sub)

    exports_p = design_sub.add_parser(
        "exports",
        help="generate __init__.py from public symbols in a package directory",
    )
    _populate_exports_args(exports_p)
