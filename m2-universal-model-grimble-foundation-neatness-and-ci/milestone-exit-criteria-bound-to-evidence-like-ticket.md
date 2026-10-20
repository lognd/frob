+++
id = "01M4069RACAQ8Z2C8APK0YKGNK"
title = "Milestone exit criteria bound to evidence like ticket acceptance"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:12:53Z"
updated = "2026-10-03T15:28:18Z"
idempotency_key = "m2-rel-milestone-evidence"
labels = ["milestone:2", "area:release"]
scope = ["crates/frob-pm/src/milestone/criteria.rs", "crates/frob-evidence/src/**", "crates/frob-pm/src/**", "crates/frob-pm/tests/**", "crates/frob/src/**", "crates/frob/tests/**", "docs/design/releases.md", "docs/reference/cli/frob.md"]

[[links]]
kind = "blocked-by"
target = "01M4069R5RH6KRMMNQA76XZ8VG"

[[acceptance]]
text = "Given a milestone criterion and a passing evidence record accepting it, when the milestone is shown, then the criterion is bound with the evidence id"
bound = true

[[acceptance]]
text = "Given a criterion with no evidence, when shown, then it is unbound"
bound = true
+++

Reuse the ticket criterion binding path (frob-evidence) so a recorded evidence record can accept a milestone criterion (`frob test --accepts MILESTONE:N` or the existing accepts mechanism extended); show prints bound state; manual-attestation evidence (an owner statement event) is allowed for criteria no command can prove, such as the outside-repository criterion.
