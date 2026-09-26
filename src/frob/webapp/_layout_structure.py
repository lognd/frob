"""LAYOUT gate substrate (docs/modules/webapp-layout-structure.md, T-5767):
the `frob.webapp._layout_*` hook module `frob.gates._layout_gate` discovers
via the same "first leaf of the family owns the one discovery edit"
`pkgutil` pattern `_a11y_gate.py` already established for the A11Y family
(T-5323) -- this is that family's first (and, at this leaf, only) hook.

# frob:ticket T-5767

Unlike A11Y's hooks (which walk parsed HTML/JSX source trees), a LAYOUT
hook walks crunk's gallery manifest (`frob.webapp._gallery_schema`,
T-5764's vendored schema) -- the gate module hands this module one
already-loaded `GalleryManifest` per tracked manifest file, not a parsed
source tree.

RULES (this leaf's own acceptance criteria):
  LAYOUT001 "unreviewed" -- `GalleryEntry.verdict is None`: nobody has
    ever signed off on this component/layout's current render set.
  LAYOUT002 "stale review" -- the manifest's recorded `source_hash`
    no longer matches a freshly recomputed hash of the entry's current
    source file (`frob.webapp._gallery_schema.entry_is_stale`, the
    owner-decreed byte-hash staleness rule, CRUNK-GALLERY-TREE.md
    section 5 Q3): a verdict exists but the component changed since.
  LAYOUT003 "render-exists" -- `GalleryEntry.artifacts == ()`: the
    entry has no declared render artifacts at all, so there is nothing
    a reviewer could have looked at even if `verdict` were set.

KNOWN LIMITATION (fixture props not yet threaded through): crunk's own
`source_hash` is `sha256(source_bytes + fixture_props_bytes)`
(`compute_source_hash`, T-5764's module docstring) -- this leaf recomputes
over `source_bytes` alone (`fixture_props_bytes=b""`), because frob has
no channel to an entry's declared fixture props yet. An entry with real
(non-empty) fixture props will therefore always compare as LAYOUT002-stale
here, even when only its source changed correctly-and-was-re-reviewed.
Threading fixture props through is explicitly out of this leaf's scope
(F-3's "webapp families accept catalog-render input" follow-on epic is
the natural home for it) -- `frob:todo T-5767` on `_recompute_source_hash`
below tracks it, not a bare TODO.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from frob.findings import Severity, Violation
from frob.logging import get_logger
from frob.webapp._gallery_schema import GalleryEntry, GalleryManifest, entry_is_stale

_log = get_logger(__name__)

__all__ = ["layout_findings"]

# frob:doc docs/modules/webapp-layout-structure.md#rule-ids
LAYOUT001_UNREVIEWED = "LAYOUT001"
LAYOUT002_STALE_REVIEW = "LAYOUT002"
LAYOUT003_RENDER_MISSING = "LAYOUT003"


# frob:doc docs/modules/webapp-layout-structure.md#staleness-recompute-known-limitation
# tests/unit/test_layout_gate.py::test_recompute_source_hash_matches_props_less_compute_source_hash  # noqa: E501
def _recompute_source_hash(root: Path, entry: GalleryEntry) -> str | None:
    """Sha256 hex digest of the entry's current source file bytes alone
    (`fixture_props_bytes=b""`, this module's own KNOWN LIMITATION,
    above) -- `None` if the source file cannot be read (missing, not a
    file, OS error), which `layout_findings` treats as "cannot judge
    staleness", not as a mismatch.

    frob:todo T-5767 thread real fixture-props bytes through once a
    channel for them exists (see this module's own docstring)."""
    source_path = root / entry.source_path
    try:
        source_bytes = source_path.read_bytes()
    except OSError as exc:
        _log.debug(
            "layout_structure: cannot read source for staleness check "
            "component_id=%s path=%s error=%s",
            entry.component_id,
            source_path,
            exc,
        )
        return None
    digest = hashlib.sha256(source_bytes + b"").hexdigest()
    _log.debug(
        "layout_structure: recomputed source hash component_id=%s digest=%s",
        entry.component_id,
        digest,
    )
    return digest


def _entry_findings(
    entry: GalleryEntry, manifest_path: str, root: Path
) -> tuple[Violation, ...]:
    """Every LAYOUT001-003 finding for one `GalleryEntry` -- `manifest_path`
    (the manifest file's root-relative path) is the `Violation.file` every
    finding here is filed against, since a manifest entry has no single
    source line of its own the way a parsed-tree finding does."""
    violations: list[Violation] = []

    if entry.verdict is None:
        violations.append(
            Violation(
                rule=LAYOUT001_UNREVIEWED,
                severity=Severity.WARN,
                file=manifest_path,
                line=1,
                message=(
                    f"{LAYOUT001_UNREVIEWED}: {manifest_path} entry "
                    f"{entry.component_id!r} has no recorded verdict "
                    "(never reviewed) -- run crunk's gallery triage UI "
                    "and record an approve/reject verdict"
                ),
            )
        )

    current_hash = _recompute_source_hash(root, entry)
    if current_hash is not None and entry_is_stale(entry, current_hash):
        violations.append(
            Violation(
                rule=LAYOUT002_STALE_REVIEW,
                severity=Severity.WARN,
                file=manifest_path,
                line=1,
                message=(
                    f"{LAYOUT002_STALE_REVIEW}: {manifest_path} entry "
                    f"{entry.component_id!r}'s recorded source_hash no "
                    "longer matches its current source file -- the "
                    "component changed since its last review; re-run "
                    "crunk's gallery pipeline and re-review"
                ),
            )
        )

    if not entry.artifacts:
        violations.append(
            Violation(
                rule=LAYOUT003_RENDER_MISSING,
                severity=Severity.WARN,
                file=manifest_path,
                line=1,
                message=(
                    f"{LAYOUT003_RENDER_MISSING}: {manifest_path} entry "
                    f"{entry.component_id!r} has no render artifacts -- "
                    "nothing has been rendered for review yet; run "
                    "crunk's gallery render step"
                ),
            )
        )

    return tuple(violations)


# frob:doc docs/modules/webapp-layout-structure.md#layout_findings
def layout_findings(
    manifest: GalleryManifest, manifest_path: str, root: Path
) -> tuple[Violation, ...]:
    """LAYOUT001-003 over every entry in one already-loaded
    `GalleryManifest` (the `frob.gates._layout_gate` hook shape,
    T-5767): the hook this leaf's gate discovery calls once per tracked
    manifest file. `manifest_path` is the manifest's root-relative path
    (every returned `Violation.file`); `root` locates each entry's
    `source_path` for `_recompute_source_hash`."""
    violations: list[Violation] = []
    for entry in manifest.entries:
        violations.extend(_entry_findings(entry, manifest_path, root))
    _log.info(
        "layout_structure: manifest=%s entries=%d violations=%d",
        manifest_path,
        len(manifest.entries),
        len(violations),
    )
    return tuple(violations)
