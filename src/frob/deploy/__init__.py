"""`frob.deploy`: compile `std.host` `HostManifest` facts (T-0255) into
idempotent Linux/systemd install/status/uninstall bash, drift-locked and
conformance-checked against the design model (T-0257/T-0258, deploy epic
T-0254).

Public surface: `generate_all`/`generate_install_script`/
`generate_status_script`/`generate_uninstall_script`/`manifest_digest`
(`_generate.py`); `deploy_drift_violations` (`_drift.py`, DEPLOY001); and
`deploy_conformance_violations`/`extract_mutation_surface`/
`expected_mutation_surface` (`_conform.py`, DEPLOY002/DEPLOY003). No
generator or check here redefines `HostManifest` (T-0255) or the
HOST001/HOST002 isolation checks (T-0256) -- both are consumed as-is.
"""

from __future__ import annotations

from frob.deploy._conform import (
    ConformanceViolation,
    MutationTarget,
    deploy_conformance_violations,
    expected_mutation_surface,
    extract_mutation_surface,
)
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
    "ConformanceViolation",
    "DeployDriftViolation",
    "ManifestEntry",
    "MutationTarget",
    "deploy_conformance_violations",
    "deploy_drift_violations",
    "expected_mutation_surface",
    "extract_mutation_surface",
    "generate_all",
    "generate_install_script",
    "generate_status_script",
    "generate_uninstall_script",
    "manifest_digest",
    "sorted_manifest_entries",
]
