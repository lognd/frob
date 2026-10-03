+++
id = "01M406M2HX6Z6SEGM6HRPQKHAV"
title = "frob vet: dependency vetting (designed in cli.md, not implemented)"
type = "task"
category = "todo"
priority = "medium"
points = 5
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-03T06:18:31Z"
updated = "2026-10-03T06:18:31Z"
idempotency_key = "m2-frob-vet"
labels = ["milestone:2", "area:security"]
scope = ["crates/frob-vet/**", "crates/frob/src/**"]

[[acceptance]]
text = "Given a change that adds a dependency with a RustSec advisory, when frob vet runs, then it reports the advisory with its id and the fixed versions"
bound = false

[[acceptance]]
text = "Given a ticket diff that adds a new direct dependency, when frob check --ticket runs, then the dependency is reported unless it was vetted"
bound = false
+++

cli.md and build-test-ci.md describe frob vet for dependency vetting; v2 has no implementation and no ticket, while security.md 2.5 (wasmtime vulnerable-below floor, SEC-34) and the global agent rules ('frob vet' for new dependencies) rely on it. Implement per the design text: what vet checks (licence, advisories via the RustSec database offline snapshot, yanked versions, duplicate versions, new transitive dependencies in a change, maintenance signals), output in the envelope, a rule for unvetted new dependencies in a ticket's diff. Read the cli.md and build-test-ci.md passages first; if they disagree or are thin, write the spec into the ticket before coding.
