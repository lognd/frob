# LAYOUT gate: `frob.gates._layout_gate` / `frob.webapp._layout_structure`

<!-- frob:doc docs/modules/webapp-layout-structure.md -->

T-5767 (frob leaf F-2 of the LAYOUT review gate story T-5747): the first
LAYOUT-family gate, over crunk's gallery manifest
(docs/modules/webapp-layout.md, T-5764's vendored schema) rather than
parsed source trees. Reuses the "first leaf of the family owns the one
discovery edit" `pkgutil` pattern A11Y's `_a11y_gate.py` established
(T-5323) -- see that module's own docstring for the general shape; this
page covers only what differs for LAYOUT.

## `layout_gate`

<!-- frob:doc docs/modules/webapp-layout-structure.md#layout_gate -->

`layout_gate(root: Path) -> tuple[Violation, ...]`
(`src/frob/gates/_layout_gate.py`) walks every git-tracked
`gallery-manifest*.json` file under `root`, loads each one exactly once
via `frob.webapp._gallery_schema.load_gallery_manifest`, and hands the
resulting `GalleryManifest` to every discovered `frob.webapp._layout_*`
hook (module-level `layout_findings(manifest, manifest_path, root) ->
tuple[Violation, ...]`). A repo with no tracked gallery manifest file
short-circuits to `()` before hook discovery even runs -- unlike
A11Y/SEO/WEBPERF, this gate does NOT gate on
`frob.webapp._detect.detect_frameworks`: the presence of a tracked
manifest file is this family's own relevance signal.

## `layout_findings`

<!-- frob:doc docs/modules/webapp-layout-structure.md#layout_findings -->

`layout_findings(manifest, manifest_path, root) -> tuple[Violation, ...]`
(`src/frob/webapp/_layout_structure.py`) is this leaf's one hook,
discovered by `layout_gate` above. It runs three rules over every
`GalleryEntry` in the manifest.

## Rule ids

<!-- frob:doc docs/modules/webapp-layout-structure.md#rule-ids -->

- **LAYOUT001** "unreviewed" -- `GalleryEntry.verdict is None`: nobody
  has ever recorded an approve/reject verdict for this component or
  layout's current render set.
- **LAYOUT002** "stale review" -- the manifest's recorded `source_hash`
  no longer matches a freshly recomputed hash of the entry's current
  source file (`frob.webapp._gallery_schema.entry_is_stale`, the
  owner-decreed byte-hash staleness rule: a verdict expires on ANY byte
  change of source or fixture props, CRUNK-GALLERY-TREE.md section 5
  Q3). A verdict exists, but the component changed since it was
  recorded.
- **LAYOUT003** "render-exists" -- `GalleryEntry.artifacts == ()`: the
  entry has no declared render artifacts at all, so there was nothing a
  reviewer could have looked at even with a recorded verdict.

Positive control (this leaf's own acceptance criterion): a fixture
manifest entry with a `source_hash` that does not match its current
source file's recomputed hash raises LAYOUT002; a `verdict=null` entry
raises LAYOUT001; both clear once the entry is genuinely current
(matching hash, non-null verdict) and carries at least one artifact.

## Staleness recompute (known limitation)

<!-- frob:doc docs/modules/webapp-layout-structure.md#staleness-recompute-known-limitation -->

crunk's own `source_hash` is `sha256(source_bytes + fixture_props_bytes)`
(`compute_source_hash`, docs/modules/webapp-layout.md#staleness). This
leaf's `_recompute_source_hash` recomputes over `source_bytes` alone
(`fixture_props_bytes=b""`), because frob has no channel to an entry's
declared fixture props yet -- an entry with real (non-empty) fixture
props will therefore always compare as LAYOUT002-stale here, even
immediately after a correct re-review. Threading fixture props through
is explicitly out of this leaf's scope; `frob:todo T-5767` on
`_recompute_source_hash` tracks it, and F-3 (webapp families accepting
catalog-render input, filed as a follow-on epic per
CRUNK-GALLERY-TREE.md section 5 Q4) is its natural home.

## Not yet wired into `frob check`

This leaf ships `layout_gate`/`layout_findings` as importable, fully
tested modules; wiring `layout_gate` into `frob.gates.__init__`'s
process-job table and registering `LAYOUT001`-`LAYOUT003` in
`frob.gates._waive._KNOWN_GATE_RULES` are out of this leaf's declared
scope (`src/frob/gates/_layout_gate.py`,
`src/frob/webapp/_layout_structure.py` only) -- filed as T-draft-0ab8e38c
rather than silently left undone.
