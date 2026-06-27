from __future__ import annotations

import sys

from frob.app.config import AppConfig, Subcommand
from frob.logging import get_logger

_log = get_logger(__name__)


class App:
    def __init__(self, cfg: AppConfig) -> None:
        self._cfg = cfg

    def __call__(self) -> None:
        from frob.app import (
            arch_runner,
            bind_runner,
            bundle_runner,
            check_runner,
            ctx_runner,
            cycle_runner,
            dispatch_runner,
            gitlog_runner,
            mission_runner,
            docs_runner,
            dup_runner,
            edit_runner,
            exports_runner,
            init_runner,
            inspect_runner,
            map_runner,
            outline_runner,
            parse_runner,
            scaffold_runner,
            stub_runner,
            todo_runner,
            tokens_runner,
            xref_runner,
        )

        match self._cfg.subcommand:
            case Subcommand.init:
                scaffold_runner.run(self._cfg)
            case Subcommand.scaffold:
                scaffold_runner.run(self._cfg)
            case Subcommand.cycle:
                cycle_runner.run(self._cfg)
            case Subcommand.stub:
                stub_runner.run(self._cfg)
            case Subcommand.outline:
                outline_runner.run(self._cfg)
            case Subcommand.map:
                map_runner.run(self._cfg)
            case Subcommand.xref:
                xref_runner.run(self._cfg)
            case Subcommand.tokens:
                tokens_runner.run(self._cfg)
            case Subcommand.bundle:
                bundle_runner.run(self._cfg)
            case Subcommand.parse:
                parse_runner.run(self._cfg)
            case Subcommand.dup:
                dup_runner.run(self._cfg)
            case Subcommand.arch:
                arch_runner.run(self._cfg)
            case Subcommand.inspect:
                inspect_runner.run(self._cfg)
            case Subcommand.docs:
                docs_runner.run(self._cfg)
            case Subcommand.bind:
                bind_runner.run([])
            case Subcommand.exports:
                exports_runner.run(self._cfg)
            case Subcommand.edit:
                edit_runner.run(self._cfg)
            case Subcommand.check:
                check_runner.run(self._cfg)
            case Subcommand.ctx:
                ctx_runner.run(self._cfg)
            case Subcommand.mission:
                mission_runner.run(self._cfg)
            case Subcommand.gitlog:
                gitlog_runner.run(self._cfg)
            case Subcommand.dispatch:
                dispatch_runner.run(self._cfg)
            case Subcommand.todo:
                todo_runner.run(self._cfg)
            case _:
                _log.error(
                    "usage: frob "
                    "<scaffold|cycle|stub|outline|map|xref|tokens|bundle|parse|dup|arch|inspect|docs|bind|"
                    "exports|edit|check|ctx|mission|gitlog|dispatch|todo>"
                    " ..."
                )
                sys.exit(1)
