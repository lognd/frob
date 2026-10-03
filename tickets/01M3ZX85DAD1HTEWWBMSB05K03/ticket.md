+++
id = "01M3ZX85DAD1HTEWWBMSB05K03"
title = "frob mirror init: setup guidance including the GitHub autolink"
type = "task"
category = "todo"
priority = "low"
points = 2
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:44Z"
updated = "2026-10-03T03:34:44Z"
idempotency_key = "m2-mirror-init"
labels = ["milestone:2", "area:mirror"]
scope = ["crates/frob/src/mirror_cmd.rs"]

[[links]]
kind = "blocked-by"
target = "01M3ZX8182AHQF2XB4WYNC30Q8"

[[acceptance]]
text = "Given `frob mirror init`, when run, then the setup steps are printed and nothing is written"
bound = false

[[acceptance]]
text = "Given the autolink limits, when verified against the GitHub docs, then the ticket records the verified format or states it is unsupported"
bound = false
+++

Implements navigation.md section 1 (autolink, UNVERIFIED); mirror.md.

Prints the secrets, permissions and workflow to set up and the autolink reference; the autolink format limits are UNVERIFIED and must be checked here.
