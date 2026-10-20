+++
id = "01M3ZX7EYANWG9GE031G17RK4A"
title = "Plan executor relations: edge verbs, bounded reaches, count, defs, knobs, side relations"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 5
parent = "01M3ZWPE0CNFWB4PTW3D05GDWP"
reporter = "lognd"
created = "2026-10-03T03:34:21Z"
updated = "2026-10-09T19:39:00Z"
idempotency_key = "m2-exec-relations"
labels = ["milestone:2", "area:grl", "creates:crates/gob-plan/tests/exec_relations.rs", "creates:crates/gob-plan/src/exec/relations/**"]
scope = ["crates/gob-plan/src/exec/relations/**", "crates/gob-plan/src/exec/mod.rs", "crates/gob-plan/tests/exec_relations.rs", "crates/gob-plan/src/exec/core/eval.rs", "crates/gob-plan/src/exec/core/kind.rs", "crates/gob-plan/src/exec/core/mod.rs", "crates/gob-plan/src/exec/core/verdict.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7DMYNTWB3AP04CDMAECH"

[[links]]
kind = "blocked-by"
target = "01M3ZX7ETPH5Z6K2VJ64K5XTMX"

[[links]]
kind = "relates"
target = "01M3ZTB2Y0J454GSSK4KGAMSF9"

[[links]]
kind = "relates"
target = "01M3ZVQA77ZEK9DXEN5Z0XMZEG"

[[acceptance]]
text = "Given `t reaches f via calls within 2` over a fixture whose only path crosses a May edge, when executed, then the answer is Unknown with that edge on the frontier"
bound = true

[[acceptance]]
text = "Given `find p: diff.changed` and a lease input, when executed, then rows come from the typed inputs and a knob override in [rules] changes a count threshold"
bound = true
+++

Implements grl-spec.md sections 6, 7.1 and 7.4.

Verbs with Must/May status, `reaches ... via ... within N` returning Yes/No/Unknown with the frontier, count, non-recursive defs, knobs overridable from [rules], and typed side relations (config, diff, lease, model).
