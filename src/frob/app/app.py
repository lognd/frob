from __future__ import annotations

import sys
from collections.abc import Callable

from frob.app.config import AppConfig, Subcommand
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:ticket T-1567
# frob:ticket T-1568
# frob:ticket T-1569
# frob:ticket T-1697
_RUNNER_MODULE_NAMES = (
    "ack_runner",
    "arch_runner",
    "check_runner",
    "claude_runner",
    "clean_runner",
    "coverage_runner",
    "cycle_runner",
    "debt_runner",
    "deprecated_runner",
    "deploy_runner",
    "design_runner",
    "doctor_runner",
    "docs_runner",
    "dup_runner",
    "explore_runner",
    "exports_runner",
    "fleet_runner",
    "fmt_runner",
    "pyfmt_runner",
    "gitlog_runner",
    "graph_runner",
    "map_runner",
    "mutate_runner",
    "natives_runner",
    "ops_runner",
    "outline_runner",
    "parse_runner",
    "perf_runner",
    "pool_runner",
    "quality_runner",
    "registry_runner",
    "release_runner",
    "scaffold_runner",
    "serve_runner",
    "stats_runner",
    "status_runner",
    "sys_runner",
    "test_runner",
    "ticket_runner",
    "vet_runner",
    "verify_runner",
    "xref_runner",
)
"""Every `frob.app.*_runner` module name with a uniform `run(AppConfig)`
entry point -- documents the full set `_SUBCOMMAND_RUNNER_NAMES` maps
subcommands onto; not imported as a batch by anything else (T-1216:
`_resolve_runner` imports exactly the one module a live invocation's
subcommand actually needs)."""


# frob:ticket T-1567
# frob:ticket T-1568
# frob:ticket T-1569
# frob:ticket T-1697
_SUBCOMMAND_RUNNER_NAMES: dict[Subcommand, str] = {
    Subcommand.scaffold: "scaffold_runner",
    Subcommand.cycle: "cycle_runner",
    Subcommand.outline: "outline_runner",
    Subcommand.map: "map_runner",
    Subcommand.xref: "xref_runner",
    Subcommand.parse: "parse_runner",
    Subcommand.dup: "dup_runner",
    Subcommand.explore: "explore_runner",
    Subcommand.quality: "quality_runner",
    Subcommand.design: "design_runner",
    Subcommand.ops: "ops_runner",
    Subcommand.arch: "arch_runner",
    Subcommand.docs: "docs_runner",
    Subcommand.exports: "exports_runner",
    Subcommand.fleet: "fleet_runner",
    Subcommand.check: "check_runner",
    Subcommand.gitlog: "gitlog_runner",
    Subcommand.graph: "graph_runner",
    Subcommand.ack: "ack_runner",
    Subcommand.debt: "debt_runner",
    Subcommand.deprecated: "deprecated_runner",
    Subcommand.pool: "pool_runner",
    Subcommand.profile: "profile_runner",
    Subcommand.registry: "registry_runner",
    Subcommand.ticket: "ticket_runner",
    Subcommand.test: "test_runner",
    Subcommand.vet: "vet_runner",
    Subcommand.perf: "perf_runner",
    Subcommand.release: "release_runner",
    Subcommand.stats: "stats_runner",
    Subcommand.serve: "serve_runner",
    Subcommand.mutate: "mutate_runner",
    Subcommand.sys: "sys_runner",
    Subcommand.deploy: "deploy_runner",
    Subcommand.doctor: "doctor_runner",
    Subcommand.clean: "clean_runner",
    Subcommand.fmt: "fmt_runner",
    Subcommand.format: "pyfmt_runner",
    Subcommand.natives: "natives_runner",
    Subcommand.coverage: "coverage_runner",
    Subcommand.verify: "verify_runner",
    Subcommand.status: "status_runner",
    Subcommand.claude: "claude_runner",
}
"""Every subcommand handled by a uniform `*_runner.run(AppConfig)` entry point,
mapped to the runner module name that serves it. `bind` is excluded: it takes
a raw argv rather than an `AppConfig`, so `App.__call__` wires it up
separately."""


# frob:ticket T-1337
# frob:ticket T-1567
# frob:ticket T-1568
# frob:ticket T-1569
# frob:ticket T-1697
# frob:invariant INV-049
# invariant spec: [INV-049](invariants/INV-049.md)
# frob:waive DUP001 reason="deliberately mirrors src/frob/app/__init__.py:: \
# _import_runner_run_module -- both are OPAQUE001 fail-closed workarounds (T-1337's \
# own docstring below) that MUST be a closed if/elif chain of literal imports, one per \
# module domain; T-1567 added one more elif branch (quality_runner) to this domain, \
# pushing an already near-duplicate pre-existing pair a little closer -- extracting a \
# shared helper would reintroduce the computed-module-name string OPAQUE001 this \
# pattern exists to avoid"
def _import_runner_module(name: str):  # noqa: ANN201 -- returns a module object
    """Import exactly the one `frob.app.<name>` runner module named by
    `name` (T-1337), dispatching through a closed if/elif chain of LITERAL
    `import` statements instead of `importlib.import_module`'s runtime
    string computation. `name` is always one of `_RUNNER_MODULE_NAMES`
    (`_resolve_runner`'s only caller looks it up from
    `_SUBCOMMAND_RUNNER_NAMES`, itself a closed dict over that same
    tuple) -- this chain enumerates that exact bounded domain so every
    target module name is statically visible to `frob.vet._capability`'s
    ordinary resolver (a literal `import` is exactly what it already
    walks), instead of the OPAQUE001 fail-closed obligation firing on a
    computed module-name string it cannot see through. Laziness is
    preserved: only the one matching branch executes, so only that one
    module (and its own import graph) is ever imported."""
    if name == "ack_runner":
        import frob.app.ack_runner as module
    elif name == "coverage_runner":
        import frob.app.coverage_runner as module
    elif name == "arch_runner":
        import frob.app.arch_runner as module
    elif name == "check_runner":
        import frob.app.check_runner as module
    elif name == "claude_runner":
        import frob.app.claude_runner as module
    elif name == "clean_runner":
        import frob.app.clean_runner as module
    elif name == "cycle_runner":
        import frob.app.cycle_runner as module
    elif name == "debt_runner":
        import frob.app.debt_runner as module
    elif name == "deprecated_runner":
        import frob.app.deprecated_runner as module
    elif name == "deploy_runner":
        import frob.app.deploy_runner as module
    elif name == "design_runner":
        import frob.app.design_runner as module
    elif name == "doctor_runner":
        import frob.app.doctor_runner as module
    elif name == "docs_runner":
        import frob.app.docs_runner as module
    elif name == "dup_runner":
        import frob.app.dup_runner as module
    elif name == "explore_runner":
        import frob.app.explore_runner as module
    elif name == "exports_runner":
        import frob.app.exports_runner as module
    elif name == "fleet_runner":
        import frob.app.fleet_runner as module
    elif name == "fmt_runner":
        import frob.app.fmt_runner as module
    elif name == "pyfmt_runner":
        import frob.app.pyfmt_runner as module
    elif name == "gitlog_runner":
        import frob.app.gitlog_runner as module
    elif name == "graph_runner":
        import frob.app.graph_runner as module
    elif name == "map_runner":
        import frob.app.map_runner as module
    elif name == "mutate_runner":
        import frob.app.mutate_runner as module
    elif name == "natives_runner":
        import frob.app.natives_runner as module
    elif name == "ops_runner":
        import frob.app.ops_runner as module
    elif name == "outline_runner":
        import frob.app.outline_runner as module
    elif name == "parse_runner":
        import frob.app.parse_runner as module
    elif name == "perf_runner":
        import frob.app.perf_runner as module
    elif name == "pool_runner":
        import frob.app.pool_runner as module
    elif name == "profile_runner":
        import frob.app.profile_runner as module
    elif name == "quality_runner":
        import frob.app.quality_runner as module
    elif name == "registry_runner":
        import frob.app.registry_runner as module
    elif name == "release_runner":
        import frob.app.release_runner as module
    elif name == "scaffold_runner":
        import frob.app.scaffold_runner as module
    elif name == "serve_runner":
        import frob.app.serve_runner as module
    elif name == "stats_runner":
        import frob.app.stats_runner as module
    elif name == "status_runner":
        import frob.app.status_runner as module
    elif name == "sys_runner":
        import frob.app.sys_runner as module
    elif name == "test_runner":
        import frob.app.test_runner as module
    elif name == "ticket_runner":
        import frob.app.ticket_runner as module
    elif name == "vet_runner":
        import frob.app.vet_runner as module
    elif name == "verify_runner":
        import frob.app.verify_runner as module
    elif name == "xref_runner":
        import frob.app.xref_runner as module
    else:  # pragma: no cover -- unreachable: name always comes from the closed domain
        raise AssertionError(
            f"_import_runner_module: unknown runner module name {name!r}"
        )
    return module


# frob:ticket T-1216
# frob:ticket T-1337
# frob:tests tests/unit/test_app_lazy_dispatch.py::TestResolveRunner.test_imports_only_the_requested_subcommands_module  # noqa: E501
def _resolve_runner(subcommand: Subcommand) -> Callable[[AppConfig], None] | None:
    """The single `frob.app.*_runner` module's `run` entry point that
    `subcommand` dispatches to, importing ONLY that one module -- `None` if
    `subcommand` has no uniform runner entry (unknown, or `bind`, which
    `App.__call__` wires up separately since its `run` takes a raw argv, not
    an `AppConfig`).

    T-1216: replaces the old `_dispatch_table()`/`_import_runner_modules()`
    pair, which built a dict keyed by EVERY subcommand by importing EVERY
    runner module (deploy/strata/vet/gates included) on every single
    invocation, regardless of which one subcommand was actually requested --
    the real source of the 632ms eager import chain `frob ticket list` used
    to pay even though it never touches any of those modules.

    T-1337: the module-name resolution itself now goes through
    `_import_runner_module`'s closed if/elif chain of literal imports
    instead of `importlib.import_module`, so this is statically resolvable
    without regressing the lazy-import behavior this docstring already
    pins."""
    name = _SUBCOMMAND_RUNNER_NAMES.get(subcommand)
    if name is None:
        return None
    return getattr(_import_runner_module(name), "run")


# frob:ticket T-4690
_DEPRECATED_SPELLINGS: dict[tuple[Subcommand, str | None], tuple[str, str]] = {
    (Subcommand.quality, None): (
        "quality",
        "the standalone verb directly (e.g. `frob check`)",
    ),
    (Subcommand.design, None): (
        "design",
        "the standalone verb directly (e.g. `frob sys`)",
    ),
    (Subcommand.ops, None): (
        "ops",
        "the standalone verb directly (e.g. `frob release`)",
    ),
    (Subcommand.outline, None): ("outline", "explore outline"),
    (Subcommand.map, None): ("map", "explore map"),
    (Subcommand.xref, None): ("xref", "explore xref"),
    (Subcommand.verify, "status"): ("verify status", "status"),
    (Subcommand.fleet, "status"): ("fleet status", "status"),
    # frob:ticket T-4692
    (Subcommand.dup, None): ("dup", "check --only dup"),
    (Subcommand.arch, None): ("arch", "check --only arch"),
    (Subcommand.cycle, None): ("cycle", "check --only cycle"),
    (Subcommand.exports, None): ("exports", "scaffold exports"),
    # frob:ticket T-4695
    (Subcommand.gitlog, None): ("gitlog", "explore gitlog"),
    (Subcommand.stats, None): ("stats", "explore stats"),
    (Subcommand.debt, None): ("debt", "explore debt"),
    (Subcommand.deprecated, None): ("deprecated", "explore deprecated"),
    (Subcommand.graph, "query"): ("graph query", "explore graph-query"),
    (Subcommand.graph, "why"): ("graph why", "explore graph-why"),
    (Subcommand.graph, "affects"): ("graph affects", "explore graph-affects"),
}
"""T-4690's single deprecation-shim dispatch table: every deleted/renamed
spelling this story's `App.__call__` interception point covers, keyed by
`(subcommand, subverb)` (`subverb=None` matches the whole group, e.g.
`quality` regardless of `quality_command`) and mapping to `(old_name,
new_name)` for `frob._cli_parsers._shims.announce_shim`. `fmt` and
`whereis` are NOT here: each already calls `announce_shim` directly from
its own runner/dispatch (`fmt_runner.run`, `__main__._dispatch_whereis`)
since neither has a same-named surviving sibling this dict-keyed
interception could confuse with a non-deprecated invocation the way
`outline`/`map`/`xref` (mirrored under `explore`) or `verify status`/
`fleet status` (mirrored under top-level `status`) would be."""


# frob:ticket T-4690
def _announce_deprecated_spelling(
    subcommand: Subcommand | None, subverb: str | None, cfg: AppConfig
) -> None:
    """Print T-4690's shared deprecation notice (`announce_shim`) exactly
    once, before dispatch, for any `(subcommand, subverb)` pair
    `_DEPRECATED_SPELLINGS` names -- the single point of interception for
    every deleted verb-GROUP spelling and every deleted flat MIRROR
    spelling this story removes, so the runner underneath (shared with
    the surviving spelling, e.g. `outline_runner.run` serves both `frob
    outline` and `frob explore outline`) never has to know which name it
    was invoked through."""
    if subcommand is None:
        return
    entry = _DEPRECATED_SPELLINGS.get((subcommand, subverb))
    if entry is None:
        entry = _DEPRECATED_SPELLINGS.get((subcommand, None))
    if entry is None:
        return
    old_name, new_name = entry
    from frob._cli_parsers._shims import announce_shim

    announce_shim(
        old_name=old_name,
        new_name=new_name,
        sunset="2026-12-01",
        ticket="T-4690",
        color=cfg.color,
        no_color=cfg.no_color,
    )


# frob:doc docs/modules/app.md#entry-point
# frob:ticket T-1697
# frob:ticket T-1808
# frob:waive AFFECT001 reason="T-1808 added one dict entry / one elif branch / one \
# usage-string token for the new claude subcommand, the same shape of edit several \
# prior tickets already carry this exact waiver for on config.py's own AppConfig class \
# -- docs/modules/app.md is not in T-1808's declared scope and adding it opened the \
# same scope-closure cascade those tickets' own waiver text describes; disclosed \
# deferral, not a convention change"
# frob:ticket T-4689
class App:
    # frob:ticket T-0021
    def __init__(self, cfg: AppConfig) -> None:
        self._cfg = cfg

    # frob:waive ARCH103 reason="T-0977: the CLI dispatch entrypoint's one job IS \
    # orchestration -- resolve subcommand, format the usage error, exit; splitting the \
    # usage message out would add indirection with no cohesion gain, and the per- \
    # subcommand resolution itself already lives in _resolve_runner()"
    def __call__(self) -> None:
        # frob:ticket T-0021
        # frob:ticket T-1216
        # frob:ticket T-1697
        subcommand = self._cfg.subcommand
        handler: Callable[[AppConfig], None] | None
        if subcommand == Subcommand.bind:
            from frob.app import bind_runner

            def handler(_cfg: AppConfig) -> None:
                bind_runner.run([])
        elif subcommand is not None:
            handler = _resolve_runner(subcommand)
        else:
            handler = None
        if handler is None:
            _log.error(
                "usage: frob "
                "<scaffold|explore|parse|bind|"
                "check|graph|ack|pool|ticket|test|vet|"
                "perf|release|serve|mutate|sys|deploy|doctor|clean|fleet|"
                "format|verify|claude>"
                " ..."
            )
            sys.exit(1)
        # frob:ticket T-0178
        # frob:ticket T-4689
        from pathlib import Path

        from frob.app.telemetry import timed_call

        root = Path(".").resolve()
        verb = subcommand.value if subcommand else ""
        # T-4689: every group verb's own sub-dispatch field is named
        # `<verb>_command` on AppConfig (e.g. `ticket_command`,
        # `explore_command`) -- read it back by that convention rather
        # than re-lexing argv, so the recorded subverb can never disagree
        # with what argparse actually resolved. A leaf verb with no such
        # field (e.g. `frob dup`) has nothing to read: `getattr` returns
        # `None`, and `None` is recorded verbatim rather than guessed at.
        subverb = getattr(self._cfg, f"{verb}_command", None) if verb else None
        _log.debug("dispatch: verb=%r subverb=%r", verb, subverb)
        _announce_deprecated_spelling(subcommand, subverb, self._cfg)
        timed_call(
            root,
            subcommand=verb,
            subverb=subverb,
            args_head=" ".join(sys.argv[1:])[:512],
            fn=lambda: handler(self._cfg),
        )
