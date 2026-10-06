+++
id = "01M4839AA2A1YSTF5AX2DRPX3B"
title = "Generate docs/schemas/sibling.json from the gob-check::sibling types"
type = "task"
category = "in-progress"
priority = "medium"
parent = "01M47QSB9W3BVYZ4NPRVX11TG4"
reporter = "lognd"
created = "2026-10-06T07:54:09Z"
updated = "2026-10-06T08:42:12Z"
scope = ["crates/gob-check/**", "docs/schemas/sibling.json", "crates/gob-config/**", "changelog.d/**"]

[[acceptance]]
text = "docs/schemas/sibling.json is generated and GEN001-checked"
bound = false

[[acceptance]]
text = "sibling documents are byte-identical before and after (existing snapshots unchanged)"
bound = false
+++

Deferred by ~BVCRKXA: the gob.sibling/1 emitter still builds serde_json::Value and the schema stays hand-written. Move the emitter to typed structs with a schemars derive and generate the schema through cargo dev gen so GEN001 keeps it current (products.md section 7). Documents must stay byte-identical.
