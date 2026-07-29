from __future__ import annotations

import sys
from collections.abc import Callable

from frob.app.config import AppConfig, Subcommand
from frob.logging import get_logger

_log = get_logger(__name__)


_RUNNER_MODULE_NAMES = (
    "ack_runner",
    "arch_runner",
    "check_runner",
    "clean_runner",
    "cycle_runner",
    "debt_runner",
    "deprecated_runner",
    "deploy_runner",
    "doctor_runner",
    "docs_runner",
    "dup_runner",
    "exports_runner",
    "fleet_runner",
    "fmt_runner",
    "gitlog_runner",
    "graph_runner",
    "map_runner",
    "mutate_runner",
    "natives_runner",
    "outline_runner",
    "parse_runner",
    "perf_runner",
    "pool_runner",
    "registry_runner",
    "release_runner",
    "scaffold_runner",
    "serve_runner",
    "stats_runner",
    "sys_runner",
    "test_runner",
    "ticket_runner",
    "vet_runner",
    "xref_runner",
)
"""Every `frob.app.*_runner` module name with a uniform `run(AppConfig)`
entry point -- documents the full set `_SUBCOMMAND_RUNNER_NAMES` maps
subcommands onto; not imported as a batch by anything else (T-1216:
`_resolve_runner` imports exactly the one module a live invocation's
subcommand actually needs)."""


_SUBCOMMAND_RUNNER_NAMES: dict[Subcommand, str] = {
    Subcommand.scaffold: "scaffold_runner",
    Subcommand.cycle: "cycle_runner",
    Subcommand.outline: "outline_runner",
    Subcommand.map: "map_runner",
    Subcommand.xref: "xref_runner",
    Subcommand.parse: "parse_runner",
    Subcommand.dup: "dup_runner",
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
    Subcommand.natives: "natives_runner",
}
"""Every subcommand handled by a uniform `*_runner.run(AppConfig)` entry point,
mapped to the runner module name that serves it. `bind` is excluded: it takes
a raw argv rather than an `AppConfig`, so `App.__call__` wires it up
separately."""


# frob:ticket T-1216
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
    to pay even though it never touches any of those modules."""
    import importlib

    name = _SUBCOMMAND_RUNNER_NAMES.get(subcommand)
    if name is None:
        return None
    return getattr(importlib.import_module(f"frob.app.{name}"), "run")


# frob:doc docs/modules/app.md#entry-point
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
                "<scaffold|cycle|outline|map|xref|parse|dup|arch|docs|bind|"
                "exports|check|gitlog|graph|ack|debt|deprecated|pool|ticket|test|vet|"
                "perf|release|stats|serve|mutate|sys|deploy|doctor|clean|fleet|fmt>"
                " ..."
            )
            sys.exit(1)
        # frob:ticket T-0178
        from pathlib import Path

        from frob.app.telemetry import timed_call

        root = Path(".").resolve()
        timed_call(
            root,
            subcommand=subcommand.value if subcommand else "",
            args_head=" ".join(sys.argv[1:])[:512],
            fn=lambda: handler(self._cfg),
        )
