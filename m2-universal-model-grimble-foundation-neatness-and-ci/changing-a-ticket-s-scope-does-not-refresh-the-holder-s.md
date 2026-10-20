+++
id = "01M3ZBRRMQ55G1B8VCNKDR4ZBR"
title = "Changing a ticket's scope does not refresh the holder's lease"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T22:29:14Z"
updated = "2026-10-02T23:00:35Z"
idempotency_key = "m2-lease-refresh"
labels = ["milestone:2"]
scope = ["crates/frob-lease/**", "crates/frob-ledger/**", "crates/frob/**", "docs/reference/**"]

[[acceptance]]
text = "Given a held lease, when the holder widens the ticket scope, then the lease file contains the new globs and SCOPE001 no longer fires for them"
bound = true
+++

Found on ~KKR84AW: after ticket update changed the scope, the live lease under .git/frob/leases kept the old globs and SCOPE001 kept firing; there is no verb to widen a held lease, so the coordinator edited the lease file by hand. A scope change by the lease holder must re-validate overlap and rewrite the lease under leases.lock (refusing with E-LEASE-HELD if the widened scope overlaps another live lease); add frob lease widen <ticket> as the explicit form.
