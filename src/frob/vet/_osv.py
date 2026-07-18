"""osv-scanner adapter (docs/modules/vet.md "External tool adapters" -- VET005).

Honest absence: no binary on PATH -> skipped-with-note, never silent."""

# frob:waive TEST005 reason="module line coverage 47.9%, debt T-0160"

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from frob.gitio import run_argv
from frob.logging import get_logger

_log = get_logger(__name__)

_BINARY = "osv-scanner"

#: An OSV advisory id (or one of its `aliases`) is a CVE id when it matches
#: this shape (docs/strata/threat.md "CVE: threat intelligence joined to
#: the proof") -- GHSA/PYSEC/RUSTSEC-only advisories with no CVE alias are
#: honestly out of the T-0110 join (see `_containment.py` module docstring).
_CVE_RE = re.compile(r"^CVE-\d{4}-\d+$")


# frob:doc docs/modules/vet.md#public-api
class OsvAdvisory:
    """One advisory finding: id + affected package + fixed version (if known)
    + any `aliases` osv-scanner reports (GHSA<->CVE cross-references)."""

    __slots__ = ("advisory_id", "package", "version", "fixed_version", "aliases")

    def __init__(
        self,
        advisory_id: str,
        package: str,
        version: str,
        fixed_version: str | None,
        aliases: tuple[str, ...] = (),
    ) -> None:
        self.advisory_id = advisory_id
        self.package = package
        self.version = version
        self.fixed_version = fixed_version
        self.aliases = aliases


# frob:doc docs/modules/vet.md#public-api
def cve_ids(advisory: OsvAdvisory) -> tuple[str, ...]:
    """The CVE-shaped ids naming `advisory`: its own `advisory_id` plus any
    `aliases` matching `CVE-\\d{4}-\\d+` (docs/strata/threat.md "CVE: threat
    intelligence joined to the proof") -- a GHSA/PYSEC/RUSTSEC-only advisory
    with no CVE alias yields an empty tuple, honestly, rather than a guess."""
    candidates = (advisory.advisory_id, *advisory.aliases)
    seen: list[str] = []
    for candidate in candidates:
        if _CVE_RE.match(candidate) and candidate not in seen:
            seen.append(candidate)
    return tuple(seen)


# frob:doc docs/modules/vet.md#public-api
def is_available() -> bool:
    """Whether `osv-scanner` is resolvable on PATH."""
    return shutil.which(_BINARY) is not None


# frob:doc docs/modules/vet.md#public-api
# frob:waive TEST005 reason="run_osv_scan 19.0% branch cover, debt T-0160"
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
                aliases = tuple(vuln.get("aliases", []))
                advisories.append(
                    OsvAdvisory(vuln_id, name, version, _fixed_version(vuln), aliases)
                )
    return advisories


__all__ = ["OsvAdvisory", "cve_ids", "is_available", "run_osv_scan"]
