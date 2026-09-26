"""frob.gates._layout_gate / frob.webapp._layout_structure coverage:
LAYOUT001 (unreviewed), LAYOUT002 (stale review), LAYOUT003 (render-exists)
-- T-5767's own acceptance criteria plus the gate's discovery/scan wiring.

frob:ticket T-5767
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from frob.gates._layout_gate import layout_gate
from frob.webapp._gallery_schema import (
    EntryKind,
    GalleryEntry,
    GalleryManifest,
    RenderArtifact,
    RenderState,
    StateKind,
    Verdict,
    VerdictStatus,
)
from frob.webapp._layout_structure import (
    LAYOUT001_UNREVIEWED,
    LAYOUT002_STALE_REVIEW,
    LAYOUT003_RENDER_MISSING,
    _recompute_source_hash,
    layout_findings,
)

_SOURCE_BYTES = b"export const Button = () => <button />;\n"


def _make_entry(
    *,
    source_hash: str,
    verdict: Verdict | None = None,
    artifacts: tuple[RenderArtifact, ...] = (),
) -> GalleryEntry:
    """Build a minimal `GalleryEntry` for `Button.jsx` under a caller-owned
    fixture root, with the given `source_hash`/`verdict`/`artifacts`."""
    return GalleryEntry(
        component_id="Button",
        kind=EntryKind.COMPONENT,
        source_path=Path("Button.jsx"),
        source_hash=source_hash,
        states=(RenderState(kind=StateKind.EMPTY),),
        artifacts=artifacts,
        verdict=verdict,
    )


def _current_hash() -> str:
    """The hash `_recompute_source_hash` computes for `_SOURCE_BYTES`
    (props-less, this leaf's own documented limitation)."""
    return hashlib.sha256(_SOURCE_BYTES + b"").hexdigest()


# frob:tests src/frob/webapp/_layout_structure.py::_recompute_source_hash
def test_recompute_source_hash_matches_props_less_compute_source_hash(
    tmp_path: Path,
) -> None:
    """[param=recompute] `_recompute_source_hash` reads the entry's
    current source bytes and hashes them alone (props-less, the
    documented KNOWN LIMITATION)."""
    (tmp_path / "Button.jsx").write_bytes(_SOURCE_BYTES)
    entry = _make_entry(source_hash="irrelevant")

    digest = _recompute_source_hash(tmp_path, entry)

    assert digest == _current_hash()


# frob:tests src/frob/webapp/_layout_structure.py::layout_findings
def test_unreviewed_entry_raises_layout001(tmp_path: Path) -> None:
    """[param=unreviewed] a `verdict=None` entry raises LAYOUT001."""
    (tmp_path / "Button.jsx").write_bytes(_SOURCE_BYTES)
    entry = _make_entry(source_hash=_current_hash(), verdict=None)
    manifest = GalleryManifest(
        generated_at=datetime.now(timezone.utc), tool_version="0.1.0", entries=(entry,)
    )

    violations = layout_findings(manifest, "gallery-manifest.v1.json", tmp_path)

    rules = {v.rule for v in violations}
    assert LAYOUT001_UNREVIEWED in rules


def test_stale_hash_raises_layout002(tmp_path: Path) -> None:
    """[param=stale-hash] a `source_hash` mismatch vs. current file
    content raises LAYOUT002 (this leaf's named positive control)."""
    (tmp_path / "Button.jsx").write_bytes(_SOURCE_BYTES)
    entry = _make_entry(
        source_hash="deadbeef-not-the-real-hash",
        verdict=Verdict(
            status=VerdictStatus.APPROVED,
            reviewer="logan@logandapp.com",
            timestamp=datetime.now(timezone.utc),
        ),
        artifacts=(
            RenderArtifact(
                path=Path("ci/Button.png"), state=RenderState(kind=StateKind.EMPTY)
            ),
        ),
    )
    manifest = GalleryManifest(
        generated_at=datetime.now(timezone.utc), tool_version="0.1.0", entries=(entry,)
    )

    violations = layout_findings(manifest, "gallery-manifest.v1.json", tmp_path)

    rules = {v.rule for v in violations}
    assert LAYOUT002_STALE_REVIEW in rules


def test_reviewed_current_entry_is_clean(tmp_path: Path) -> None:
    """[param=clean] a reviewed entry whose `source_hash` matches its
    current source file and carries artifacts raises nothing -- both
    LAYOUT001 and LAYOUT002 clear once the entry is genuinely current
    (this leaf's own acceptance criterion)."""
    (tmp_path / "Button.jsx").write_bytes(_SOURCE_BYTES)
    entry = _make_entry(
        source_hash=_current_hash(),
        verdict=Verdict(
            status=VerdictStatus.APPROVED,
            reviewer="logan@logandapp.com",
            timestamp=datetime.now(timezone.utc),
        ),
        artifacts=(
            RenderArtifact(
                path=Path("ci/Button.png"), state=RenderState(kind=StateKind.EMPTY)
            ),
        ),
    )
    manifest = GalleryManifest(
        generated_at=datetime.now(timezone.utc), tool_version="0.1.0", entries=(entry,)
    )

    violations = layout_findings(manifest, "gallery-manifest.v1.json", tmp_path)

    assert violations == ()


def test_missing_artifacts_raises_layout003(tmp_path: Path) -> None:
    """[param=render-missing] an entry with no render artifacts raises
    LAYOUT003, independent of its verdict/hash state."""
    (tmp_path / "Button.jsx").write_bytes(_SOURCE_BYTES)
    entry = _make_entry(
        source_hash=_current_hash(),
        verdict=Verdict(
            status=VerdictStatus.APPROVED,
            reviewer="logan@logandapp.com",
            timestamp=datetime.now(timezone.utc),
        ),
        artifacts=(),
    )
    manifest = GalleryManifest(
        generated_at=datetime.now(timezone.utc), tool_version="0.1.0", entries=(entry,)
    )

    violations = layout_findings(manifest, "gallery-manifest.v1.json", tmp_path)

    rules = {v.rule for v in violations}
    assert LAYOUT003_RENDER_MISSING in rules


def _git(*args: str, cwd: Path) -> None:
    """Run a `git` command in `cwd`, raising on failure -- test-only
    helper for the gate-level (tracked-file) tests below."""
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


# frob:tests src/frob/gates/_layout_gate.py::layout_gate
def test_gate_discovers_hook_and_scans_manifest(tmp_path: Path) -> None:
    """[param=gate-scan] `layout_gate` discovers the `_layout_structure`
    hook, loads a tracked `gallery-manifest.v1.json`, and returns its
    LAYOUT001/LAYOUT003 findings for an unreviewed, artifact-less entry."""
    (tmp_path / "Button.jsx").write_bytes(_SOURCE_BYTES)
    manifest_payload = {
        "schema_version": 1,
        "generated_at": "2026-09-24T00:00:00Z",
        "tool_version": "0.1.0",
        "entries": [
            {
                "component_id": "Button",
                "kind": "component",
                "source_path": "Button.jsx",
                "source_hash": "not-yet-reviewed",
            }
        ],
    }
    (tmp_path / "gallery-manifest.v1.json").write_text(
        json.dumps(manifest_payload), encoding="utf-8"
    )
    _git("init", "-q", cwd=tmp_path)
    _git("add", ".", cwd=tmp_path)

    violations = layout_gate(tmp_path)

    rules = {v.rule for v in violations}
    assert LAYOUT001_UNREVIEWED in rules
    assert LAYOUT003_RENDER_MISSING in rules


# frob:tests src/frob/gates/_layout_gate.py::layout_gate
def test_gate_returns_empty_with_no_manifest_files(tmp_path: Path) -> None:
    """[param=gate-no-manifest] a repo with no tracked
    `gallery-manifest*.json` file short-circuits to `()` -- never a
    silent crash, never a spurious finding."""
    _git("init", "-q", cwd=tmp_path)

    assert layout_gate(tmp_path) == ()
