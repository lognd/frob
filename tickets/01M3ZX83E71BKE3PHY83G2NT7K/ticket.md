+++
id = "01M3ZX83E71BKE3PHY83G2NT7K"
title = "[mirror.<tracker>] mapping, materialized, checked against capabilities"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:42Z"
updated = "2026-10-03T03:34:42Z"
idempotency_key = "m2-mirror-mapping-config"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/mapping.rs", "crates/frob-mirror/src/config.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX83AB2JADBKWFA9SY4J60"

[[acceptance]]
text = "Given a mapping that omits the priority field and does not drop it, when loaded, then a config error names the field"
bound = false

[[acceptance]]
text = "Given a mapping routing priority to a label, when applied, then the label appears in the planned operation"
bound = false
+++

Implements mirror.md sections 2 and 2.1.

Versioned ConfigTable mapping projection fields to labels, fields, issue types or states; a projection field the mapping neither routes nor explicitly drops is a config error so nothing disappears silently.
