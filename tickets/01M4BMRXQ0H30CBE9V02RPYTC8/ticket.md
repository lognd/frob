+++
id = "01M4BMRXQ0H30CBE9V02RPYTC8"
title = "TEST001: suggest Type.method when a symref writes Type::method"
type = "task"
category = "todo"
priority = "low"
reporter = "lognd"
created = "2026-10-07T16:57:29Z"
updated = "2026-10-07T16:57:29Z"
idempotency_key = "test001-dot-member-hint"
labels = ["milestone:2"]
scope = ["crates/frob-tests/**", "crates/gob-symbols/**"]

[[acceptance]]
text = "Given a frob:tests symref path::Type::method where path::Type.method resolves, when frob check runs, then TEST001 names the dotted form as the fix (machine-applicable)"
bound = false
+++

On 2026-10-07 four directives in ~YR7MCXF used Type::method; TEST001 said only 'names no symbol in the graph'. code-model.md 2 nests members with '.', and '::' only separates locator from qualname. A teaching diagnostic (D78) should offer the dotted form.
