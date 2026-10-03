+++
id = "01M3ZX7ECR0R91Q5R2T16R03NG"
title = "GRL015: fix applicability required and plugin fixes confined to the primary span"
type = "task"
category = "todo"
priority = "medium"
points = 2
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:20Z"
updated = "2026-10-03T03:34:20Z"
idempotency_key = "m2-grl-check-fixes"
labels = ["milestone:2", "area:grl"]
scope = ["crates/gob-plan/src/check/fixes.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7DYR7PR1PBCZ7E8Q56WW"

[[links]]
kind = "blocked-by"
target = "01M3ZX7E968R74N08V8DW4RJVG"

[[acceptance]]
text = "Given `fix d -> `x`` with no applicability, when compiled, then GRL015 is emitted with its golden"
bound = false

[[acceptance]]
text = "Given a plugin-pack rule using `fix host add_grant(...)`, when compiled, then GRL015 rejects it because host fixes are std only"
bound = false
+++

Implements grl-spec.md section 8; security.md section 2.10.

A fix without an applicability, or a plugin fix that edits outside the finding's primary span without fix.machine, is GRL015. `fix host` is std only.
