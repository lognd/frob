+++
id = "01M3ZBQPK3ZFE8TVB3GV5F85PC"
title = "ticket update: empty --set clears list fields silently; ticket show --json omits scope"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-02T22:28:39Z"
updated = "2026-10-02T22:51:43Z"
idempotency_key = "m2-update-scope"
labels = ["milestone:2"]
scope = ["crates/frob-ledger/**", "crates/frob/**"]

[[acceptance]]
text = "Given a ticket with a scope, when ticket update --set scope= runs without --clear, then it is refused and the scope is unchanged"
bound = false

[[acceptance]]
text = "Given any ticket, when ticket show --json runs, then every frontmatter field including scope is present"
bound = false
+++

Found by the coordinator on ~KKR84AW: frob ticket update --set scope= (empty value) replaced the scope with an empty list and reported ok, and ticket show --json has no scope key, so scripts cannot read it. Refuse an empty value for list fields unless --clear <field> is given (E-USAGE with the remedy); add --add-scope and --remove-scope flags mirroring --add-label; include scope, labels, acceptance and every frontmatter field in show --json (generated from the TicketSchema description so nothing is missing).
