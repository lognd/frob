+++
id = "01M61DFC5ZCSJTKMNBP88AKFVS"
title = "Resolve serde with-attribute functions in the DEAD001 call graph"
type = "bug"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-28T14:08:55Z"
updated = "2026-10-28T14:08:55Z"
scope = ["crates/frob-check/**", "crates/gob-symbols/**"]
+++

Functions named by #[serde(with = "mod")] strings (serialize/deserialize in gob-symbols model.rs and graph/linkcache.rs) are reported DEAD001 as unresolved. Teach the resolver to read serde with attributes, then drop the defers. Found while working ST6JQTK.
