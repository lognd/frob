"""T-1216: `frob.app.app._resolve_runner` must import ONLY the one runner
module a given subcommand needs, never the full runner set `App.__call__`
used to build via the old `_dispatch_table()`/`_import_runner_modules()`
pair."""

from __future__ import annotations

import subprocess
import sys

import pytest

from frob.app.app import _resolve_runner
from frob.app.config import Subcommand


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
    # frob:ticket T-1343
    def test_imports_only_the_requested_subcommands_module(self) -> None:
        # frob:tests src/frob/app/app.py::_resolve_runner kind="unit"
        # frob:waive COV006 reason="T-1343: confirmed exercised -- this assertion \
        # drives _resolve_runner through a subprocess.run([sys.executable, -c, code]) \
        # child process, so the actual call lives inside a string literal executed \
        # out-of-process, structurally invisible to frob.graph.callgraph's in-process \
        # AST-based best-effort BFS. Same subprocess-boundary class as this repo's \
        # other COV006 waivers (tests/system/test_cli_ticket_land.py::TestLandCLI:: \
        # test_dry_run_reports_clean); pre-dates and is unrelated to T-1337's \
        # OPAQUE001 lazy-dispatch fix."
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


# frob:ticket T-1319
class TestResolveRunnerDispatchTotality:
    """T-1319 acceptance [1]: an exhaustive, statically-enumerated totality
    check over every `Subcommand` member -- a future subcommand added to
    the enum without a matching `_SUBCOMMAND_RUNNER_NAMES` entry fails this
    test immediately, instead of only surfacing the first time a live
    invocation of that subcommand hits `_resolve_runner` and silently gets
    `None` back (`bind` is excepted by design: `App.__call__` wires it up
    separately since it parses a raw argv rather than an `AppConfig`,
    documented on `_SUBCOMMAND_RUNNER_NAMES` itself)."""

    # frob:tests tests/unit/test_app_lazy_dispatch.py::TestResolveRunnerDispatchTotality.test_every_non_bind_subcommand_resolves_a_callable_runner kind="unit"  # noqa: E501
    @pytest.mark.parametrize("subcommand", sorted(Subcommand, key=lambda s: s.value))
    def test_every_non_bind_subcommand_resolves_a_callable_runner(
        self, subcommand: Subcommand
    ) -> None:
        runner = _resolve_runner(subcommand)
        if subcommand is Subcommand.bind:
            assert runner is None
        else:
            assert callable(runner), (
                f"{subcommand!r} has no _SUBCOMMAND_RUNNER_NAMES entry (or its "
                "runner module has no callable run) -- add it to "
                "_SUBCOMMAND_RUNNER_NAMES and _import_runner_module's if/elif chain"
            )
