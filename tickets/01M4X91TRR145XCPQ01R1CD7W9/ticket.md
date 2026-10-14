+++
id = "01M4X91TRR145XCPQ01R1CD7W9"
title = "GRL lowering: needs vocab(NAME) and vocab membership (in knob.NAME)"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 5
reporter = "lognd"
created = "2026-10-14T13:18:58Z"
updated = "2026-10-14T15:45:02Z"
scope = ["crates/gob-plan/**"]
+++

Found while working ~C6W2KWJ. NEAT013 (acceptance corpus ~0HC06TD) uses 'needs vocab(sources)', a vocab knob and 'v in knob.sources'. gob-plan has no vocab need, Need bitset has 4 variants, and the executor has no callee_vocab (Q47) support; knob values are inlined at declared defaults. Needs IR (need or op), codec, validate, executor and tests.
