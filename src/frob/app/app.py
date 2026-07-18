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
    "cycle_runner",
    "docs_runner",
    "dup_runner",
    "exports_runner",
    "gitlog_runner",
    "graph_runner",
    "map_runner",
    "mutate_runner",
    "outline_runner",
    "parse_runner",
    "perf_runner",
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


# frob:ticket T-0021
def _dispatch_table() -> dict[Subcommand, Callable[[AppConfig], None]]:
    """Map each subcommand to the runner entry point that handles it."""
    from frob.app import bind_runner

    r = _import_runner_modules()
    return {
        Subcommand.scaffold: r["scaffold_runner"],
        Subcommand.cycle: r["cycle_runner"],
        Subcommand.outline: r["outline_runner"],
        Subcommand.map: r["map_runner"],
        Subcommand.xref: r["xref_runner"],
        Subcommand.parse: r["parse_runner"],
        Subcommand.dup: r["dup_runner"],
        Subcommand.arch: r["arch_runner"],
        Subcommand.docs: r["docs_runner"],
        Subcommand.bind: lambda _cfg: bind_runner.run([]),
        Subcommand.exports: r["exports_runner"],
        Subcommand.check: r["check_runner"],
        Subcommand.gitlog: r["gitlog_runner"],
        Subcommand.graph: r["graph_runner"],
        Subcommand.ack: r["ack_runner"],
        Subcommand.ticket: r["ticket_runner"],
        Subcommand.test: r["test_runner"],
        Subcommand.vet: r["vet_runner"],
        Subcommand.perf: r["perf_runner"],
        Subcommand.release: r["release_runner"],
        Subcommand.stats: r["stats_runner"],
        Subcommand.serve: r["serve_runner"],
        Subcommand.mutate: r["mutate_runner"],
        Subcommand.sys: r["sys_runner"],
    }


# frob:doc docs/modules/app.md#entry-point
class App:
    # frob:ticket T-0021
    def __init__(self, cfg: AppConfig) -> None:
        self._cfg = cfg

    def __call__(self) -> None:
        # frob:ticket T-0021
        subcommand = self._cfg.subcommand
        handler = _dispatch_table().get(subcommand) if subcommand else None
        if handler is None:
            _log.error(
                "usage: frob "
                "<scaffold|cycle|outline|map|xref|parse|dup|arch|docs|bind|"
                "exports|check|gitlog|graph|ack|ticket|test|vet|perf|"
                "release|stats|serve|mutate|sys>"
                " ..."
            )
            sys.exit(1)
        handler(self._cfg)
