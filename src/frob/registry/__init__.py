# frob:ticket T-0591
# frob:waive TEST003 reason="unit-tested exhaustively via its consuming gates (test_registry_models.py, test_registry_exhaustiveness.py, ...); no CLI/subprocess integration entrypoint exists for this internal model package"  # noqa: E501
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
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/registry/__init__.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

from frob.registry._corpus import CorpusError, append_entry, format_entry_block
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
from frob.registry._staleness import missing_gate_rule_ids, sync_gate_rule_entries

__all__ = [
    "CorpusError",
    "Disposition",
    "DispositionKind",
    "RegistryAudit",
    "RegistryEntry",
    "RegistryFile",
    "RegistryLoadError",
    "append_entry",
    "audit_registry_file",
    "format_entry_block",
    "load_registry_dir",
    "missing_gate_rule_ids",
    "parse_disposition",
    "sync_gate_rule_entries",
]
