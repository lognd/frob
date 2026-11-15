+++
id = "01M7EX824YW7XZ0183N96J8B58"
title = "attestation events: bind to an attester identity so they cannot be forged"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:10:22Z"
updated = "2026-11-15T06:10:23Z"
labels = ["no-story"]

[[acceptance]]
text = "An attestation from a non-listed attester is rejected (test)"
bound = false
+++

Source: frob-audit-core.md M7. Evidence: crates/frob-evidence/src/record.rs:281-294 and attestation.rs accept an attestation event whose attester is free text. Remedy: verify the attester against [evidence] attesters and the commit author. Files: those two files.
