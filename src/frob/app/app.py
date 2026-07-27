# frob:waive TEST005 reason="module line coverage 52.0%, debt T-0160"
# frob:waive SCOPE001 reason="T-0319 scope comma-joined, matches nothing (T-0241 bug)"
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
"""Every `frob.app.*_runner` module name, dispatched by `_dispatch_table`."""


def _import_runner_modules() -> dict[str, Callable[[AppConfig], None]]:
    """Every uniform `frob.app.*_runner` module's `run` entry point, keyed by name.

    `bind_runner` is excluded: its `run(argv: list)` takes a raw argv, not an
    `AppConfig`, so `_dispatch_table` wires it up separately. `getattr`
    (rather than static attribute access on the imported module) keeps this
    a plain `str -> Callable` map for the type checker -- the alternative, a
    `dict[str, ModuleType]`, makes every lookup below an unresolved-attribute
    error since `ModuleType` has no `run` member.
    """
    import importlib

    return {
        name: getattr(importlib.import_module(f"frob.app.{name}"), "run")
        for name in _RUNNER_MODULE_NAMES
    }


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
a raw argv rather than an `AppConfig`, so `_dispatch_table` wires it up
separately."""


# frob:ticket T-0021
def _dispatch_table() -> dict[Subcommand, Callable[[AppConfig], None]]:
    """Map each subcommand to the runner entry point that handles it."""
    from frob.app import bind_runner

    r = _import_runner_modules()
    table: dict[Subcommand, Callable[[AppConfig], None]] = {
        subcommand: r[name] for subcommand, name in _SUBCOMMAND_RUNNER_NAMES.items()
    }
    table[Subcommand.bind] = lambda _cfg: bind_runner.run([])
    return table


# frob:doc docs/modules/app.md#entry-point
# frob:waive AFFECT001 reason="T-0988 pure mechanical frob:-directive comment rewrap \
# in an inner method's body; no behavior/contract change, doc anchor remains accurate \
# as-is"
class App:
    # frob:ticket T-0021
    def __init__(self, cfg: AppConfig) -> None:
        self._cfg = cfg

    # frob:waive ARCH103 reason="T-0977: the CLI dispatch entrypoint's one job IS \
    # orchestration -- resolve subcommand, format the usage error, exit; splitting the \
    # usage message out would add indirection with no cohesion gain, and the dispatch \
    # table itself already lives in _dispatch_table()"
    def __call__(self) -> None:
        # frob:ticket T-0021
        subcommand = self._cfg.subcommand
        handler = _dispatch_table().get(subcommand) if subcommand else None
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
