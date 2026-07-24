"""Shared proof-against-code plumbing for the T-0331 reliability-obligation
family (`_reliability.py`'s REL2xx TIMEOUT/HEALTH, `_retry.py`'s REL22x
RETRY, `_circuit_breaker.py`'s REL23x CIRCUIT BREAKER, `_fallback.py`'s
REL24x FALLBACK).

Every one of these obligations follows the SAME two-rule shape: "missing
declaration" (deny-by-default) and "declared but unproven" (T-0331's
PROVABILITY CONSTRAINT: bare declaration never discharges an obligation,
the code `bind_code` binds to a node must carry a real matching token).
`_reliability.py` (T-0640, the structural template this whole family
copies) built its own private `_owner_index`/`_node_has_bound_code`/
`_files_evidence_timeout` trio inline; this module is that trio's ONE
shared home (charter: no duplication) now that a second obligation
(T-0641 RETRY) needs the identical proof-against-code mechanism against a
DIFFERENT token regex. `_reliability.py` itself is left as-is (its own
copies still work; T-0640 already shipped and re-deriving its internals
mid-family is out of scope for T-0641) -- new REL2xx modules import from
here instead of re-copying the pattern a third/fourth/fifth time.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: this file's \
# 'only' hits are source-level design-rationale/scope-cut prose (docstrings \
# describing already-implemented internal behavior, verifiable by reading \
# the code they annotate) rather than a separate cross-module contract \
# needing its own tracked invariant, the same disposition _reliability.py's \
# own identical waiver already uses for the identical reason"

from __future__ import annotations

import re
from pathlib import Path

from frob.logging import get_logger

from ._code_binding import CodeBinding

_log = get_logger(__name__)


# frob:doc docs/strata/reliability.md#shared-proof-against-code-plumbing-t-0641
# frob:ticket T-0641
# frob:tests tests/unit/strata/test_obligation_proof.py::TestOwnerIndex.test_inverts_file_to_node_map  # noqa: E501
def owner_index(owner: dict[str, str]) -> dict[str, list[str]]:
    """`CodeBinding.owner` (file -> node id) inverted to node id -> its
    bound files, in deterministic path order -- the per-node lookup every
    proof-against-code rule needs (`_reliability.py::_owner_index`'s exact
    shape, promoted here so RETRY/CIRCUIT-BREAKER/FALLBACK share it rather
    than re-deriving it)."""
    by_node: dict[str, list[str]] = {}
    for rel, node_id in sorted(owner.items()):
        by_node.setdefault(node_id, []).append(rel)
    return by_node


# frob:doc docs/strata/reliability.md#shared-proof-against-code-plumbing-t-0641
# frob:ticket T-0641
# frob:tests tests/unit/strata/test_obligation_proof.py::TestNodeHasBoundCode.test_true_when_files_present  # noqa: E501
def node_has_bound_code(node_id: str, owner_by_node: dict[str, list[str]]) -> bool:
    """Whether `node_id` owns at least one real source file per `bind_code`
    -- the "can this rule even check?" gate every proof-against-code rule
    needs before it can honestly claim proof (uncheckable is silent, never
    a guessed-at violation, the ceiling `_reliability.py`'s module
    docstring establishes)."""
    return bool(owner_by_node.get(node_id))


# frob:doc docs/strata/reliability.md#shared-proof-against-code-plumbing-t-0641
# frob:ticket T-0641
# frob:tests tests/unit/strata/test_obligation_proof.py::TestFilesEvidenceToken.test_matches_a_real_token  # noqa: E501
def files_evidence_token(
    paths: list[str], root: Path, pattern: re.Pattern[str]
) -> bool:
    """Whether any of `paths` (root-relative) contains a real token
    matching `pattern` -- the proof-against-code body every REL2xx
    obligation rule shares, parameterized on the caller's own regex
    (`_reliability.py::_files_evidence_timeout`'s exact shape, generalized
    over the token). Unreadable files are skipped, never treated as proof
    (fails closed, consistent with every other strata code-binding
    reader's error handling)."""
    for rel in paths:
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except OSError:
            _log.warning("obligation_proof: could not read bound file %s", rel)
            continue
        if pattern.search(text):
            return True
    return False


# frob:doc docs/strata/reliability.md#shared-proof-against-code-plumbing-t-0641
# frob:ticket T-0641
# frob:tests tests/unit/strata/test_obligation_proof.py::TestBoundEndpoints.test_both_endpoints_bound_src_first  # noqa: E501
def bound_endpoints(
    flow_src: str, flow_dst: str, owner_by_node: dict[str, list[str]]
) -> list[str]:
    """The subset of a flow's endpoints (`src`, `dst`, deduped, src-first
    for stable reporting) that own at least one bound file (T-0758's
    proof-anchoring precedent: check whichever endpoint(s) actually have
    code, not only `src` -- `_reliability.py::_bound_endpoints`'s exact
    shape)."""
    endpoints = [flow_src] if flow_src == flow_dst else [flow_src, flow_dst]
    return [node for node in endpoints if node_has_bound_code(node, owner_by_node)]


__all__ = [
    "CodeBinding",
    "bound_endpoints",
    "files_evidence_token",
    "node_has_bound_code",
    "owner_index",
]
