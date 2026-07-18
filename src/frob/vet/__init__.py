"""frob.vet -- dependency-vetting (docs/modules/vet.md).

Lockfile-conformance slice: allow-list conformance (VET001), cooldown
quarantine (VET011), JS lifecycle-script detection (VET-JS), typosquat
distance, and an osv-scanner adapter (VET005). T-0008 slice on top: tree-
sitter capability scanning, the VET004 obfuscation ensemble, VET002/VET003
conformance-and-escalation diffs, and cheap per-ecosystem rules (VET-PY,
VET-RS, VET-JS004). See docs/modules/vet.md "Implementation notes" for what remains
out of scope (VET006-VET010, most of VET-C, dynamic detonation).
"""

from __future__ import annotations

from frob.vet._containment import (
    CONTAINED,
    LIVE,
    UNMODELED,
    UNVERIFIED,
    ContainmentFinding,
    ContainmentReport,
    build_containment_report,
    find_importing_nodes,
    render_containment_report,
)
from frob.vet._cve import (
    CveMatch,
    CweDisposition,
    CweLink,
    MatchStatus,
    link_cwe_ids,
    match_dependencies_against_mirror,
)
from frob.vet._hook import check_package, parse_hook_command
from frob.vet._models import (
    Dependency,
    HookVerdict,
    PackageVerdict,
    VetConfig,
    VetError,
    VetReport,
    Violation,
    capability_diff,
)
from frob.vet._nvd import NvdResult, fetch_cwe_for_cve
from frob.vet._osv import OsvAdvisory, cve_ids
from frob.vet._scan import scan_tree

__all__ = [
    "CONTAINED",
    "LIVE",
    "UNMODELED",
    "UNVERIFIED",
    "ContainmentFinding",
    "ContainmentReport",
    "CveMatch",
    "CweDisposition",
    "CweLink",
    "Dependency",
    "HookVerdict",
    "MatchStatus",
    "NvdResult",
    "OsvAdvisory",
    "PackageVerdict",
    "VetConfig",
    "VetError",
    "VetReport",
    "Violation",
    "build_containment_report",
    "capability_diff",
    "check_package",
    "cve_ids",
    "fetch_cwe_for_cve",
    "find_importing_nodes",
    "link_cwe_ids",
    "match_dependencies_against_mirror",
    "parse_hook_command",
    "render_containment_report",
    "scan_tree",
]
