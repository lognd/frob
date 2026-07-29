"""T-0351 declared-surface join: which files a loaded strata design already
`carries` std.pii categories or Secret-clearance for, so a real declaration
discharges a PII010/SEC110 finding outright instead of needing a waiver
(T-1076 split of `frob.gates._pii_structural`)."""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/gates/_pii_structural/_declared_surface.py's exclusivity-vocabulary hit is \
# source-level design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim -- carried from the \
# pre-T-1076-split monolith's identical file-level waiver"

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from frob.logging import get_logger
from frob.strata._code_binding import bind_code
from frob.strata._design_load import load_design_ids
from frob.strata._pii import node_pii_tags

_log = get_logger(__name__)


@dataclass(frozen=True)
class _DeclaredSurface:
    """T-0351: the per-file std.pii/std.secrets JOIN target -- which PII
    categories a code-bound strata `Node` already `carries` for a file, and
    whether a code-bound node for a file is a Secret-clearance node
    (`load_design_ids`'s existing "Secret-clearance node is the best-effort
    standing proxy for std.secrets" convention, `_design_load.py`'s
    `DesignIds.secrets` docstring -- reused here, not re-derived). A finding
    whose file already resolves to a matching declaration is DISCHARGED
    (no violation emitted) rather than merely waived -- the whole point of
    this ticket: a real declaration, not a bare `frob:waive`, is now a
    legitimate way to clear PII010/SEC110."""

    pii_categories: dict[str, frozenset[str]]
    secret_files: frozenset[str]

    def _has_pii(self, rel_path: str, category: str) -> bool:
        """Whether `rel_path`'s code-bound node already `carries` `category`."""
        return category in self.pii_categories.get(rel_path, frozenset())

    def _has_secret(self, rel_path: str) -> bool:
        """Whether `rel_path` is code-bound to a Secret-clearance node."""
        return rel_path in self.secret_files


#: The empty join target -- every scan function defaults to this so a repo
#: with no strata design directory (or no matching bindings) behaves
#: exactly as before T-0351 (every PII010/SEC110 site still fires,
#: waiver-only discharge).
_EMPTY_DECLARED_SURFACE = _DeclaredSurface(pii_categories={}, secret_files=frozenset())


# frob:tests tests/test_pii_structural_gate.py::TestDeclaredSurfaceJoin.test_pii010_discharged_by_matching_carries_tag  # noqa: E501
def _load_declared_surface(root: Path) -> _DeclaredSurface:
    """Load every `.strata` design file under `root` (`load_design_ids`,
    the SAME loader `sys_gate` already uses -- no second design-loading
    path) and join each file's tier-2 code-binding owner node
    (`bind_code`) to that node's `carries` PII tags (`node_pii_tags`) and
    Secret-clearance status (T-0351). A repo with no design directory, or
    whose design fails to load/bind, degrades to `_EMPTY_DECLARED_SURFACE`
    (never a crash -- gates degrade, they don't fail closed on a missing
    optional feature)."""
    design_ids = load_design_ids(root)
    pii_categories: dict[str, set[str]] = {}
    secret_files: set[str] = set()
    for model in design_ids.models:
        bound = bind_code(model, root)
        if bound.is_err:
            _log.warning(
                "_load_declared_surface: code binding ambiguous, skipping a model: %s",
                bound.danger_err,
            )
            continue
        nodes_by_id = {node.id: node for node in model.nodes}
        for rel_path, node_id in bound.danger_ok.owner.items():
            node = nodes_by_id.get(node_id)
            if node is None:
                continue
            for tag in node_pii_tags(node):
                category = tag.split(".", 1)[0]
                pii_categories.setdefault(rel_path, set()).add(category)
            if node.clearance == "Secret":
                secret_files.add(rel_path)
    _log.info(
        "_load_declared_surface: %d file(s) with declared PII categories, "
        "%d file(s) code-bound to a Secret-clearance node",
        len(pii_categories),
        len(secret_files),
    )
    return _DeclaredSurface(
        pii_categories={path: frozenset(cats) for path, cats in pii_categories.items()},
        secret_files=frozenset(secret_files),
    )
