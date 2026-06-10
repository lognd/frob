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
            bundle_runner,
            cycle_runner,
            init_runner,
            map_runner,
            outline_runner,
            parse_runner,
            stub_runner,
            tokens_runner,
            xref_runner,
        )

        match self._cfg.subcommand:
            case Subcommand.init:
                init_runner.run(self._cfg)
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
            case _:
                _log.error("usage: frob <init|cycle|stub|outline|map|xref|tokens|bundle|parse> ...")
                sys.exit(1)
