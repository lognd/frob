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


class TestLazyRunnerRunAttrs:
    def test_accessing_one_alias_does_not_import_the_others(self) -> None:
        # frob:tests src/frob/app/__init__.py::__getattr__ kind="unit"
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
