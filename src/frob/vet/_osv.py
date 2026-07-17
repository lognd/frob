"""osv-scanner adapter (docs/modules/vet.md "External tool adapters" -- VET005).

Honest absence: no binary on PATH -> skipped-with-note, never silent."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from frob.gitio import run_argv
from frob.logging import get_logger

_log = get_logger(__name__)

_BINARY = "osv-scanner"


# frob:doc docs/modules/vet.md#public-api
class OsvAdvisory:
    """One advisory finding: id + affected package + fixed version, if known."""

    __slots__ = ("advisory_id", "package", "version", "fixed_version")

    def __init__(
        self, advisory_id: str, package: str, version: str, fixed_version: str | None
    ) -> None:
        self.advisory_id = advisory_id
        self.package = package
        self.version = version
        self.fixed_version = fixed_version


# frob:doc docs/modules/vet.md#public-api
def is_available() -> bool:
    """Whether `osv-scanner` is resolvable on PATH."""
    return shutil.which(_BINARY) is not None


# frob:doc docs/modules/vet.md#public-api
def run_osv_scan(lockfile: Path) -> tuple[OsvAdvisory, ...] | None:
    """Advisories for `lockfile`, or `None` if osv-scanner is absent/failed
    (caller must report a skipped-note, never treat `None` as "no findings")."""
    if not is_available():
        _log.info("vet: %s not on PATH; VET005 skipped", _BINARY)
        return None

    argv = (_BINARY, "--lockfile", str(lockfile), "--format", "json")
    spawned = run_argv(argv, timeout_s=60.0)
    if spawned.is_err:
        _log.warning("vet: osv-scanner invocation failed: %s", spawned.danger_err)
        return None
    result = spawned.danger_ok
    # osv-scanner exits non-zero when it finds vulnerabilities; only a parse
    # failure or crash (empty stdout) is a real adapter failure.
    if not result.stdout.strip():
        if result.returncode != 0:
            _log.warning(
                "vet: osv-scanner exited %d with no output: %s",
                result.returncode,
                result.stderr,
            )
            return None
        return ()

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        _log.warning("vet: osv-scanner output unparseable: %s", exc)
        return None

    advisories = _advisories_from_data(data)
    _log.info("vet: osv-scanner reported %d advisory finding(s)", len(advisories))
    return tuple(advisories)


def _fixed_version(vuln: dict) -> str | None:
    """The last-declared `fixed` event across a vuln's affected ranges, if any."""
    fixed: str | None = None
    for affected in vuln.get("affected", []):
        for rng in affected.get("ranges", []):
            for event in rng.get("events", []):
                if "fixed" in event:
                    fixed = event["fixed"]
    return fixed


def _advisories_from_data(data: dict) -> list[OsvAdvisory]:
    """Flatten osv-scanner's nested results JSON into `OsvAdvisory` records."""
    advisories: list[OsvAdvisory] = []
    for result_entry in data.get("results", []):
        for pkg_entry in result_entry.get("packages", []):
            pkg_info = pkg_entry.get("package", {})
            name = pkg_info.get("name", "")
            version = pkg_info.get("version", "")
            for vuln in pkg_entry.get("vulnerabilities", []):
                vuln_id = vuln.get("id", "unknown")
                advisories.append(
                    OsvAdvisory(vuln_id, name, version, _fixed_version(vuln))
                )
    return advisories


__all__ = ["OsvAdvisory", "is_available", "run_osv_scan"]
