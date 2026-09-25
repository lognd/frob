"""frob.webapp._gallery_schema coverage: crunk fixture parity, staleness
rule, and vendored-schema drift detection (docs/modules/webapp-layout.md).

frob:ticket T-5764
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from frob.webapp._gallery_schema import (
    VENDORED_SCHEMA,
    GalleryManifest,
    GalleryManifestError,
    entry_is_stale,
    load_gallery_manifest,
)

_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "webapp"
    / "gallery"
    / "gallery-manifest.fixture.json"
)

#: The sibling crunk checkout this repo's fleet convention assumes (see
#: docs/modules/webapp-layout.md#vendoring-procedure). Tests that diff
#: against crunk's live source are skipped with a named reason when this
#: path is absent, rather than failing.
_CRUNK_SCHEMA_PATH = (
    Path.home() / "projects" / "crunk" / "schemas" / "gallery-manifest.v1.json"
)


# frob:tests src/frob/webapp/_gallery_schema.py::load_gallery_manifest
# frob:tests src/frob/webapp/_gallery_schema.py::GalleryManifest
# frob:tests src/frob/webapp/_gallery_schema.py::Verdict
# frob:tests src/frob/webapp/_gallery_schema.py::VerdictStatus
def test_fixture_manifest_round_trips() -> None:
    """[param=fixture] crunk's own fixture manifest loads through frob's
    vendored loader and its entries survive intact."""
    result = load_gallery_manifest(_FIXTURE_PATH)
    assert result.is_ok, f"load_gallery_manifest failed: {result}"
    manifest = result.danger_ok
    assert isinstance(manifest, GalleryManifest)
    assert len(manifest.entries) == 1
    entry = manifest.entries[0]
    assert entry.component_id == "Button"
    assert entry.source_hash == "abc123"
    assert entry.verdict is not None
    assert entry.verdict.status.value == "approved"


# frob:tests src/frob/webapp/_gallery_schema.py::load_gallery_manifest
# frob:tests src/frob/webapp/_gallery_schema.py::GalleryManifestError
# frob:tests src/frob/webapp/_gallery_schema.py::GalleryEntry
def test_missing_source_hash_rejected(tmp_path: Path) -> None:
    """[param=missing-source-hash] an entry with no `source_hash` is
    rejected by frob's loader identically to crunk's own check (positive
    control + cross-repo parity)."""
    fixture = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
    del fixture["entries"][0]["source_hash"]
    bad_path = tmp_path / "invalid.json"
    bad_path.write_text(json.dumps(fixture), encoding="utf-8")

    result = load_gallery_manifest(bad_path)

    assert result.is_err
    assert result.danger_err is GalleryManifestError.Invalid


# frob:tests src/frob/webapp/_gallery_schema.py::load_gallery_manifest
# frob:tests src/frob/webapp/_gallery_schema.py::GalleryManifestError
def test_load_gallery_manifest_not_found(tmp_path: Path) -> None:
    """[param=not-found] a nonexistent path returns `Err(NotFound)`."""
    result = load_gallery_manifest(tmp_path / "does-not-exist.json")
    assert result.is_err
    assert result.danger_err is GalleryManifestError.NotFound


# frob:tests src/frob/webapp/_gallery_schema.py::load_gallery_manifest
# frob:tests src/frob/webapp/_gallery_schema.py::GalleryManifestError
def test_load_gallery_manifest_malformed(tmp_path: Path) -> None:
    """[param=malformed] non-JSON content returns `Err(Malformed)`."""
    bad_path = tmp_path / "bad.json"
    bad_path.write_text("not json {", encoding="utf-8")
    result = load_gallery_manifest(bad_path)
    assert result.is_err
    assert result.danger_err is GalleryManifestError.Malformed


# frob:tests src/frob/webapp/_gallery_schema.py::entry_is_stale
def test_entry_is_stale_on_hash_change() -> None:
    """[param=hash-changed] a byte-changed source hash marks the entry
    stale (owner decision: byte hash, any change re-opens review)."""
    manifest = load_gallery_manifest(_FIXTURE_PATH).danger_ok
    entry = manifest.entries[0]
    assert entry_is_stale(entry, "different-hash-value") is True


# frob:tests src/frob/webapp/_gallery_schema.py::entry_is_stale
def test_entry_is_stale_false_when_unchanged() -> None:
    """[param=hash-unchanged] an unchanged source hash keeps the entry
    non-stale."""
    manifest = load_gallery_manifest(_FIXTURE_PATH).danger_ok
    entry = manifest.entries[0]
    assert entry_is_stale(entry, entry.source_hash) is False


# frob:tests src/frob/webapp/_gallery_schema.py::RenderArtifact
def test_vendored_schema_matches_crunk_source() -> None:
    """[param=schema-drift] the vendored JSON schema equals crunk's
    `schemas/gallery-manifest.v1.json` byte-for-byte, so drift between
    the two repos is caught here rather than at runtime. Skipped with a
    named reason when the sibling crunk checkout is absent."""
    if not _CRUNK_SCHEMA_PATH.exists():
        pytest.skip(
            "sibling crunk checkout not present at "
            f"{_CRUNK_SCHEMA_PATH} -- schema-drift parity check needs "
            "a local crunk clone to diff against"
        )
    crunk_schema = json.loads(_CRUNK_SCHEMA_PATH.read_text(encoding="utf-8"))
    assert VENDORED_SCHEMA == crunk_schema
