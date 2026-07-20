# frob:waive SCOPE001 reason="T-0319 scope comma-joined, matches nothing (T-0241 bug)"
# frob:waive TEST003 reason="pre-existing T-0319 debt, system kind only"
"""`frob doctor`: verify the native extensions (`frob_core`, `strata_core`)
are importable in the current environment and print exact remediation when
they are not.

Follow-up from T-0316: a plain `uv tool upgrade frob` (or `uv tool install
--force --reinstall frob` without `--with`) can silently strip the natives
`make install-tool` added, degrading `frob dup`'s R3+ rungs and every
`frob sys` command to the honest-but-easy-to-miss `SYS004` /
`DupError.CoreUnavailable` failure path. This module makes that same check a
first-class, explicit CLI surface instead of a paragraph in
docs/guides/install.md.
"""

from __future__ import annotations

import importlib
from importlib.metadata import PackageNotFoundError, version

from pydantic import BaseModel

from frob.logging import get_logger

_log = get_logger(__name__)

# frob:doc docs/guides/install.md#frob-doctor-native-extension-diagnosis-t-0319
#: the exact remediation command printed when a native extension is missing.
REMEDIATION_HINT = (
    "run 'make core' (build in-place) or 'make install-tool' "
    "(reinstall the frob CLI with natives bundled)"
)

# frob:doc docs/guides/install.md#frob-doctor-native-extension-diagnosis-t-0319
#: Native extension module names `frob doctor` checks for importability.
NATIVE_EXTENSIONS: tuple[str, ...] = ("frob_core", "strata_core")


# frob:doc docs/guides/install.md#frob-doctor-native-extension-diagnosis-t-0319
class NativeExtensionStatus(BaseModel):
    """Importability and version of one native extension, as observed by
    `frob doctor`."""

    model_config = {}

    name: str
    available: bool
    version: str | None = None


# frob:doc docs/guides/install.md#frob-doctor-native-extension-diagnosis-t-0319
class DoctorReport(BaseModel):
    """Full `frob doctor` diagnosis: per-extension status plus the overall
    verdict and remediation hint (empty when everything is healthy)."""

    model_config = {}

    frob_version: str
    extensions: list[NativeExtensionStatus]
    healthy: bool
    remediation: str | None = None


def _extension_status(name: str) -> NativeExtensionStatus:
    """Import `name` and report whether it succeeded, plus its version if
    the module exposes one -- never raises, a missing extension is a normal
    (not exceptional) outcome this function reports rather than propagates."""
    try:
        mod = importlib.import_module(name)
    except ImportError:
        _log.warning("doctor: native extension %s not importable", name)
        return NativeExtensionStatus(name=name, available=False, version=None)
    mod_version = getattr(mod, "__version__", None)
    _log.debug("doctor: native extension %s available (version=%s)", name, mod_version)
    return NativeExtensionStatus(name=name, available=True, version=mod_version)


def _frob_version() -> str:
    """Resolve the installed `frob` distribution version, or 'unknown' when
    run from a source checkout with no registered distribution metadata."""
    try:
        return version("frob")
    except PackageNotFoundError:
        return "unknown"


# frob:doc docs/guides/install.md#frob-doctor-native-extension-diagnosis-t-0319
# frob:tests tests/system/test_cli_doctor.py kind="integration"
def run_diagnosis() -> DoctorReport:
    """Check every entry in `NATIVE_EXTENSIONS` for importability and build
    the full `DoctorReport` -- `healthy` is True only when all of them
    import cleanly, and `remediation` carries `REMEDIATION_HINT` whenever
    it is not."""
    extensions = [_extension_status(name) for name in NATIVE_EXTENSIONS]
    healthy = all(ext.available for ext in extensions)
    report = DoctorReport(
        frob_version=_frob_version(),
        extensions=extensions,
        healthy=healthy,
        remediation=None if healthy else REMEDIATION_HINT,
    )
    _log.info("doctor: healthy=%s extensions=%s", healthy, extensions)
    return report
