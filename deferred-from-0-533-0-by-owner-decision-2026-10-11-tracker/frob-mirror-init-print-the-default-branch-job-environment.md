+++
id = "01M3ZX85DAD1HTEWWBMSB05K03"
title = "frob mirror init: print the default-branch job, environment and App setup, and the GitHub autolink"
type = "task"
category = "todo"
priority = "low"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-03T03:34:44Z"
updated = "2026-10-03T05:49:59Z"
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

Implements mirror.md section 3.1 (setup) and navigation.md section 1 (autolink, UNVERIFIED).

Prints, writing nothing: the dedicated GitHub App and its permissions, the environment restricted to the default branch holding the App key and the marker keyring (never repository secrets), the default-branch workflow, the optional nudge workflow, [mirror] bot_ids, and the autolink reference. The autolink format limits are UNVERIFIED and must be checked here against the live API.
