+++
id = "01M68K5GXB2C7G082PGAA9C2BY"
title = "frob verb to dismiss a finding with a reason (over gob_check::dismiss)"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-31T09:03:05Z"
updated = "2026-10-31T09:03:05Z"
idempotency_key = "x84157k-dismiss-verb"
scope = ["crates/frob/**", "crates/frob-check/**"]

[[acceptance]]
text = "A frob verb takes a rule, fingerprint and reason and records the dismissal via gob_check::dismiss; a missing reason is rejected"
bound = false
+++

follow-up of ~X84157K: the dismiss entry point exists in gob-check but has no CLI verb. Also consider locking precision-history.json against concurrent check runs.
