+++
id = "01M7EXVJ2EZKNPCK1F2WY2V5CG"
title = "docs/guides/grimble.md: fix five stale lines (fail-on, strict, gate, link, empty model)"
type = "task"
category = "todo"
priority = "medium"
points = 1
reporter = "lognd"
created = "2026-11-15T06:21:01Z"
updated = "2026-11-15T06:21:01Z"
labels = ["no-story"]

[[acceptance]]
text = "Each of the five lines matches current behavior"
bound = false

[[acceptance]]
text = "gob-dev gen all --check passes"
bound = false
+++

Audit: ~/projects/frob-audit2-grimble.md M8 (stale lines). GUIDE line 67 --fail-on error|warn|advisory|none; line 173 strict=true (docs/reference/config/frob.md:242 says deprecated no-op); lines 161-163 gate in fail_on terms; line 215 link text/target mismatch ../design/grmb-spec.md; line 65 'An empty model passes' is false. Verify each against HEAD before editing.
