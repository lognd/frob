+++
id = "01M41RHBJ03PGD6JY0J6JTAH9Q"
title = "TICK004 is an Error; ticket doctor --fix scrubs absolute home paths from existing ledgers with a forward commit"
type = "security"
category = "in-progress"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-10-03T20:50:51Z"
updated = "2026-10-03T21:22:03Z"
scope = ["crates/frob-ledger/**", "crates/frob-evidence/src/scrub.rs", "docs/reference/rules/TICK004.md", "docs/design/tickets.md", "crates/frob/src/ticket/doctor_cmd.rs", "crates/frob/tests/ticket_scrub.rs", "docs/reference/rules/README.md"]

[[acceptance]]
text = "Given a ledger file containing an absolute home path, when frob check runs, then TICK004 is an error"
bound = true

[[acceptance]]
text = "Given a ledger with lease reasons and evidence transcripts holding absolute paths, when ticket doctor --fix runs, then one commit scrubs them, every ticket still folds with the same evidence binding, and TICK004 reports nothing"
bound = true

[[acceptance]]
text = "Given a scrubbed ledger, when ticket doctor --fix runs again, then it changes nothing"
bound = true
+++

Owner decision 2026-10-03: TICK004 (absolute home path in a committed ledger file, ~33PZ67A) is an Error, and existing ledgers are cleaned with a forward commit, never by rewriting git history.

1. TICK004 severity Warn -> Error; regenerate its rule page.
2. ticket doctor --fix (the existing ledger repair verb) gains a scrub repair: every ledger file containing an absolute home path has those paths replaced in place, using the same PathScrub rules ~33PZ67A added for new evidence (worktree root -> <worktree>, repository root -> <repo>, home -> ~, path-boundary aware), and for paths of other worktrees of this repository (the old lease reasons name sibling worktrees such as frob-v2-wt/7HWFTBP) the worktree-relative form frob-v2-wt/7HWFTBP. Anything still matching TICK004 after that (a foreign home path) becomes ~other/... or is reported, not guessed.
3. Integrity: some events carry digests or artifact URIs over the captured text. Decide and document (tickets.md) what a scrub does to them: recompute the digest over the scrubbed text and record a doctor repair event naming the files and the reason, so the change is auditable; a scrubbed record must still fold and still count as evidence where it did before. Artifacts stored outside the ledger (.git/frob/artifacts) are local and untouched.
4. The repair is one commit through the ledger's normal write path (the same path doctor --fix uses today), idempotent (a second run changes nothing), and reported (files changed, counts).
