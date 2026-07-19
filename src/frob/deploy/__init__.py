"""`frob.deploy`: compile `std.host` `HostManifest` facts (T-0255) into
idempotent Linux/systemd install/status/uninstall bash, drift-locked
against the design model (T-0257, deploy epic T-0254).

Public surface: `generate_all`/`generate_install_script`/
`generate_status_script`/`generate_uninstall_script`/`manifest_digest`
(`_generate.py`) and `deploy_drift_violations` (`_drift.py`, DEPLOY001).
No generator or check here redefines `HostManifest` (T-0255) or the
HOST001/HOST002 isolation checks (T-0256) -- both are consumed as-is.
"""

from __future__ import annotations

from frob.deploy._drift import DeployDriftViolation, deploy_drift_violations
from frob.deploy._generate import (
    ManifestEntry,
    generate_all,
    generate_install_script,
    generate_status_script,
    generate_uninstall_script,
    manifest_digest,
    sorted_manifest_entries,
)

__all__ = [
    "DeployDriftViolation",
    "ManifestEntry",
    "deploy_drift_violations",
    "generate_all",
    "generate_install_script",
    "generate_status_script",
    "generate_uninstall_script",
    "manifest_digest",
    "sorted_manifest_entries",
]
