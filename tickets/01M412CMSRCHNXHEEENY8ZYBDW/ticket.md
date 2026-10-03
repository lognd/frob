+++
id = "01M412CMSRCHNXHEEENY8ZYBDW"
title = "Audited --no-changelog exemption for changes with no user-visible effect"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T14:23:48Z"
updated = "2026-10-03T14:33:07Z"
idempotency_key = "m2-rel-no-changelog-exempt"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/frob-evidence/src/done.rs", "crates/frob-release/src/rel003.rs", "crates/frob/src/ticket/**", "crates/frob-land/**", "crates/frob/tests/close_guards.rs", "crates/frob-ledger/src/event.rs", "crates/frob-ledger/src/fold.rs", "crates/frob-ledger/src/brief.rs", "crates/frob-check/src/options.rs", "crates/frob-check/src/snapshot.rs", "crates/frob-check/src/product.rs", "crates/frob-release/src/status.rs", "crates/frob/src/release_cmd.rs", "crates/frob/tests/release_status.rs", "crates/frob/tests/remedies.rs", "crates/frob/tests/check_verb.rs", "docs/design/tickets.md", "docs/design/documentation.md"]

[[acceptance]]
text = "Given a ticket with no fragment, when close runs with --no-changelog and a reason, then it closes and records a changelog-exempt event"
bound = false

[[acceptance]]
text = "Given --no-changelog without a reason, when close runs, then it is a usage error"
bound = false
+++

Split from ~HE2EX99 criterion 2 (removed there because it was never built): changelog_fragment is required for every done close, but some changes have no user-visible effect (design documents, internal refactors, test-only changes), and a fragment for them would fill CHANGELOG.md with noise. Add an audited exemption, like the evidence bypass: `ticket close` and `land` accept `--no-changelog --reason TEXT`, recorded as an event (kind changelog-exempt) and shown in brief and the done report; REL003 under check --ticket treats an exempted ticket as clean; release status lists exempted tickets in the milestone so a reviewer sees them. No exemption by file type: the person or agent states why. Test: a ticket closed with --no-changelog and a reason closes and records the event; without a reason it is a usage error; REL003 is clean for it.
