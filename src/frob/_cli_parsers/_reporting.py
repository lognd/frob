# frob:waive INV006 reason="T-1076 split of __main__.py's original T-0585 waiver: this \
# module's help/docstring text carries incidental exclusivity-flavored wording \
# (argparse help strings, scope-cut prose) inherited verbatim from __main__.py, not a \
# new normative contract -- disposed as the same calibration batch, not claim-by-claim"
# frob:waive REF002 preset="split-fragment"
"""CLI parser builders: reporting/inspection subcommands (gitlog, graph,
ack, debt, deprecated, pool, registry, fleet).

Split out of `frob.__main__` (T-1076) purely to keep that module below the
large-file gate threshold -- no behavior change, same argparse tree.
"""

from __future__ import annotations


def _add_gitlog_range_args(gitlog_p) -> None:
    """Register `frob gitlog`'s commit-range selection flags (since/until/limit)."""
    gitlog_p.add_argument(
        "--since",
        dest="gitlog_since",
        metavar="TAG_OR_DATE",
        help="start from tag (e.g. v1.0.0) or date (e.g. 2024-01-01)",
    )
    gitlog_p.add_argument("--until", dest="gitlog_until", metavar="TAG_OR_DATE")
    gitlog_p.add_argument(
        "--limit",
        "-n",
        dest="gitlog_limit",
        type=int,
        metavar="N",
        help="max number of commits to fetch",
    )


# frob:ticket T-0030
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_gitlog_parser(sub) -> None:
    """Register the `frob gitlog` subcommand and its arguments."""
    # -- gitlog ---------------------------------------------------------------
    gitlog_p = sub.add_parser(
        "gitlog",
        help="summarize git history by type/granularity (conventional commits)",
    )
    gitlog_p.add_argument(
        "gitlog_path",
        metavar="path",
        nargs="?",
        help="git repo root (default: current directory)",
    )
    gitlog_p.add_argument(
        "--level",
        dest="gitlog_granularity",
        choices=["major", "user", "full", "changelog"],
        default="user",
        help="major=breaking only | user=feat+fix | full=all | changelog=release notes",
    )
    _add_gitlog_range_args(gitlog_p)
    gitlog_p.add_argument(
        "--all",
        dest="gitlog_all",
        action="store_true",
        help="include non-conventional commits",
    )
    gitlog_p.add_argument("--json", dest="gitlog_json", action="store_true")


# frob:ticket T-0030
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_graph_parser(sub) -> None:
    """Register the `frob graph` subcommand and its arguments."""
    # -- graph -----------------------------------------------------------------
    graph_p = sub.add_parser(
        "graph", help="obligation graph: build cache, query symbols, explain drift"
    )
    graph_sub = graph_p.add_subparsers(dest="graph_command")
    graph_build_p = graph_sub.add_parser("build", help="(re)build the graph cache")
    graph_build_p.add_argument("graph_path", metavar="path", nargs="?", default=".")
    graph_query_p = graph_sub.add_parser(
        "query", help="resolve a symbol ref and show its edges"
    )
    graph_query_p.add_argument("graph_ref", metavar="ref")
    graph_query_p.add_argument("graph_path", metavar="path", nargs="?", default=".")
    graph_query_p.add_argument("--json", dest="graph_json", action="store_true")
    graph_why_p = graph_sub.add_parser(
        "why", help="explain drift/ack status and remedy for a ref"
    )
    graph_why_p.add_argument("graph_ref", metavar="ref")
    graph_why_p.add_argument("graph_path", metavar="path", nargs="?", default=".")
    graph_why_p.add_argument("--json", dest="graph_json", action="store_true")
    # frob:ticket T-0628
    graph_affects_p = graph_sub.add_parser(
        "affects",
        help="transitive uses-contract dependents + docs/tests a ref's change affects",
    )
    graph_affects_p.add_argument("graph_ref", metavar="ref")
    graph_affects_p.add_argument("graph_path", metavar="path", nargs="?", default=".")
    graph_affects_p.add_argument("--json", dest="graph_json", action="store_true")
    graph_affects_p.add_argument(
        "--max-depth", dest="graph_max_depth", type=int, default=None
    )
    graph_affects_p.add_argument(
        "--max-nodes", dest="graph_max_nodes", type=int, default=None
    )


# frob:ticket T-0030
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_ack_parser(sub) -> None:
    """Register the `frob ack` subcommand and its arguments."""
    # -- ack ---------------------------------------------------------------
    ack_p = sub.add_parser(
        "ack", help="acknowledge current digests for one or more symbol refs"
    )
    ack_p.add_argument("ack_refs", metavar="ref", nargs="+")
    ack_p.add_argument(
        "--facet", dest="ack_facet", choices=["sig", "body", "doc"], default="sig"
    )
    ack_p.add_argument("--path", dest="ack_path", metavar="DIR", default=".")


# frob:ticket T-0412
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_debt_parser(sub) -> None:
    """Register the `frob debt` subcommand: list outstanding `frob:debt` entries."""
    debt_p = sub.add_parser(
        "debt", help="list outstanding frob:debt entries (rule, site, ticket, until)"
    )
    debt_p.add_argument("--path", dest="debt_path", metavar="DIR", default=".")
    debt_p.add_argument("--json", dest="debt_json", action="store_true")


# frob:ticket T-0638
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_deprecated_parser(sub) -> None:
    """Register the `frob deprecated` subcommand: list outstanding
    `frob:deprecated` entries (since/sunset/ticket/status)."""
    deprecated_p = sub.add_parser(
        "deprecated",
        help="list outstanding frob:deprecated entries (symref, since, "
        "sunset, ticket, status)",
    )
    deprecated_p.add_argument(
        "--path", dest="deprecated_path", metavar="DIR", default="."
    )
    deprecated_p.add_argument("--json", dest="deprecated_json", action="store_true")


# frob:ticket T-0569
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_pool_parser(sub) -> None:
    """Register the `frob pool snapshot|clear` subcommand: ratchet-pool
    baseline management over `frob.gates._ratchet` (T-0569)."""
    pool_p = sub.add_parser(
        "pool",
        help="ratchet-pool baseline management (T-0569): warn-rule "
        "findings frozen as a tracked baseline, new findings error",
    )
    pool_sub = pool_p.add_subparsers(dest="pool_command")

    pool_snapshot_p = pool_sub.add_parser(
        "snapshot",
        help="baseline every given --key as warn for RULE; anything else "
        "of that rule reports at error severity",
    )
    pool_snapshot_p.add_argument("pool_rule", metavar="RULE")
    pool_snapshot_p.add_argument(
        "--key",
        dest="pool_keys",
        action="append",
        default=[],
        metavar="KEY",
        help="a finding's stable location key (e.g. path:line), repeatable",
    )
    pool_snapshot_p.add_argument("--path", dest="pool_path", metavar="DIR", default=".")

    pool_clear_p = pool_sub.add_parser(
        "clear",
        help="remove one baselined --key from RULE's pool -- always "
        "requires --reason (the disposition every ratcheted finding "
        "eventually needs)",
    )
    pool_clear_p.add_argument("pool_rule", metavar="RULE")
    pool_clear_p.add_argument("--key", dest="pool_key", required=True, metavar="KEY")
    pool_clear_p.add_argument(
        "--reason", dest="pool_reason", required=True, metavar="TEXT"
    )
    pool_clear_p.add_argument("--path", dest="pool_path", metavar="DIR", default=".")


# frob:ticket T-0407
# frob:ticket T-0429
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_registry_parser(sub) -> None:
    """Register the `frob registry` subcommand and its `audit`/`add` actions."""
    registry_p = sub.add_parser(
        "registry", help="unified design-knowledge registry (T-0407)"
    )
    registry_sub = registry_p.add_subparsers(dest="registry_command")
    registry_audit_p = registry_sub.add_parser(
        "audit",
        help="per-registry-file disposition accounting (handled/deferred/"
        "out-of-scope/unaccounted)",
    )
    registry_audit_p.add_argument("--path", dest="registry_path", metavar="DIR")
    registry_audit_p.add_argument("--json", dest="registry_json", action="store_true")
    # T-0560: auto-file check-coverage.yaml's gate-rule staleness (REG010).
    registry_audit_p.add_argument(
        "--sync-gate-rules",
        dest="registry_sync_gate_rules",
        action="store_true",
        help="append a CHK-GATE-<rule> entry for every live gate rule "
        "check-coverage.yaml is missing one for (T-0560)",
    )

    # T-0429: the exhaustive-researcher's corpus-emit mechanism -- appends
    # one new disposition:pending entry directly into the universe SSOT,
    # never assigning a real disposition itself (T-0428's derived model).
    registry_add_p = registry_sub.add_parser(
        "add",
        help="append a new pending entry to a registry file's universe "
        "corpus (T-0429 exhaustive-research emit path)",
    )
    registry_add_p.add_argument("--file", dest="registry_add_file", required=True)
    registry_add_p.add_argument("--key", dest="registry_add_key", default="entries")
    registry_add_p.add_argument("--id", dest="registry_add_id", required=True)
    registry_add_p.add_argument("--name", dest="registry_add_name", required=True)
    registry_add_p.add_argument(
        "--source-doc", dest="registry_add_source_doc", default=""
    )
    registry_add_p.add_argument("--path", dest="registry_path", metavar="DIR")


# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_fleet_parser(sub) -> None:
    """Register the `frob fleet` subcommand and its `status`/`route` actions
    (T-0573, docs/modules/fleet.md)."""
    fleet_p = sub.add_parser(
        "fleet",
        help="cross-repo status, gate rollup, and ticket routing over a "
        "fleet.toml manifest of sibling repos (T-0573)",
    )
    fleet_sub = fleet_p.add_subparsers(dest="fleet_command")

    status_p = fleet_sub.add_parser(
        "status", help="reddest-first status/gate rollup over every manifest repo"
    )
    status_p.add_argument(
        "--manifest", dest="fleet_manifest", metavar="PATH", default=None
    )
    status_p.add_argument("--json", dest="fleet_json", action="store_true")
    status_p.add_argument(
        "--skip-gates",
        dest="fleet_skip_gates",
        action="store_true",
        help="skip the frob check --json probe; git/ticket status only",
    )

    route_p = fleet_sub.add_parser(
        "route", help="file a ticket directly into a named sibling repo's ledger"
    )
    route_p.add_argument(
        "--manifest", dest="fleet_manifest", metavar="PATH", default=None
    )
    route_p.add_argument("--repo", dest="fleet_repo", required=True)
    route_p.add_argument("--title", dest="fleet_title", required=True)
    route_p.add_argument(
        "--kind",
        dest="fleet_kind",
        default="bug",
        choices=["feature", "bug", "security", "ux", "docs", "invariant", "incident"],
    )
    route_p.add_argument(
        "--priority",
        dest="fleet_priority",
        default="medium",
        choices=["low", "medium", "high", "critical"],
    )
    route_p.add_argument(
        "--scope", dest="fleet_scope", action="append", default=[], metavar="GLOB"
    )
    route_p.add_argument("--body", dest="fleet_body", default="")
