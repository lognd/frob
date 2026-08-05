"""T-1318: `frob.security._redact`'s whole reason for existing is that
importing it, and calling `frob.app.telemetry.redact_command` (which
imports it internally), must NEVER pull in `frob.gates` -- the heavy
aggregator package whose `__init__.py` eagerly imports its entire stage
roster (pii, arch, dup, vet._capability, testing, ...) as a side effect of
importing ANY of its submodules, including `frob.gates._secrets` (the
pre-T-1318 import site `redact_command` used to reach for).

Uses a subprocess with a clean interpreter, same precedent as
`tests/unit/test_app_lazy_exports.py`'s own T-1216 import-graph tests --
within the same pytest process, some OTHER test may have already imported
`frob.gates`, making an in-process `sys.modules` check unreliable either
way (a false pass from this test file's own prior imports, a false fail
from some unrelated test's).
"""

from __future__ import annotations

import subprocess
import sys


# frob:waive DUP001 reason="established clean-interpreter subprocess-run fixture \
# idiom, verbatim in tests/unit/test_app_lazy_exports.py and \
# tests/unit/test_app_lazy_dispatch.py (T-1216) before this file's own T-1318 \
# import-graph tests added a third copy -- same shape as the _debt_deprecated.py \
# DUP001 waiver precedent, extracting a shared helper would add an import-graph \
# coupling this file exists specifically to avoid"
def _run(code: str) -> str:
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


class TestRedactModuleImportGraph:
    """`import frob.security._redact` alone must never load `frob.gates`."""

    def test_importing_redact_module_never_loads_frob_gates(self) -> None:
        # frob:tests tests/unit/security/test_redact.py::TestRedactModuleImportGraph.test_importing_redact_module_never_loads_frob_gates  # noqa: E501
        code = (
            "import sys\n"
            "import frob.security._redact\n"
            "print('frob.gates' in sys.modules)\n"
        )
        out = _run(code)
        assert out == "False", out


class TestRedactCommandImportGraph:
    """`frob.app.telemetry.redact_command` -- the actual per-CLI-invocation
    call site T-1318's own incident named -- must never load `frob.gates`
    either, not just the module that defines it."""

    def test_calling_redact_command_never_loads_frob_gates(self) -> None:
        # frob:tests tests/unit/security/test_redact.py::TestRedactCommandImportGraph.test_calling_redact_command_never_loads_frob_gates  # noqa: E501
        code = (
            "import sys\n"
            "from frob.app.telemetry import redact_command\n"
            # frob:secret-fake reason="T-1318 fixture placeholder"
            "redact_command('sk-ant-abcdefghijklmnopqrstuvwxyz1234567890')\n"
            "print('frob.gates' in sys.modules)\n"
        )
        out = _run(code)
        assert out == "False", out

    def test_redact_command_still_redacts_a_real_looking_token(self) -> None:
        # frob:tests tests/unit/security/test_redact.py::TestRedactCommandImportGraph.test_redact_command_still_redacts_a_real_looking_token  # noqa: E501
        code = (
            "from frob.app.telemetry import redact_command\n"
            # frob:secret-fake reason="T-1318 fixture placeholder"
            "print(redact_command('sk-ant-abcdefghijklmnopqrstuvwxyz1234567890'))\n"
        )
        out = _run(code)
        assert out.startswith("sk-ant-...")
        assert "abcdefghijklmnopqrstuvwxyz1234567890" not in out


class TestGatesSecretsStillWorksViaTheExtractedModule:
    """`frob.gates._secrets` (the gate's own consumer) must still detect
    and redact exactly as before -- the extraction moved WHERE the
    detection engine lives, never WHAT it detects."""

    def test_secrets_gate_module_still_exposes_redact_and_scan_line(self) -> None:
        # frob:tests tests/unit/security/test_redact.py::TestGatesSecretsStillWorksViaTheExtractedModule.test_secrets_gate_module_still_exposes_redact_and_scan_line  # noqa: E501
        from frob.gates import _secrets
        from frob.security._redact import _redact, _scan_line

        assert _secrets._redact is _redact
        assert _secrets._scan_line is _scan_line

    def test_severity_round_trips_through_the_plain_string_boundary(self) -> None:
        # frob:tests tests/unit/security/test_redact.py::TestGatesSecretsStillWorksViaTheExtractedModule.test_severity_round_trips_through_the_plain_string_boundary  # noqa: E501
        from frob.gates._models import Severity
        from frob.security._redact import _PATTERNS

        for pattern in _PATTERNS:
            # _SecretPattern.severity is a plain str ("error"/"warn") in
            # the extracted module (it has no Severity import at all,
            # T-1318's whole point) -- frob.gates._secrets converts via
            # Severity(pattern.severity) at its own Violation call site;
            # this proves every stored value actually round-trips.
            assert Severity(pattern.severity) in (Severity.ERROR, Severity.WARN)
