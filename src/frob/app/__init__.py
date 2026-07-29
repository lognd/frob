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

import importlib
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


# frob:ticket T-1216
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
    module = importlib.import_module(f"frob.app.{module_name}")
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
