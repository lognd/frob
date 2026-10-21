+++
id = "01M4828JQJKETWWCRQGJCXJ4VH"
title = "gob-symbols: CJS function-expression exports and block-scoped binders for TS/JS"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M47QJ3CHWZBZ6R3QHN4R2XN5"
reporter = "lognd"
created = "2026-10-06T07:36:16Z"
updated = "2026-10-21T23:28:16Z"
scope = ["crates/gob-symbols/src/typescript/**", "crates/gob-symbols/src/graph/typescript.rs", "crates/gob-symbols/tests/it/typescript.rs", "docs/reference/fidelity.md", "changelog.d/01M4828JQJKETWWCRQGJCXJ4VH.added.md"]

[[acceptance]]
text = "Given exports.f = function(){} or module.exports = { f() {} }, when symbols are built, then a unit exists for f"
bound = true

[[acceptance]]
text = "Given a block-scoped let or const binder in TS or JS, when a reference is resolved, then it binds to the block binder"
bound = true

[[acceptance]]
text = "Function-valued CJS exports (exports.f, module.exports.f, object-literal members) become public units"
bound = true

[[acceptance]]
text = "CJS last write of a name wins and module.exports reassignment detaches earlier writes"
bound = true

[[acceptance]]
text = "let/const in a block shadow only inside that block; var hoists; for/catch/switch scopes bind"
bound = false
+++

Found while working ~6KKJF80. Two honest gaps of the TS adapter, both reported Unknown today: (1) exports.f = function(){} and module.exports = { f() {} } create no unit (only identifier aliases do); (2) binders are function-level, so a block-scoped let that shadows an outer name hides it for the whole function. Add units for CJS function-expression exports and block-level scopes in the scope graph, with corpus tests.
