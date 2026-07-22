"""Shared hash helper for the legacy Type-1/Type-2 dup scan.

Raw node traversal (`child_by_field`/`node_text`) now lives in `frob.lang`
(see `frob.lang.child_by_field`/`frob.lang.node_text`) so it is shared with
`frob.arch` instead of duplicated here; only the dup-specific body digest
stays local.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/dup/_legacy_common.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

# frob:waive REF002 reason="private helper imported only by its sibling aggregator frob.dup._legacy; a single inbound anchor is intentional for a legacy-scan leaf module, T-0450"  # noqa: E501

from __future__ import annotations

import hashlib


def _sha16(s: str) -> str:
    """First 16 hex chars of sha256(s) -- the fragment/body fingerprint."""
    return hashlib.sha256(s.encode()).hexdigest()[:16]
