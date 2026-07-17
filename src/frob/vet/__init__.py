"""frob.vet -- dependency-vetting MVP (docs/vet.md).

Implements the lockfile-conformance slice of the full design: allow-list
conformance (VET001), cooldown quarantine (VET011), JS lifecycle-script
detection (VET-JS), typosquat distance, and an osv-scanner adapter (VET005).
Full capability scanning (VET002-VET004, VET006-VET010) is 0.2.x.
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
    "check_package",
    "parse_hook_command",
    "scan_tree",
]
