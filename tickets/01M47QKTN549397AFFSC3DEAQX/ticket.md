+++
id = "01M47QKTN549397AFFSC3DEAQX"
title = "project_model: package.json workspaces and tsconfig paths resolve TS imports"
type = "story"
category = "in-progress"
priority = "high"
points = 5
parent = "01M47QJ3CHWZBZ6R3QHN4R2XN5"
reporter = "lognd"
created = "2026-10-06T04:30:10Z"
updated = "2026-10-06T08:28:49Z"
scope = ["crates/gob-symbols/**"]

[[links]]
kind = "blocked-by"
target = "01M43ARXMH7RJ63G8096KKJF80"

[[acceptance]]
text = "a monorepo fixture with two workspace packages and a tsconfig paths alias resolves every import, with node_modules imports external"
bound = false

[[acceptance]]
text = "unresolvable specifiers are Unknown imports, never dropped"
bound = false

[[acceptance]]
text = "frob doctor --languages reports the project model rows"
bound = false
+++

language-engines.md section 2. In gob-symbols beside crates.rs and the .NET project model: package.json (name, workspaces, dependencies, exports, main) and tsconfig.json (paths, baseUrl, extends, include) become packages and path aliases; TS/JS import resolution uses them (bare specifier to workspace package, alias to file, node_modules as external, anything unresolvable Unknown). A file belongs to the nearest enclosing package.
