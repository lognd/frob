+++
id = "01M5GGJXDV139FW9WX0JR8RKNQ"
title = "gob-symbols: expose a public TS/JS export resolver"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M47QJ3CHWZBZ6R3QHN4R2XN5"
reporter = "lognd"
created = "2026-10-22T00:36:12Z"
updated = "2026-11-12T08:31:42Z"
scope = ["crates/gob-symbols/src/**", "crates/gob-frameworks/**", "changelog.d/01M5GGJXDV139FW9WX0JR8RKNQ.*"]

[[acceptance]]
text = "Given a TS/JS module that re-exports a name from a relative module, when the public export resolver is called, then it returns the defining module and gob-frameworks uses it instead of its own text-based re-export resolution"
bound = false
+++

Found while working PDZD40N. ts_export is private and ts_import_targets ignores public re-export bindings, so gob-frameworks/src/exports.rs and repo.rs duplicate text-based relative re-export resolution. Expose a resolver and replace the duplicate. Limits left: flatRoutes() stays Unknown; package and computed re-exports leave handler unnamed; export * approximated via Method::EXPORTS; tsconfig alias specifiers unresolved.
