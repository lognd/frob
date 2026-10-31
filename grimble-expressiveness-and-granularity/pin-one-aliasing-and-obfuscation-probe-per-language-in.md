+++
id = "01M67VHPGMWP2ZSN378AH9XAGZ"
title = "Pin one aliasing and obfuscation probe per language in symbolic_audit"
type = "task"
category = "in-progress"
priority = "high"
points = 5
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-31T02:10:18Z"
updated = "2026-10-31T06:02:07Z"
idempotency_key = "aliasprobe-1"
scope = ["crates/grimble-check/tests/symbolic_audit.rs"]

[[acceptance]]
text = "For every supported language there is at least one aliased-import case, one shadowing case and one computed-name case in symbolic_audit.rs."
bound = true

[[acceptance]]
text = "Resolvable forms report the capability; unresolvable forms report Unresolved, never a silent pass."
bound = true
+++

Owner: ensure no easily defeatable lexical checks. Serialize after Java, C/C++ and shell land (they edit the same test file).
