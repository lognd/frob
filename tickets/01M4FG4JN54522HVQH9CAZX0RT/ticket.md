+++
id = "01M4FG4JN54522HVQH9CAZX0RT"
title = "Directive parser: support v1 backslash continuation onto the next comment line, and never echo a stray backslash as a TEST001 symref"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-09T04:53:26Z"
updated = "2026-10-09T16:20:53Z"
labels = ["adoption:logand-app", "creates:crates/gob-directives/src/compat.rs", "creates:crates/gob-directives/tests/mdtest/continuation.md", "creates:crates/gob-directives/tests/mdtest/v1-keys.md"]
scope = ["changelog.d/**", "crates/gob-directives/src/comments.rs", "crates/gob-directives/src/lex.rs", "crates/gob-directives/src/lib.rs", "crates/gob-directives/src/compat.rs", "crates/gob-directives/tests/mdtest/continuation.md", "crates/gob-directives/src/frob.rs", "crates/gob-directives/src/scan.rs", "crates/gob-directives/tests/mdtest/trailing-pragma.md", "crates/gob-directives/tests/mdtest/v1-keys.md", "docs/reference/directives.md", "docs/schemas/directives.json", "changelog.d/01M4FCZE7QETQK5CKKDSZ3EANE.fixed.md"]

[[acceptance]]
text = '''Given '# frob:tests path::test_x\' followed by '# kind="unit"' (including a break mid-token), when directives are parsed, then one directive with both arguments results, with no PARSE001 and no TEST001 naming a backslash'''
bound = true

[[acceptance]]
text = 'Given v1 key forms frob:todo T-1 note="multi word" and frob:invariant NAME reason="...", when parsed, then they are accepted as the note text and reason (v1 compatibility) and fmt or --fix rewrites them to the v2 form'
bound = true

[[acceptance]]
text = "Given C-like comments (// and /* */ in TS, TSX and Rust), when v1 continuation, note= forms or frob:waive appear in them, then they are handled exactly like the # forms (logand.app-v2 F-549)"
bound = true
+++

logand.app-v2 F-503: about 850 sites (593 PARSE001, 261 TEST001). Same crate as ~SZ3EANE (trailing pragmas): dispatch after it.
