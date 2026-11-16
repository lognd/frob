+++
id = "01M61DFC5ZCSJTKMNBP88AKFVS"
title = "Resolve serde with-attribute functions in the DEAD001 call graph"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-28T14:08:55Z"
updated = "2026-11-16T09:28:20Z"
scope = ["crates/frob-check/**", "crates/gob-symbols/**"]

[[acceptance]]
text = "DEAD001 treats a function named by a serde with attribute as reached; test proves it"
bound = true
+++

Functions named by #[serde(with = "mod")] strings (serialize/deserialize in gob-symbols model.rs and graph/linkcache.rs) are reported DEAD001 as unresolved. Teach the resolver to read serde with attributes, then drop the defers. Found while working ST6JQTK.
