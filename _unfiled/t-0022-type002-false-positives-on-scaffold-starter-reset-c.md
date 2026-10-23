+++
id = "01M1J91D0PY8SZ490FJKJB61YE"
title = "TYPE002 false-positives on scaffold starter reset.css font-family var()"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-03T00:00:00Z"
updated = "2026-09-03T00:00:02Z"
aliases = ["crunk:T-0022"]
labels = ["component:crunk", "source:crunk"]
scope = ["src/crunk/rules/_typography.py", "src/crunk/scaffold/write.py", "tests/unit/test_rules_typography.py", "docs/design/subsystems/rules.md", "tests/unit/test_scaffold.py"]
+++

Discovered while working T-0012 (shell wiring). scaffold()'s generated
base/reset.css sets font-family: var(--font-family-base); (see
scaffold/write.py's _reset_css). rules/_typography.py's type002() only
understands a literal comma-separated family list and treats any
font-family value as one, so it splits 'var(--font-family-base)' into a
single stack entry that never matches spec.typography.families as a
prefix -- every freshly scaffolded default-preset project fails
crunk check out of the box with a TYPE002 error on its own starter
reset.css. Either type002() needs to recognize and skip/resolve
var(--font-family-base) references (mirroring how COLOR002 handles
var() for colors), or scaffold's starter reset.css should not use the
token custom property for font-family. Fix belongs in rules or
scaffold, not shell -- shell wiring's own tests route around it by
patching the fixture's reset.css post-scaffold.
