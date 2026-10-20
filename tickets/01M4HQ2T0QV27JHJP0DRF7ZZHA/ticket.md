+++
id = "01M4HQ2T0QV27JHJP0DRF7ZZHA"
title = "ticket triage and ticket scrub support the ticket-branch layout (today they refuse with a clear error)"
type = "story"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-10T01:33:17Z"
updated = "2026-10-20T15:33:37Z"
scope = ["crates/frob/src/ticket/**", "crates/frob-ledger/src/**", "changelog.d/**", "crates/frob-ledger/tests/ledger.rs"]

[[acceptance]]
text = "Given ref_mode = orphan, when ticket triage list/accept and ticket scrub run, then they work on the branch layout with the same results as the dir layout"
bound = true
+++

Deferred by ~H3WVSYM.
