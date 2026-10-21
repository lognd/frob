+++
id = "01M4DGHT8H530QHR7VJPHFBHDJ"
title = "gob-config schema export drops the $defs entries its $ref links point at, so row columns (ForbidImport) are untyped"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-08T10:22:01Z"
updated = "2026-10-21T21:39:35Z"
scope = ["crates/gob-config/src/schema.rs", "docs/schemas/config.json", "crates/gob-config/src/describe.rs", "crates/gob-config/tests/config.rs", "crates/gob-config/tests/snapshots/config__schema_has_property_per_table.snap", "changelog.d/01M4DGHT8H530QHR7VJPHFBHDJ.fixed.md", "docs/design/config.md", "docs/design/documentation.md"]

[[acceptance]]
text = "Every $ref in the exported config schema resolves to a $defs entry (nested and recursive definitions included, shared definitions merged once)"
bound = true

[[acceptance]]
text = "ForbidImport columns are typed in docs/schemas/config.json"
bound = true

[[acceptance]]
text = "gob-plan ConfigSchema::from_json reads the shipped $defs"
bound = false
+++

found while working ~CDMAECH. docs/schemas/config.json has $ref to #/$defs/ForbidImport (also FailOn, ToolStage, ExternalPack, Pull) but no $defs object, so the GRL catalog cannot type the columns of config.invariants.forbid_imports. The exporter (schemars subschemas) must carry the definitions into the document root. gob-plan reads $defs when present (ConfigSchema::from_json).
