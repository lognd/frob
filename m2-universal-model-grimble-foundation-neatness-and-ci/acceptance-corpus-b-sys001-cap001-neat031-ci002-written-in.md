+++
id = "01M3ZX7HZSW3J5YN1KEACSP6CZ"
title = "Acceptance corpus B: SYS001, CAP001, NEAT031, CI002 written in GRL"
type = "task"
category = "todo"
priority = "low"
points = 3
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:24Z"
updated = "2026-10-03T03:34:24Z"
idempotency_key = "m2-grl-ten-b"
labels = ["milestone:2", "area:grl", "kind:test"]
scope = ["crates/gob-plan/tests/ten_rules/**"]

[[links]]
kind = "blocked-by"
target = "01M3Z714EEST9EGEHWWV56RXG4"

[[links]]
kind = "blocked-by"
target = "01M3Z90E4JN2DFEJ0Y4WHCDCMG"

[[links]]
kind = "blocked-by"
target = "01M3ZX7E5VPTH8J16D5APQDEAP"

[[links]]
kind = "blocked-by"
target = "01M3ZX7HW6V59EBYZ2A0HC06TD"

[[acceptance]]
text = "Given the four .grl files, when `rule test` runs, then every example passes including the unresolved and notapplicable ones"
bound = false

[[acceptance]]
text = "Given CI002 on a workflow that fails to parse, when run, then the result is Unresolved, not clean"
bound = false
+++

Implements grl-spec.md section 12; D80 acceptance.

The four rules that need engine relations (cell, owned by), as roles snippets and the YAML adapter.
