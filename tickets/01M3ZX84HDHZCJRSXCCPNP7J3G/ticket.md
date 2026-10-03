+++
id = "01M3ZX84HDHZCJRSXCCPNP7J3G"
title = "Detect edited issues: skip, report MIR002 with specifics, comment once"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "high"
points = 5
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:43Z"
updated = "2026-10-03T03:39:11Z"
idempotency_key = "m2-mirror-divergence"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob-mirror/src/divergence.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX83NZ4PAM53VQCHXPE1R8"

[[links]]
kind = "blocked-by"
target = "01M3ZX841SP0ZXM4CT18A4B8CV"

[[acceptance]]
text = "Given an issue whose title was edited in the tracker, when the mirror runs, then it skips that issue, reports MIR002 with the published and current titles, and posts one comment"
bound = false

[[acceptance]]
text = "Given the same divergence on a second run, when it runs, then no second comment is posted but MIR002 repeats"
bound = false
+++

Implements mirror.md section 3.1.

Compare the tracker rendering to the last published digest; a diverged issue is skipped, never overwritten; the finding names ticket, issue URL, each edited field with published and current values (diff for body sections), tracker user and time; one explanatory comment posted once.
