+++
id = "01M6KN3351QXZFGKMZ23C21CRN"
title = "evidence: stamp design digests on non-attestation milestone captures and frob-tests capture"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-04T16:08:21Z"
updated = "2026-11-05T16:53:01Z"
idempotency_key = "followup-2v265h6-remainder"
labels = ["no-story"]
scope = ["crates/frob/src/milestone_evidence_cmd.rs", "crates/frob-tests/src/verb.rs", "crates/frob-evidence/src/design.rs"]

[[acceptance]]
text = "milestone captures from every provider carry design digests"
bound = false

[[acceptance]]
text = "frob-tests capture carries design digests"
bound = false

[[acceptance]]
text = "design::stamp merges instead of overwriting"
bound = false
+++

Remainder of 2V265H6: only attestations are stamped. Nextest/command/other milestone captures and the frob-tests capture are not. Also design::stamp assigns rather than merges, so an attestation stamp can be overwritten by the ticket-level stamp on evidence add.
