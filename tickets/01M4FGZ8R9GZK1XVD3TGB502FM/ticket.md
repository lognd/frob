+++
id = "01M4FGZ8R9GZK1XVD3TGB502FM"
title = "Exceptions: ticket= aliases and an expiring suppression that needs no ULID"
type = "docs"
category = "todo"
priority = "low"
points = 3
parent = "01M4FGWBHH3K9F2PPFYRGQ353T"
reporter = "lognd"
created = "2026-10-09T05:08:00Z"
updated = "2026-10-09T05:08:18Z"
idempotency_key = "logand-gaps-D4"
labels = ["adoption:logand-app", "grimble"]
scope = ["docs/design/exceptions.md", "docs/design/grmb-spec.md", "changelog.d/**"]

[[links]]
kind = "relates"
target = "01M4FCB1QKVVA2EWYEGKP5659Y"

[[acceptance]]
text = "Given defer ... ticket=T-0042 in a repo migrated from v1, when the decision is read, then the doc states MDL013 behaviour, who resolves the alias and the finding when it is unknown"
bound = false

[[acceptance]]
text = "Given a design-first selector for code not yet written, when the doc is read, then it states the expiring form that needs no ULID"
bound = false
+++

Repros 10-ticket-must-be-ulid (~/projects/frob-v2-repros/logand-grimble-20261009/10-ticket-must-be-ulid) and 21-design-first-warning-flood (~/projects/frob-v2-repros/logand-grimble-20261009/21-design-first-warning-flood). Relates frob ticket ~KP5659Y (directives accept v1 aliases): grimble never reads tickets (grimble-model.md section 7), so decide how ticket= keeps an opaque string yet accepts a legacy T-NNNN that frob resolves through the ledger aliases, and add a per-selector planned marker or an expiring accept so design-first MDL005 needs no ULID ticket. Write in exceptions.md and grmb-spec 7.
