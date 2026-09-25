# Webapp layout: vendored gallery manifest schema

<!-- frob:doc docs/modules/webapp-layout.md -->

`frob.webapp._gallery_schema` (`src/frob/webapp/_gallery_schema.py`) is
frob's read-only, vendored copy of crunk's gallery manifest schema. It
lets frob validate a `gallery-manifest.v1.json` file -- the one
committed artifact crunk's gallery pipeline (`crunk.gallery.manifest`)
writes -- without frob ever importing crunk as a package. This is the
one leaf (F-0) of the frob story "LAYOUT review gate" (T-5747) that the
rest of that story (LAYOUT001-00x rules, doctor tool-presence check,
ticket-evidence wiring) builds on.

## Cross-repo contract

crunk and frob are separate repos with separate dependency graphs.
frob's `webapp` package is a leaf layer (`[arch.layering]`, `frob.toml`)
and does not import crunk. The contract between the two repos is the
JSON Schema crunk generates from its pydantic `Manifest` model
<!-- frob:waive DOC006 reason="cross-repo pointer: this path lives in the crunk repository, which owns the gallery manifest (T-5747 split)" -->(`crunk/schemas/gallery-manifest.v1.json`, produced by
`Manifest.model_json_schema()`) -- frob vendors a byte-for-byte copy of
that file as data inside `_gallery_schema.py`, plus a small pydantic
model (`GalleryManifest` and friends) that mirrors crunk's field shapes
closely enough for frob's own reads. Nothing in this module writes a
manifest; that remains crunk's job.

## Vendoring procedure

Whenever crunk's schema changes (a field is added/removed, or
`SCHEMA_VERSION` bumps):

1. Regenerate crunk's schema file per crunk's own doc
<!-- frob:waive DOC006 reason="cross-repo pointer: this path lives in the crunk repository, which owns the gallery manifest (T-5747 split)" -->   (`crunk/docs/design/subsystems/gallery-manifest.md#json-schema-export`).
2. Copy the regenerated `crunk/schemas/gallery-manifest.v1.json` text
   verbatim into `_VENDORED_SCHEMA_JSON` in
   `src/frob/webapp/_gallery_schema.py` (wrapped across multiple short
   Python string literals so no physical source line exceeds the
   88-column limit; the JSON content itself is unchanged by the
   wrapping).
3. Update `_VENDORED_FROM_COMMIT` to the crunk commit hash the schema
   came from, and `_VENDORED_SCHEMA_VERSION` if crunk's
   `SCHEMA_VERSION` constant moved.
4. Update the mirror pydantic model (`GalleryManifest`, `GalleryEntry`,
   `RenderState`, `RenderArtifact`, `Verdict`, enums) by hand against
   `crunk.gallery.manifest`'s current field list.
5. Re-run `tests/unit/test_webapp_gallery_schema.py::test_vendored_schema_matches_crunk_source`
   with a sibling crunk checkout present -- it diffs the vendored JSON
   Schema against crunk's live file and fails on any drift. The test is
   skipped with a named reason when no sibling crunk checkout is found,
   so CI without a crunk clone still runs the rest of the file.

## Manifest

`GalleryManifest` mirrors `crunk.gallery.manifest.Manifest`: a
`schema_version`, `generated_at`/`tool_version` provenance fields, and
a tuple of `GalleryEntry` records. Each `GalleryEntry` requires
`source_hash` -- an entry missing it fails validation identically to
crunk's own `Manifest` check (this module's named positive control).

`load_gallery_manifest(path: Path) -> Result[GalleryManifest, GalleryManifestError]`
reads and validates one manifest file from disk, using typani's
`Result` rather than raising.

## Staleness

crunk's owner decision (`CRUNK-GALLERY-TREE.md` section 5, Q3): a
`GalleryEntry.verdict` expires on ANY byte change of the component's
source or its fixture props. `source_hash` is a sha256 digest over
`source_bytes + fixture_props_bytes` (crunk's `compute_source_hash`);
this is a byte hash, not a visual diff -- a whitespace-only source edit
or an unchanged-pixel props reformat both invalidate an existing
verdict.

`entry_is_stale(entry: GalleryEntry, current_source_hash: str) -> bool`
implements the consumer side of this rule: it compares
`entry.source_hash` against a hash the caller already recomputed the
same way crunk does. This module does not recompute the hash itself.

## Errors

`GalleryManifestError` (`typani.error_set.ErrorSet`): `NotFound`,
`Unreadable`, `Malformed`, `Invalid` -- mirrors crunk's own
`ManifestError` shape.

## Public API

- `GalleryManifest`, `GalleryEntry`, `RenderState`, `RenderArtifact`,
  `Verdict`, `EntryKind`, `StateKind`, `VerdictStatus` -- the mirror
  pydantic models.
- `VENDORED_SCHEMA: dict` -- the vendored JSON Schema, parsed once at
  import time.
- `load_gallery_manifest(path: Path) -> Result[GalleryManifest, GalleryManifestError]`
- `entry_is_stale(entry: GalleryEntry, current_source_hash: str) -> bool`
