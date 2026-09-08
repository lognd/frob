"""T-1216: `frob.app`'s `<name>_runner_run` aliases must resolve lazily
(PEP 562 `__getattr__`), never importing every runner module up front.

Uses a subprocess with a clean interpreter for the "does not import" checks
-- within the same pytest process, other tests may have already imported
some of these runner modules, making an in-process `sys.modules` check
unreliable either way (a false pass if already imported by this test file's
own fixtures, a false fail if some OTHER test imported it first)."""

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


# frob:ticket T-1636
class TestLazyRunnerRunAttrs:
    # frob:ticket T-1424
    # frob:ticket T-1636
    def test_accessing_one_alias_does_not_import_the_others(self) -> None:
        # frob:tests src/frob/app/__init__.py::__getattr__ kind="unit"
        # frob:tests src/frob/app/__init__.py::_import_runner_run_module kind="integration"  # noqa: E501
        code = (
            "import sys\n"
            "import frob.app as app\n"
            "clean_run = app.clean_runner_run\n"
            "print(callable(clean_run))\n"
            "print('frob.app.deploy_runner' in sys.modules)\n"
            "print('frob.app.clean_runner' in sys.modules)\n"
        )
        out = _run(code).splitlines()
        assert out[0] == "True"
        # deploy_runner (and its heavy strata/vet/gates chain) must never
        # be imported just because an unrelated alias was accessed.
        assert out[1] == "False"
        assert out[2] == "True"

    def test_unknown_attribute_still_raises_attribute_error(self) -> None:
        # frob:tests src/frob/app/__init__.py::__getattr__ kind="unit"
        import frob.app as app

        try:
            app.definitely_not_a_real_attribute  # type: ignore[attr-defined]
        except AttributeError as exc:
            assert "definitely_not_a_real_attribute" in str(exc)
        else:
            raise AssertionError("expected AttributeError")

    # frob:ticket T-4297
    def test_every_registered_runner_run_alias_resolves(self) -> None:
        """T-4297: walk every `_RUNNER_RUN_MODULES` entry (not just one spot
        check) so a name added to that dict without a matching branch in
        `_import_runner_run_module`'s closed if/elif chain fails immediately,
        instead of only surfacing on whichever alias a caller happens to
        touch first."""
        # frob:tests src/frob/app/__init__.py::_import_runner_run_module kind="unit"
        import frob.app as app

        for alias in app._RUNNER_RUN_MODULES:
            # frob:waive OPAQUE001 reason="T-4297: alias is drawn from the closed \
            # _RUNNER_RUN_MODULES dict this very test walks exhaustively; that is the \
            # point of the test, not an arbitrary runtime name."
            run = getattr(app, alias)
            assert callable(run), f"{alias} did not resolve to a callable"
