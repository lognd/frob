+++
id = "01M4XFTY5MGTJ6GMS4NEAKG01G"
title = "GRL lowering: non-count knobs honour per-repo [rules] overrides"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-14T15:17:32Z"
updated = "2026-10-14T15:17:32Z"
scope = ["crates/gob-plan/**"]
+++

Found while working ~C6W2KWJ. Only count limits (Limit::Knob) read a [rules] override; int/string/bool/regex/glob knob operands inline their declared default at lowering. Needs a plan operand that reads the knob at run time (like Op::Count knob limits) plus executor and validate support.
