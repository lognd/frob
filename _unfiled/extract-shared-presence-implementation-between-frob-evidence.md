+++
id = "01M6REGJ1EDACXZ22GZHAW6R9X"
title = "Extract shared Presence implementation between frob-evidence and grimble"
type = "task"
category = "todo"
priority = "low"
points = 3
reporter = "lognd"
created = "2026-11-06T12:49:35Z"
updated = "2026-11-06T12:49:35Z"
labels = ["no-story"]
+++

DUP004 accepted (via frob:accept + frob ack) on Presence.from_parts and Presence.reasons in crates/frob-evidence/src/attestation.rs, which mirror grimble's Presence. Extract a shared crate or module and drop the accepts.
