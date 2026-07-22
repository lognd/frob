"""`frob.deploy`: compile `std.host` `HostManifest` facts (T-0255) into
idempotent Linux/systemd install/status/uninstall bash, PLUS (T-0264)
idempotent windows PowerShell/DSC install/status/uninstall for any
`HostPlatform.WINDOWS` manifest, drift-locked and conformance-checked
against the design model (T-0257/T-0258, deploy epic T-0254).

Public surface: `generate_all`/`generate_install_script`/
`generate_status_script`/`generate_uninstall_script`/`manifest_digest`
(`_generate.py`, bash); `generate_windows_install_script`/
`generate_windows_status_script`/`generate_windows_uninstall_script`/
`windows_entries` (`_generate_windows.py`, T-0264, windows);
`deploy_drift_violations` (`_drift.py`, DEPLOY001, covers BOTH platforms'
generated filenames); `deploy_conformance_violations`/
`extract_mutation_surface`/`expected_mutation_surface` (`_conform.py`,
DEPLOY002/DEPLOY003); and the `frob deploy audit --vm` VM snapshot-diff
harness (T-0259, deploy epic T-0254 child 5) -- pure diff/proof/
attestation logic in `_audit.py`, VM orchestration in `_vm_runner.py`. No
generator or check here redefines `HostManifest`/`HostPlatform` (T-0255/
T-0261) or the HOST001/HOST002 isolation checks (T-0256) -- both are
consumed as-is.
"""

from __future__ import annotations

from frob.deploy._audit import (
    ALLOWLIST_PATTERNS,
    AuditAttestation,
    CheckpointResult,
    FileFact,
    StateCapture,
    StateDiff,
    artifact_freeness_holds,
    assert_healthy,
    assert_not_installed,
    build_attestation,
    diff_states,
    idempotence_holds,
    install_exactness_holds,
)
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
from frob.deploy._generate_windows import (
    generate_windows_install_script,
    generate_windows_status_script,
    generate_windows_uninstall_script,
    windows_entries,
)
from frob.deploy._vm_runner import (
    AuditRunResult,
    VmAuditConfig,
    run_vm_audit,
    vboxmanage_available,
)

__all__ = [
    "ALLOWLIST_PATTERNS",
    "AuditAttestation",
    "AuditRunResult",
    "CheckpointResult",
    "ConformanceViolation",
    "DeployDriftViolation",
    "FileFact",
    "ManifestEntry",
    "MutationTarget",
    "StateCapture",
    "StateDiff",
    "VmAuditConfig",
    "artifact_freeness_holds",
    "assert_healthy",
    "assert_not_installed",
    "build_attestation",
    "deploy_conformance_violations",
    "deploy_drift_violations",
    "diff_states",
    "expected_mutation_surface",
    "extract_mutation_surface",
    "generate_all",
    "generate_install_script",
    "generate_status_script",
    "generate_uninstall_script",
    "generate_windows_install_script",
    "generate_windows_status_script",
    "generate_windows_uninstall_script",
    "idempotence_holds",
    "install_exactness_holds",
    "manifest_digest",
    "run_vm_audit",
    "sorted_manifest_entries",
    "vboxmanage_available",
    "windows_entries",
]
