+++
id = "01M40THSWB75TFY8949M4T7MXR"
title = "Digests hash raw worktree bytes, so core.autocrlf checkouts look changed (EXC005, DRIFT)"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T12:06:48Z"
updated = "2026-10-03T15:28:30Z"
idempotency_key = "m2-rel-digest-git-normalized"
labels = ["milestone:2", "area:release"]
scope = ["crates/gob-git/**", "crates/gob-lock/**", "crates/frob-ack/**", "crates/gob-text/**", "crates/frob-ledger/**", "crates/gob-walk/**", "crates/gob-symbols/src/pipeline.rs", "crates/gob-symbols/Cargo.toml", "changelog.d/01M40THSWB75TFY8949M4T7MXR.fixed.md", "crates/frob-obligations/tests/repo.rs", "docs/design/git-io.md"]

[[links]]
kind = "blocked-by"
target = "01M40T3VA5Y86ZQH234NTKAXC1"

[[acceptance]]
text = "Given core.autocrlf=true and a CRLF checkout of an acked file with no content change, when check runs, then no EXC005 or DRIFT001 finding appears"
bound = true

[[acceptance]]
text = "Given a real content change, when check runs, then it is still reported"
bound = true
+++

Reported from the cloc repository (FROB_FEEDBACK.md item 7): with core.autocrlf=true a fresh frob work worktree checks files out with CRLF while they were acked from an LF copy, so EXC005 reports 'changed since it was attested' although git diff is empty; re-acking is the only workaround. Every content digest frob computes for comparison with recorded state (frob.lock symbol and section digests, attestation digests, cache keys over file content) must be computed over the content as git would store it: apply the repository's clean conversion (core.autocrlf, core.eol, .gitattributes text and eol, filters) through gix, the same normalization as ~NTKAXC1 (SCOPE001 symlinks) uses for the worktree side; one shared helper in gob-git, used everywhere. Tests: a repository with core.autocrlf=true and a CRLF checkout: no EXC005 or DRIFT001 change; a real content change: still reported.
