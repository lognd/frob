+++
id = "01M40AKKXBN7K30090V7KQSA8Z"
title = "Attestation evidence: a person's signed statement as evidence for criteria that no tool can measure"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T07:28:11Z"
updated = "2026-10-03T10:19:19Z"
idempotency_key = "m2-rel-attestation-evidence"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/frob-evidence/**", "crates/frob/src/**", "crates/frob/tests/**", "crates/frob-pm/**", "crates/gob-diagnostics/**", "crates/gob-cli/src/**", "crates/frob-release/**"]

[[acceptance]]
text = "Given an attester at a TTY, when they attest a milestone criterion with a statement and facts, then the criterion is bound and show marks it as attested"
bound = false

[[acceptance]]
text = "Given an agent environment or a non-attester identity, when attestation is attempted, then it is refused with a remedy"
bound = false

[[acceptance]]
text = "Given a milestone criterion with bound evidence, when it is removed, then the lost evidence is reported"
bound = false
+++

Follow-up of ~K0YKGNK, whose description asked for manual-attestation evidence that was not built. Some exit criteria cannot be measured by a tool (0.532.0: two outside repositories managed for two cycles with no ledger data loss; 1.0.0: 30 days managing three repositories). Add an attestation provider for ticket and milestone evidence: the statement text, the attesting identity, and the facts it rests on (links, commits, ticket ids); it counts as measured only when made by an identity in [evidence] attesters (materialized, default the repository owner) and only from a TTY without an agent marker (an agent can never attest, security.md 2.3 pattern); the record is visibly an attestation in show, brief, release status and the done report, never presented as a tool measurement. Also add the lost-evidence report to milestone criterion remove, as ticket update has.
