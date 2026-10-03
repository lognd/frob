+++
id = "01M410A4XR556D484CYYP2Y2R3"
title = "A ticket's own changelog fragment is always in scope and never contends for a lease"
type = "task"
category = "in-progress"
priority = "high"
reporter = "lognd"
created = "2026-10-03T13:47:29Z"
updated = "2026-10-03T13:52:23Z"
labels = ["release:0.532.0"]
scope = ["crates/frob-check/src/scope.rs", "crates/frob-lease/**", "crates/frob-check/tests/check.rs", "crates/frob-release/src/fragment.rs", "crates/frob-release/src/lib.rs"]
+++

found while working ~3TXB8SR: another ticket leasing changelog.d/** blocks every other ticket from widening to its own <ULID>.<type>.md, so check --ticket reports SCOPE001 on the fragment the close guard requires. Fragments are one file per ticket, so add changelog.d/** to [lease] shared_files or have the scope check always allow the ticket's own fragment.
