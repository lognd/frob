+++
id = "01M4M27EPRF0RAN4YBEA2J8C05"
title = "Lease and ledger actor is the git user.name at the time of the call, so changing the git identity strands a held lease (requeue refused with E-LEASE-HELD for the same worker)"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-10T23:26:32Z"
updated = "2026-10-26T13:17:59Z"
scope = ["crates/frob-lease/**"]

[[acceptance]]
text = "a lease held by actor A can be released by the same clone after the git identity changes, or the refusal names the identity mismatch and the verb to fix it, covered by a test"
bound = true
+++

found while draining tickets: after git user.name changed from Claude to lognd, frob requeue of a lease held by Claude was refused with E-LEASE-HELD; releasing required running under the old identity.
