"""Vendored copy of crunk's gallery manifest JSON schema
(docs/modules/webapp-layout.md#manifest) for frob-side validation without
importing crunk.

# frob:ticket T-5764

WHY VENDORED, NOT IMPORTED: `webapp` is a leaf layer (`[arch.layering]`,
`frob.toml`) and frob does not depend on crunk as a package at all --
crunk is a sibling tool frob's future LAYOUT gate (T-5747 story, leaf
F-2) shells out to or reads artifacts from, never imports. This module
is a byte-for-byte copy of crunk's `schemas/gallery-manifest.v1.json`
(see `_VENDORED_FROM_COMMIT`/`_VENDORED_SCHEMA_VERSION` below) plus a
small pydantic model that mirrors `crunk.gallery.manifest.Manifest`
closely enough for frob's own reads -- frob never writes a manifest.

VENDORING PROCEDURE (repeat whenever crunk's schema changes): copy
`crunk/schemas/gallery-manifest.v1.json` verbatim into
`_VENDORED_SCHEMA_JSON` below, update `_VENDORED_FROM_COMMIT` to the
crunk commit hash it came from, update `_VENDORED_SCHEMA_VERSION` if
crunk bumped `SCHEMA_VERSION`, then re-run this module's mirror model
by hand against `crunk.gallery.manifest`'s field list and re-run
`tests/unit/test_webapp_gallery_schema.py::test_vendored_schema_matches_crunk_source`
(skipped without a sibling crunk checkout) to confirm.

STALENESS RULE (owner decision, crunk's CRUNK-GALLERY-TREE.md section 5,
Q3, mirrored in docs/modules/webapp-layout.md#staleness): a
`GalleryEntry.verdict` expires on ANY byte change of the component's
source or its fixture props -- `entry_is_stale` below implements this
as a plain string comparison against a hash the caller recomputed with
crunk's own `compute_source_hash` convention (sha256 over
`source_bytes + fixture_props_bytes`); this module does not recompute
the hash itself, it only compares.
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ValidationError, model_validator
from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.logging import get_logger

_log = get_logger(__name__)

#: The crunk commit `gallery-manifest.v1.json` was vendored from
#: (docs/modules/webapp-layout.md#vendoring-procedure). Update this
#: whenever `_VENDORED_SCHEMA_JSON` is refreshed.
_VENDORED_FROM_COMMIT = "2c8758446a8c28d4e695d63c83ef6daa0ac374fb"

#: crunk's `Manifest.schema_version` this vendored copy matches
#: (`crunk.gallery.manifest.SCHEMA_VERSION` at `_VENDORED_FROM_COMMIT`).
_VENDORED_SCHEMA_VERSION = 1

#: Byte-for-byte copy of crunk's `schemas/gallery-manifest.v1.json`,
#: parsed once at import time. Kept as a JSON string (not a dict
#: literal) so a diff against crunk's file is a straight text compare.
_VENDORED_SCHEMA_JSON = (
    "{\n"
    '  "$defs": {\n'
    '    "EntryKind": {\n'
    '      "description": "Which org bucket family (`crunk.ingest.models.Bucket`) a gal'
    'lery\\nentry was enumerated from: a single component or a whole layout.",\n'
    '      "enum": [\n'
    '        "component",\n'
    '        "layout"\n'
    "      ],\n"
    '      "title": "EntryKind",\n'
    '      "type": "string"\n'
    "    },\n"
    '    "GalleryEntry": {\n'
    '      "additionalProperties": false,\n'
    '      "description": "One component or layout\'s full gallery record: identity, th'
    "e\\ncontent hash review is pinned to, its declared states, any CI render\\nartifac"
    'ts, and the current verdict (`None` until first review).",\n'
    '      "properties": {\n'
    '        "artifacts": {\n'
    '          "default": [],\n'
    '          "items": {\n'
    '            "$ref": "#/$defs/RenderArtifact"\n'
    "          },\n"
    '          "title": "Artifacts",\n'
    '          "type": "array"\n'
    "        },\n"
    '        "component_id": {\n'
    '          "title": "Component Id",\n'
    '          "type": "string"\n'
    "        },\n"
    '        "kind": {\n'
    '          "$ref": "#/$defs/EntryKind"\n'
    "        },\n"
    '        "source_hash": {\n'
    '          "title": "Source Hash",\n'
    '          "type": "string"\n'
    "        },\n"
    '        "source_path": {\n'
    '          "format": "path",\n'
    '          "title": "Source Path",\n'
    '          "type": "string"\n'
    "        },\n"
    '        "states": {\n'
    '          "default": [],\n'
    '          "items": {\n'
    '            "$ref": "#/$defs/RenderState"\n'
    "          },\n"
    '          "title": "States",\n'
    '          "type": "array"\n'
    "        },\n"
    '        "verdict": {\n'
    '          "anyOf": [\n'
    "            {\n"
    '              "$ref": "#/$defs/Verdict"\n'
    "            },\n"
    "            {\n"
    '              "type": "null"\n'
    "            }\n"
    "          ],\n"
    '          "default": null\n'
    "        }\n"
    "      },\n"
    '      "required": [\n'
    '        "component_id",\n'
    '        "kind",\n'
    '        "source_path",\n'
    '        "source_hash"\n'
    "      ],\n"
    '      "title": "GalleryEntry",\n'
    '      "type": "object"\n'
    "    },\n"
    '    "RenderArtifact": {\n'
    '      "additionalProperties": false,\n'
    '      "description": "One reference to a rendered screenshot: a CI-only artifact p'
    "ath.\\n\\nOwner decision (CRUNK-GALLERY-TREE.md section 5, Q2): screenshots are\\n"
    "never committed to the repo; the manifest carries only this path\\nreference, prod"
    "uced fresh by CI each run (C-4/C-5's job).\",\n"
    '      "properties": {\n'
    '        "path": {\n'
    '          "format": "path",\n'
    '          "title": "Path",\n'
    '          "type": "string"\n'
    "        },\n"
    '        "state": {\n'
    '          "$ref": "#/$defs/RenderState"\n'
    "        }\n"
    "      },\n"
    '      "required": [\n'
    '        "path",\n'
    '        "state"\n'
    "      ],\n"
    '      "title": "RenderArtifact",\n'
    '      "type": "object"\n'
    "    },\n"
    '    "RenderState": {\n'
    '      "additionalProperties": false,\n'
    '      "description": "One declared state/variant an entry renders under (C-2\'s co'
    "ntract).\\n\\n`breakpoint` is required exactly when `kind` is `BREAKPOINT` (the\\n"
    "named breakpoint being rendered at) and forbidden otherwise;\\nenforced by `Manife"
    "st`'s pydantic validation, not by convention.\",\n"
    '      "properties": {\n'
    '        "breakpoint": {\n'
    '          "anyOf": [\n'
    "            {\n"
    '              "type": "string"\n'
    "            },\n"
    "            {\n"
    '              "type": "null"\n'
    "            }\n"
    "          ],\n"
    '          "default": null,\n'
    '          "title": "Breakpoint"\n'
    "        },\n"
    '        "kind": {\n'
    '          "$ref": "#/$defs/StateKind"\n'
    "        }\n"
    "      },\n"
    '      "required": [\n'
    '        "kind"\n'
    "      ],\n"
    '      "title": "RenderState",\n'
    '      "type": "object"\n'
    "    },\n"
    '    "StateKind": {\n'
    '      "description": "One declared render state/variant dimension for a gallery en'
    "try.\\n\\nFixed states are content/locale/theme conditions a component must be\\nr"
    "endered under; `BREAKPOINT` is the one parameterized kind, carrying\\na `RenderSta"
    'te.breakpoint` name (e.g. \\"sm\\"/\\"md\\"/\\"lg\\") alongside it.",\n'
    '      "enum": [\n'
    '        "empty",\n'
    '        "loading",\n'
    '        "error",\n'
    '        "long-text",\n'
    '        "rtl",\n'
    '        "dark",\n'
    '        "breakpoint"\n'
    "      ],\n"
    '      "title": "StateKind",\n'
    '      "type": "string"\n'
    "    },\n"
    '    "Verdict": {\n'
    '      "additionalProperties": false,\n'
    '      "description": "A recorded review decision (C-3\'s triage UI writes these).'
    '\\n\\nAbsent on a `GalleryEntry` (`verdict=None`) means \\"never reviewed\\";\\npr'
    "esent-but-stale (per `source_hash` staleness rule above) is a\\nfrob LAYOUT002 con"
    "dition, not represented in this model -- staleness\\nis a comparison the *consumer"
    '* makes against the current source.",\n'
    '      "properties": {\n'
    '        "note": {\n'
    '          "anyOf": [\n'
    "            {\n"
    '              "type": "string"\n'
    "            },\n"
    "            {\n"
    '              "type": "null"\n'
    "            }\n"
    "          ],\n"
    '          "default": null,\n'
    '          "title": "Note"\n'
    "        },\n"
    '        "reviewer": {\n'
    '          "title": "Reviewer",\n'
    '          "type": "string"\n'
    "        },\n"
    '        "status": {\n'
    '          "$ref": "#/$defs/VerdictStatus"\n'
    "        },\n"
    '        "timestamp": {\n'
    '          "format": "date-time",\n'
    '          "title": "Timestamp",\n'
    '          "type": "string"\n'
    "        }\n"
    "      },\n"
    '      "required": [\n'
    '        "status",\n'
    '        "reviewer",\n'
    '        "timestamp"\n'
    "      ],\n"
    '      "title": "Verdict",\n'
    '      "type": "object"\n'
    "    },\n"
    '    "VerdictStatus": {\n'
    '      "description": "The reviewer\'s decision on one gallery entry\'s current ren'
    'der set.",\n'
    '      "enum": [\n'
    '        "approved",\n'
    '        "rejected"\n'
    "      ],\n"
    '      "title": "VerdictStatus",\n'
    '      "type": "string"\n'
    "    }\n"
    "  },\n"
    '  "additionalProperties": false,\n'
    '  "description": "The full versioned gallery manifest: the one committed JSON\\nar'
    "tifact `crunk gallery` writes and frob's LAYOUT gate reads.\\n\\n`schema_version` "
    "is pinned to `SCHEMA_VERSION` (bumping the constant\\nis how a v2 gets introduced)"
    "; `generated_at`/`tool_version` record\\nprovenance so a stale manifest is disting"
    'uishable from a fresh one\\nwith no entries.",\n'
    '  "properties": {\n'
    '    "entries": {\n'
    '      "default": [],\n'
    '      "items": {\n'
    '        "$ref": "#/$defs/GalleryEntry"\n'
    "      },\n"
    '      "title": "Entries",\n'
    '      "type": "array"\n'
    "    },\n"
    '    "generated_at": {\n'
    '      "format": "date-time",\n'
    '      "title": "Generated At",\n'
    '      "type": "string"\n'
    "    },\n"
    '    "schema_version": {\n'
    '      "default": 1,\n'
    '      "title": "Schema Version",\n'
    '      "type": "integer"\n'
    "    },\n"
    '    "tool_version": {\n'
    '      "title": "Tool Version",\n'
    '      "type": "string"\n'
    "    }\n"
    "  },\n"
    '  "required": [\n'
    '    "generated_at",\n'
    '    "tool_version"\n'
    "  ],\n"
    '  "title": "Manifest",\n'
    '  "type": "object"\n'
    "}\n"
)

#: Parsed once at import time; used by tests to diff against crunk's live file.
VENDORED_SCHEMA: dict = json.loads(_VENDORED_SCHEMA_JSON)


# frob:doc docs/modules/webapp-layout.md#manifest
# frob:tests tests/unit/test_webapp_gallery_schema.py::test_entry_kind_values
class EntryKind(str, Enum):
    """Mirrors `crunk.gallery.manifest.EntryKind`: which org bucket family
    a gallery entry was enumerated from, a component or a whole layout."""

    COMPONENT = "component"
    LAYOUT = "layout"


# frob:doc docs/modules/webapp-layout.md#manifest
# frob:tests tests/unit/test_webapp_gallery_schema.py::test_breakpoint_requires_name
class StateKind(str, Enum):
    """Mirrors `crunk.gallery.manifest.StateKind`: one declared render
    state/variant dimension for a gallery entry."""

    EMPTY = "empty"
    LOADING = "loading"
    ERROR = "error"
    LONG_TEXT = "long-text"
    RTL = "rtl"
    DARK = "dark"
    BREAKPOINT = "breakpoint"


# frob:doc docs/modules/webapp-layout.md#manifest
# frob:tests tests/unit/test_webapp_gallery_schema.py::test_breakpoint_requires_name
class RenderState(BaseModel):
    """Mirrors `crunk.gallery.manifest.RenderState`: one declared
    state/variant an entry renders under; `breakpoint` is required
    exactly when `kind` is `BREAKPOINT` and forbidden otherwise."""

    model_config = {"frozen": True, "extra": "forbid"}

    kind: StateKind
    breakpoint: str | None = None

    @model_validator(mode="after")
    def _breakpoint_shape(self) -> "RenderState":
        """Reject a `breakpoint` on a non-BREAKPOINT kind, or a missing
        one on a BREAKPOINT kind -- mirrors crunk's INV-GAL-01."""
        has_bp = self.breakpoint is not None
        if has_bp != (self.kind is StateKind.BREAKPOINT):
            raise ValueError(
                "RenderState.breakpoint must be set iff kind is BREAKPOINT"
            )
        return self


# frob:doc docs/modules/webapp-layout.md#manifest
# frob:tests \
# tests/unit/test_webapp_gallery_schema.py::test_vendored_schema_matches_crunk_source  # noqa: E501
class RenderArtifact(BaseModel):
    """Mirrors `crunk.gallery.manifest.RenderArtifact`: one reference to
    a rendered screenshot, never committed (CI-only artifact path)."""

    model_config = {"frozen": True, "extra": "forbid"}

    path: Path
    state: RenderState


# frob:doc docs/modules/webapp-layout.md#manifest
# frob:tests tests/unit/test_webapp_gallery_schema.py::test_fixture_manifest_round_trips
class VerdictStatus(str, Enum):
    """Mirrors `crunk.gallery.manifest.VerdictStatus`: the reviewer's
    decision on one gallery entry's current render set."""

    APPROVED = "approved"
    REJECTED = "rejected"


# frob:doc docs/modules/webapp-layout.md#manifest
# frob:tests tests/unit/test_webapp_gallery_schema.py::test_fixture_manifest_round_trips
class Verdict(BaseModel):
    """Mirrors `crunk.gallery.manifest.Verdict`: a recorded review
    decision; absent (`GalleryEntry.verdict=None`) means never reviewed."""

    model_config = {"frozen": True, "extra": "forbid"}

    status: VerdictStatus
    reviewer: str
    timestamp: datetime
    note: str | None = None


# frob:doc docs/modules/webapp-layout.md#manifest
# frob:tests tests/unit/test_webapp_gallery_schema.py::test_missing_source_hash_rejected
class GalleryEntry(BaseModel):
    """Mirrors `crunk.gallery.manifest.GalleryEntry`: one component or
    layout's full gallery record. `source_hash` is required -- a
    manifest entry missing it fails validation (this module's named
    positive control, matching crunk's own check)."""

    model_config = {"frozen": True, "extra": "forbid"}

    component_id: str
    kind: EntryKind
    source_path: Path
    source_hash: str
    states: tuple[RenderState, ...] = ()
    artifacts: tuple[RenderArtifact, ...] = ()
    verdict: Verdict | None = None


# frob:doc docs/modules/webapp-layout.md#manifest
# frob:tests tests/unit/test_webapp_gallery_schema.py::test_fixture_manifest_round_trips
class GalleryManifest(BaseModel):
    """Mirrors `crunk.gallery.manifest.Manifest`: the full versioned
    gallery manifest frob's future LAYOUT gate (T-5747 story, leaf F-2)
    reads. `schema_version` is checked against `_VENDORED_SCHEMA_VERSION`
    by `load_gallery_manifest`, not by this model alone."""

    model_config = {"frozen": True, "extra": "forbid"}

    schema_version: int = _VENDORED_SCHEMA_VERSION
    generated_at: datetime
    tool_version: str
    entries: tuple[GalleryEntry, ...] = ()


# frob:doc docs/modules/webapp-layout.md#errors
# frob:tests \
# tests/unit/test_webapp_gallery_schema.py::test_load_gallery_manifest_not_found  # noqa: E501
# frob:tests \
# tests/unit/test_webapp_gallery_schema.py::test_load_gallery_manifest_malformed  # noqa: E501
# frob:tests tests/unit/test_webapp_gallery_schema.py::test_missing_source_hash_rejected
class GalleryManifestError(ErrorSet):
    """Failure values `load_gallery_manifest` can return."""

    NotFound = "manifest file does not exist at the stated path"
    Unreadable = "OS-level failure reading the manifest file"
    Malformed = "manifest file is not valid JSON"
    Invalid = "manifest JSON does not satisfy the vendored GalleryManifest schema"


# frob:doc docs/modules/webapp-layout.md#public-api
# frob:tests tests/unit/test_webapp_gallery_schema.py::test_fixture_manifest_round_trips
# frob:tests \
# tests/unit/test_webapp_gallery_schema.py::test_load_gallery_manifest_not_found  # noqa: E501
# frob:tests \
# tests/unit/test_webapp_gallery_schema.py::test_load_gallery_manifest_malformed  # noqa: E501
# frob:tests tests/unit/test_webapp_gallery_schema.py::test_missing_source_hash_rejected
def load_gallery_manifest(path: Path) -> Result[GalleryManifest, GalleryManifestError]:
    """Read and validate one `gallery-manifest.v1.json` file at `path`
    against frob's vendored mirror of crunk's schema (no crunk import)."""
    if not path.exists():
        _log.info("gallery manifest load reject: not found path=%s", path)
        return Err(GalleryManifestError.NotFound)

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        _log.info(
            "gallery manifest load reject: unreadable path=%s error=%s", path, exc
        )
        return Err(GalleryManifestError.Unreadable)

    try:
        manifest = GalleryManifest.model_validate_json(text)
    except ValidationError as exc:
        first = exc.errors()[0]
        if first["type"] == "json_invalid":
            _log.info(
                "gallery manifest load reject: malformed json path=%s error=%s",
                path,
                exc,
            )
            return Err(GalleryManifestError.Malformed)
        _log.info(
            "gallery manifest load reject: invalid schema path=%s error=%s", path, exc
        )
        return Err(GalleryManifestError.Invalid)

    _log.info(
        "gallery manifest loaded path=%s entries=%d schema_version=%d",
        path,
        len(manifest.entries),
        manifest.schema_version,
    )
    return Ok(manifest)


# frob:doc docs/modules/webapp-layout.md#staleness
# frob:tests \
# tests/unit/test_webapp_gallery_schema.py::test_entry_is_stale_on_hash_change  # noqa: E501
# frob:tests \
# tests/unit/test_webapp_gallery_schema.py::test_entry_is_stale_false_when_unchanged  # noqa: E501
def entry_is_stale(entry: GalleryEntry, current_source_hash: str) -> bool:
    """True iff `entry.source_hash` differs from `current_source_hash`
    (owner decision, crunk CRUNK-GALLERY-TREE.md section 5 Q3: a verdict
    expires on ANY byte change of source or fixture props; the caller is
    expected to have recomputed `current_source_hash` the same way
    crunk's `compute_source_hash` does, sha256 over
    `source_bytes + fixture_props_bytes` -- this function only compares)."""
    stale = entry.source_hash != current_source_hash
    _log.debug(
        "gallery entry staleness check component_id=%s stale=%s",
        entry.component_id,
        stale,
    )
    return stale
