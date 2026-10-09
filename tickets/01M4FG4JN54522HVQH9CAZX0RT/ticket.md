+++
id = "01M4FG4JN54522HVQH9CAZX0RT"
title = "Directive parser: support v1 backslash continuation onto the next comment line, and never echo a stray backslash as a TEST001 symref"
type = "bug"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-09T04:53:26Z"
updated = "2026-10-09T05:13:07Z"
labels = ["adoption:logand-app"]
scope = ["crates/gob-directives/**", "crates/frob-tests/**", "changelog.d/**"]

[[acceptance]]
text = '''Given '# frob:tests path::test_x\' followed by '# kind="unit"' (including a break mid-token), when directives are parsed, then one directive with both arguments results, with no PARSE001 and no TEST001 naming a backslash'''
bound = false

[[acceptance]]
text = 'Given v1 key forms frob:todo T-1 note="multi word" and frob:invariant NAME reason="...", when parsed, then they are accepted as the note text and reason (v1 compatibility) and fmt or --fix rewrites them to the v2 form'
bound = false
+++

logand.app-v2 F-503: about 850 sites (593 PARSE001, 261 TEST001). Same crate as ~SZ3EANE (trailing pragmas): dispatch after it.
