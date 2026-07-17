"""frob.vet -- dependency-vetting (docs/vet.md).

Lockfile-conformance slice: allow-list conformance (VET001), cooldown
quarantine (VET011), JS lifecycle-script detection (VET-JS), typosquat
distance, and an osv-scanner adapter (VET005). T-0008 slice on top: tree-
sitter capability scanning, the VET004 obfuscation ensemble, VET002/VET003
conformance-and-escalation diffs, and cheap per-ecosystem rules (VET-PY,
VET-RS, VET-JS004). See docs/vet.md "Implementation notes" for what remains
out of scope (VET006-VET010, most of VET-C, dynamic detonation).
"""

from __future__ import annotations

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
from frob.vet._scan import scan_tree

__all__ = [
    "Dependency",
    "HookVerdict",
    "PackageVerdict",
    "VetConfig",
    "VetError",
    "VetReport",
    "Violation",
    "capability_diff",
    "check_package",
    "parse_hook_command",
    "scan_tree",
]
