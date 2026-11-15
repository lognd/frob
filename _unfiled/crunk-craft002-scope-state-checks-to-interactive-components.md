+++
id = "01M7EXTCNFZ76538BN8RNBVXSG"
title = "crunk CRAFT002: scope state checks to interactive components"
type = "task"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-11-15T06:20:23Z"
updated = "2026-11-15T06:20:23Z"
idempotency_key = "crunkplan-93fa74ab877f"
labels = ["no-story"]

[[acceptance]]
text = "a static component with no states passes CRAFT002; ~YQ8ZG91 related"
bound = false
+++

Source: ~/projects/frob-audit2-crunk.md, finding M2.
Evidence: CRAFT002 demands states on non-interactive components
Remedy: apply only to components declared interactive
Crates/files: crates/crunk-rules craft
Verify against HEAD first; the audit ran on a stale binary.
