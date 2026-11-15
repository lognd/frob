+++
id = "01M7EXTYGA34B7M2P4NKSR1PYT"
title = "crunk parity: compare effect file contents per E2E replay step"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:20:41Z"
updated = "2026-11-15T06:20:41Z"
idempotency_key = "crunkplan-60870b2be9c6"
labels = ["no-story"]

[[acceptance]]
text = "a fix step writing wrong bytes fails the replay (mutation test)"
bound = false
+++

Source: ~/projects/frob-audit-grimble-crunk.md, finding M3.
Evidence: replay checks only that effect files exist
Remedy: compare bytes with LF normalisation; per-entry divergence field effects-content
Crates/files: crates/crunk/tests/e2e/replay.rs:205-235, tests/crunk-parity/divergences.toml
Verify against HEAD first; the audit ran on a stale binary.
