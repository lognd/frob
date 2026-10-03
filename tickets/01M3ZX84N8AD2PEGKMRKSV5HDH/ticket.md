+++
id = "01M3ZX84N8AD2PEGKMRKSV5HDH"
title = "MIR002 severity placement: required in mirror job and status, Warning in code check (OWNER call)"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "medium"
points = 2
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:43Z"
updated = "2026-10-03T03:39:11Z"
idempotency_key = "m2-mirror-mir002-placement"
labels = ["milestone:2", "area:mirror", "needs-owner"]
scope = ["crates/frob-obligations/src/mir.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX84HDHZCJRSXCCPNP7J3G"

[[acceptance]]
text = "Given a diverged issue, when `frob mirror status` runs, then it exits 1 with MIR002 as an Error"
bound = false

[[acceptance]]
text = "Given the same divergence, when `frob check` and `frob land` run in the code checkout, then MIR002 is a Warning and land is not blocked"
bound = false
+++

Implements security.md sections 2.11 and 5 item 1; mirror.md section 3.1.

Proposed: Error and required in the mirror job and `frob mirror status` (exit 1); a Warning in a code checkout's frob check and never a land blocker (I12). Awaiting owner confirmation.
