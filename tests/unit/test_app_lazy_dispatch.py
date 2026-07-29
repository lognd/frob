"""T-1216: `frob.app.app._resolve_runner` must import ONLY the one runner
module a given subcommand needs, never the full runner set `App.__call__`
used to build via the old `_dispatch_table()`/`_import_runner_modules()`
pair."""

from __future__ import annotations

import subprocess
import sys


def _run(code: str) -> str:
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


class TestResolveRunner:
    def test_imports_only_the_requested_subcommands_module(self) -> None:
        # frob:tests src/frob/app/app.py::_resolve_runner kind="unit"
        code = (
            "import sys\n"
            "from frob.app.app import _resolve_runner\n"
            "from frob.app.config import Subcommand\n"
            "run = _resolve_runner(Subcommand.outline)\n"
            "print(callable(run))\n"
            "print('frob.app.outline_runner' in sys.modules)\n"
            "print('frob.app.deploy_runner' in sys.modules)\n"
        )
        out = _run(code).splitlines()
        assert out[0] == "True"
        assert out[1] == "True"
        assert out[2] == "False"

    def test_unknown_subcommand_returns_none(self) -> None:
        # frob:tests src/frob/app/app.py::_resolve_runner kind="unit"
        from frob.app.app import _resolve_runner
        from frob.app.config import Subcommand

        assert _resolve_runner(Subcommand.bind) is None
