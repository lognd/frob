+++
id = "01M40WS6200M99J09D5XGAS05X"
title = "Close guards ignore [pm] done_requires: a ticket closed as done with no evidence"
type = "bug"
category = "in-progress"
priority = "critical"
points = 5
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T12:45:47Z"
updated = "2026-10-03T13:24:43Z"
idempotency_key = "m2-rel-done-requires-enforced"
labels = ["milestone:2", "area:release", "release:0.532.0"]
scope = ["crates/frob-evidence/**", "crates/frob-ledger/src/guards*", "crates/frob-land/**", "crates/frob/src/ticket/**", "crates/frob/src/lib.rs", "crates/frob/tests/close_guards.rs", "crates/frob/tests/ticket.rs", "crates/frob/tests/wiring.rs", "crates/frob/tests/release_status.rs", "crates/frob/tests/e2e_init_loop.rs", "crates/frob/tests/common/mod.rs", "changelog.d/01M40WS6200M99J09D5XGAS05X.fixed.md", "docs/design/tickets.md", "docs/design/pm-enforcement.md"]

[[acceptance]]
text = "Given a chore with an unbound criterion, when land or close runs, then it is refused naming the criterion and the bypass"
bound = true

[[acceptance]]
text = "Given --no-evidence --reason, when close runs, then it closes and records the bypass event"
bound = false

[[acceptance]]
text = "Given the running frob binary as a command evidence tool, when evidence add runs, then it is accepted without listing it in allowed_tools"
bound = false
+++

Reported from the cloc repository (FROB_FEEDBACK.md item 9): land closed a chore ticket as done with zero evidence although [pm] done_requires lists criteria_evidenced; the only close guard (frob-evidence has_evidence) requires one measured record for code-changing types and ignores done_requires entirely. A configured requirement nothing enforces is a silent gap. Fix: close guards enforce every entry of [pm] done_requires: criteria_evidenced (every acceptance criterion bound by measured passing evidence or an attestation, through the moved-map remap; a ticket with no criteria passes this predicate but is reported as a warning), no_open_children, docs_touched_or_excepted and objective_target_met as specified in pm-enforcement.md 3 (if one cannot be evaluated yet, close refuses with Unresolved naming it rather than silently passing; changelog_fragment stays with ~HE2EX99 but must also refuse until that lands, unless removed from done_requires); --no-evidence --reason remains the audited bypass for criteria_evidenced. Also: the running frob and grimble binaries are allowed evidence tools by default (frob check --ticket is the natural proof for frob-shaped criteria), so [evidence] allowed_tools need not list them. Tests: a chore with an unbound criterion is refused with the criterion named; bypass with reason closes and records the bypass event; all criteria bound closes; frob as a command-provider tool is accepted.
