+++
id = "01M42RRWWFPJETRP299YFN5XCF"
title = "A dedicated RequiredReason::UnreadableFile for READ001 instead of reusing ZeroSubjects"
type = "task"
category = "todo"
priority = "low"
points = 2
reporter = "lognd"
created = "2026-10-04T06:14:13Z"
updated = "2026-10-04T06:14:13Z"
scope = ["crates/gob-rules/**", "crates/gob-check/src/**", "crates/grimble-check/**", "docs/schemas/**", "docs/design/sibling-contract.md"]

[[acceptance]]
text = "Given an unreadable tracked file, when frob check and grimble check report it, then the required reason is unreadable-file in JSON and text"
bound = false
+++

~KAD47SZ reports unreadable tracked files as READ001 with RequiredReason::ZeroSubjects, so grimble-check and the envelope describe them as vacuous. Add a dedicated reason through the rule metadata, the envelope schema and the sibling contract.
