"""Unified registry capability (T-0407): one typed model every
`docs/design/registry/*.yaml` manifest instantiates, so a registry entry's
shape and disposition grammar live in exactly one place instead of being
re-derived ad hoc per consuming gate.

`frob.gates._registry_exhaustiveness.registry_gate` is the only current
consumer, but the model in `frob.registry._models` is the single source of
truth for "what a registry entry is" and "what dispositions mean" -- any
future registry instance (a new domain corpus, a new exhaustible taxonomy
such as T-0424's reflexive check-coverage registry) loads through
`load_registry_dir` rather than hand-rolling its own YAML parse.
"""

from __future__ import annotations

from frob.registry._models import (
    Disposition,
    DispositionKind,
    RegistryAudit,
    RegistryEntry,
    RegistryFile,
    RegistryLoadError,
    audit_registry_file,
    load_registry_dir,
    parse_disposition,
)

__all__ = [
    "Disposition",
    "DispositionKind",
    "RegistryAudit",
    "RegistryEntry",
    "RegistryFile",
    "RegistryLoadError",
    "audit_registry_file",
    "load_registry_dir",
    "parse_disposition",
]
