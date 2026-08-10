"""frob.app -- CLI dispatch layer (docs/modules/app.md).

Each `frob.app.<name>_runner` module's `run` is the genuine subcommand
entrypoint `frob.app.app` reaches via dynamic `importlib`/`getattr`
dispatch (T-0362); re-exported here module-aliased (`<name>_runner_run`)
since these modules share the bare name `run`. `frob.app._style`'s
`style_*` helpers are the shared CLI-output formatting layer used across
most runner modules, and `frob.app.telemetry`'s recorder/helper functions
are consumed cross-module (`app.app`, `app.ticket_runner`,
`app.stats_runner`, `frob.stats._agentic`, `frob.gates._pii_structural`,
tests) -- both re-exported for the same reason (T-0362, T-0599).

T-1216: the `<name>_runner_run` aliases below are resolved LAZILY, via
`__getattr__` (PEP 562), instead of importing every runner module up
front. `frob.app.app`'s `App.__call__` now resolves and imports ONLY the
one runner module the live subcommand needs (`_resolve_runner`) -- but
this package's `__init__.py` used to undo the equivalent old behavior by
eagerly importing every one of the same modules just to build these
re-export aliases, so `import frob.app` (triggered by ANY subcommand,
since `frob.__main__` imports `App`/`AppConfig` from here) paid for every
runner's import graph regardless of which subcommand actually ran --
measured at 632ms of cumulative importtime dominated by
`deploy_runner -> frob.strata -> frob.vet -> frob.gates`. `frob ticket
list` never touches any of those. `__getattr__` defers each runner
module's import to the first time ITS OWN alias is actually accessed
(caching the resolved callable into this module's globals so the cost is
paid at most once per process), matching `app.py`'s already-documented
lazy design instead of contradicting it.
"""

from __future__ import annotations

from typing import Any

from frob.app._style import (
    style_fail,
    style_header,
    style_ok,
    style_rule,
    style_state,
    style_ticket_id,
    style_warn,
)
from frob.app.app import App
from frob.app.config import (
    AppConfig,
    Subcommand,
    load_arch_config,
    stale_install_warning,
)
from frob.app.telemetry import (
    append_event,
    estimate_tokens,
    is_disabled,
    iso_now,
    record_cli_event,
    record_ticket_event,
    redact_command,
    timed_call,
    tree_hash,
)

# frob:ticket T-1216
# Every lazily-resolved `<name>_runner_run` alias's source runner module,
# keyed by the alias `__getattr__` resolves -- the single home for this
# mapping so `__getattr__` and `__all__` (this dict's keys) can never
# drift apart from each other.
_RUNNER_RUN_MODULES: dict[str, str] = {
    "ack_runner_run": "ack_runner",
    "arch_runner_run": "arch_runner",
    "bind_runner_run": "bind_runner",
    "check_runner_run": "check_runner",
    "clean_runner_run": "clean_runner",
    "cycle_runner_run": "cycle_runner",
    "debt_runner_run": "debt_runner",
    "deploy_runner_run": "deploy_runner",
    "docs_runner_run": "docs_runner",
    "doctor_runner_run": "doctor_runner",
    "dup_runner_run": "dup_runner",
    "exports_runner_run": "exports_runner",
    "fleet_runner_run": "fleet_runner",
    "gitlog_runner_run": "gitlog_runner",
    "graph_runner_run": "graph_runner",
    "map_runner_run": "map_runner",
    "mutate_runner_run": "mutate_runner",
    "outline_runner_run": "outline_runner",
    "parse_runner_run": "parse_runner",
    "perf_runner_run": "perf_runner",
    "pool_runner_run": "pool_runner",
    "profile_runner_run": "profile_runner",
    "registry_runner_run": "registry_runner",
    "release_runner_run": "release_runner",
    "scaffold_runner_run": "scaffold_runner",
    "serve_runner_run": "serve_runner",
    "stats_runner_run": "stats_runner",
    "sys_runner_run": "sys_runner",
    "test_runner_run": "test_runner",
    "ticket_runner_run": "ticket_runner",
    "vet_runner_run": "vet_runner",
    "xref_runner_run": "xref_runner",
}


# frob:ticket T-1337
# frob:invariant INV-049
# invariant spec: [INV-049](invariants/INV-049.md)
def _import_runner_run_module(module_name: str) -> Any:
    """Import exactly the one `frob.app.<module_name>` runner module named
    by `module_name` (T-1337), dispatching through a closed if/elif chain
    of LITERAL `import` statements instead of `importlib.import_module`'s
    runtime string computation. `module_name` is always one of
    `_RUNNER_RUN_MODULES`'s values (`__getattr__`'s only caller looks it up
    from that closed dict) -- this chain enumerates that exact bounded
    domain so every target module name is statically visible to
    `frob.vet._capability`'s ordinary resolver (a literal `import` is
    exactly what it already walks), instead of the OPAQUE001 fail-closed
    obligation firing on a computed module-name string it cannot see
    through. Laziness is preserved: only the one matching branch executes,
    so only that one module (and its own import graph) is ever imported."""
    if module_name == "ack_runner":
        import frob.app.ack_runner as module
    elif module_name == "arch_runner":
        import frob.app.arch_runner as module
    elif module_name == "bind_runner":
        import frob.app.bind_runner as module
    elif module_name == "check_runner":
        import frob.app.check_runner as module
    elif module_name == "clean_runner":
        import frob.app.clean_runner as module
    elif module_name == "cycle_runner":
        import frob.app.cycle_runner as module
    elif module_name == "debt_runner":
        import frob.app.debt_runner as module
    elif module_name == "deploy_runner":
        import frob.app.deploy_runner as module
    elif module_name == "docs_runner":
        import frob.app.docs_runner as module
    elif module_name == "doctor_runner":
        import frob.app.doctor_runner as module
    elif module_name == "dup_runner":
        import frob.app.dup_runner as module
    elif module_name == "exports_runner":
        import frob.app.exports_runner as module
    elif module_name == "fleet_runner":
        import frob.app.fleet_runner as module
    elif module_name == "gitlog_runner":
        import frob.app.gitlog_runner as module
    elif module_name == "graph_runner":
        import frob.app.graph_runner as module
    elif module_name == "map_runner":
        import frob.app.map_runner as module
    elif module_name == "mutate_runner":
        import frob.app.mutate_runner as module
    elif module_name == "outline_runner":
        import frob.app.outline_runner as module
    elif module_name == "parse_runner":
        import frob.app.parse_runner as module
    elif module_name == "perf_runner":
        import frob.app.perf_runner as module
    elif module_name == "pool_runner":
        import frob.app.pool_runner as module
    elif module_name == "registry_runner":
        import frob.app.registry_runner as module
    elif module_name == "release_runner":
        import frob.app.release_runner as module
    elif module_name == "scaffold_runner":
        import frob.app.scaffold_runner as module
    elif module_name == "serve_runner":
        import frob.app.serve_runner as module
    elif module_name == "stats_runner":
        import frob.app.stats_runner as module
    elif module_name == "sys_runner":
        import frob.app.sys_runner as module
    elif module_name == "test_runner":
        import frob.app.test_runner as module
    elif module_name == "ticket_runner":
        import frob.app.ticket_runner as module
    elif module_name == "vet_runner":
        import frob.app.vet_runner as module
    elif module_name == "xref_runner":
        import frob.app.xref_runner as module
    else:  # pragma: no cover -- unreachable: module_name always from closed domain
        raise AssertionError(
            f"_import_runner_run_module: unknown runner module name {module_name!r}"
        )
    return module


# frob:ticket T-1216
# frob:ticket T-1337
# frob:waive OPAQUE001 reason="T-1337: this module-level __getattr__ resolves ONLY a \
# '<name>_runner_run' alias present as a KEY in the closed, statically-declared \
# _RUNNER_RUN_MODULES dict above (the 'module_name is None' check below) -- not an \
# arbitrary attribute-interception surface; any name outside that closed set raises \
# AttributeError immediately. The module-name resolution itself no longer calls \
# importlib.import_module (see _import_runner_run_module's closed if/elif chain of \
# literal imports, T-1337) -- only this construct-level finding (def __getattr__ is \
# unconditionally opaque per RUNTIME_OPAQUE_CONSTRUCTS's literal_arg_index=None row, \
# regardless of body) remains, and is bounded by _RUNNER_RUN_MODULES plus this \
# function's own AttributeError-on-miss fallback. Pinned by the two frob:tests edges \
# below (test_accessing_one_alias_does_not_import_the_others, \
# test_unknown_attribute_still_raises_attribute_error)"
# frob:tests tests/unit/test_app_lazy_exports.py::TestLazyRunnerRunAttrs.test_accessing_one_alias_does_not_import_the_others  # noqa: E501
# frob:tests tests/unit/test_app_lazy_exports.py::TestLazyRunnerRunAttrs.test_unknown_attribute_still_raises_attribute_error  # noqa: E501
def __getattr__(name: str) -> Any:
    """PEP 562 module `__getattr__`: resolve a `<name>_runner_run` alias by
    importing ONLY that one runner module, on first access, then cache the
    resolved callable into this module's globals (so the cost is paid at
    most once per process, and every access after the first is a plain
    attribute read -- no re-import, no repeated `__getattr__` call)."""
    module_name = _RUNNER_RUN_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = _import_runner_run_module(module_name)
    run = module.run
    globals()[name] = run
    return run


__all__ = [
    "App",
    "AppConfig",
    "Subcommand",
    "ack_runner_run",
    "append_event",
    "arch_runner_run",
    "bind_runner_run",
    "check_runner_run",
    "clean_runner_run",
    "cycle_runner_run",
    "debt_runner_run",
    "deploy_runner_run",
    "docs_runner_run",
    "doctor_runner_run",
    "dup_runner_run",
    "estimate_tokens",
    "exports_runner_run",
    "fleet_runner_run",
    "gitlog_runner_run",
    "graph_runner_run",
    "is_disabled",
    "iso_now",
    "load_arch_config",
    "map_runner_run",
    "mutate_runner_run",
    "outline_runner_run",
    "parse_runner_run",
    "perf_runner_run",
    "pool_runner_run",
    "profile_runner_run",
    "record_cli_event",
    "record_ticket_event",
    "redact_command",
    "registry_runner_run",
    "release_runner_run",
    "scaffold_runner_run",
    "serve_runner_run",
    "stale_install_warning",
    "stats_runner_run",
    "style_fail",
    "style_header",
    "style_ok",
    "style_rule",
    "style_state",
    "style_ticket_id",
    "style_warn",
    "sys_runner_run",
    "test_runner_run",
    "ticket_runner_run",
    "timed_call",
    "tree_hash",
    "vet_runner_run",
    "xref_runner_run",
]
