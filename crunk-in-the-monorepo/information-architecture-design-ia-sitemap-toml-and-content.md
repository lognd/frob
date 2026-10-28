+++
id = "01M5XCZ0XPCPA1DT2QB5VGHDZC"
title = "Information architecture: design/ia/sitemap.toml and content-model.toml with route/screen, depth, label and reachability rules"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M4CXSAG0YPF18FX3KAPVX45C"
reporter = "lognd"
created = "2026-10-27T00:43:02Z"
updated = "2026-10-28T12:55:43Z"
labels = ["area:crunk", "no-story"]
scope = ["crates/crunk-spec/src/ia.rs, crates/crunk-rules/src/ux/ia.rs, crates/crunk-rules/tests/ux_ia.rs"]

[[acceptance]]
text = "Given a sitemap route with no screen, or a screen with no route, when checked, then a UX finding names it; given routes in code (gob-frameworks) absent from the sitemap, then a finding names the route. Edge cases: depth beyond the configured max fires once per deepest path; duplicate sibling labels differ only by case still collide; a cycle in parent links is a schema error; a page unreachable from home is named; a dynamic route segment matches a screen declared with the same param shape; absent sitemap with the pack on is silent"
bound = false
+++

Design crunk.md section 8 IA row. Route discovery reuses gob-frameworks; if unavailable for a project, route/code comparison is Unresolved, not clean.

no-story: internal engineering task in crunk-spec; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
