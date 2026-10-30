+++
id = "01M67DZ7XVWH6P7KNYAZN6F4A4"
title = "Deprecate [pm] strict as a no-op that logs WARN"
type = "task"
category = "done"
outcome = "duplicate"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-30T22:13:02Z"
updated = "2026-10-30T23:03:38Z"
scope = ["crates/frob-pm/**", "docs/design/rules.md"]

[[acceptance]]
text = "[pm] strict is accepted in config, logs a WARN deprecation via tracing, and changes no finding severity"
bound = false
+++

Split from ~BZF44PC (out of its scope). [pm] strict (frob-pm config.rs, eval apply_strict/strict_severity, host.rs) must stay accepted but change no behavior and log a tracing WARN deprecation; PM rules are Errors.
