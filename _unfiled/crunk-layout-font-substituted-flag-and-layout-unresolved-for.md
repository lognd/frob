+++
id = "01M7EXTHCAV03YK72VM157ZVFN"
title = "crunk layout: font_substituted flag and LAYOUT Unresolved for unbundled faces"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:20:28Z"
updated = "2026-11-15T06:20:28Z"
idempotency_key = "crunkplan-79b6023d3ca3"
labels = ["no-story"]

[[acceptance]]
text = "a solve with a substituted face sets font_substituted and layout rules are Unresolved"
bound = false
+++

Source: ~/projects/frob-audit2-crunk.md, finding L7.
Evidence: unbundled display faces silently fall back
Remedy: record font_substituted in the solve; LAYOUT rules return Unresolved
Crates/files: crates/crunk-layout fonts, crates/crunk-rules layout
Verify against HEAD first; the audit ran on a stale binary.
