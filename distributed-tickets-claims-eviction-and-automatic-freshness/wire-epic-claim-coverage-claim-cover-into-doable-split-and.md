+++
id = "01M5DJ4K69T67D50C19B4NY6RM"
title = "Wire epic claim coverage (claim_cover) into doable, split and move"
type = "task"
category = "todo"
priority = "medium"
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T21:05:36Z"
updated = "2026-10-20T21:05:36Z"
+++

Follow-up of ~J2S1737: crates/frob-ledger/src/claim_cover.rs is pure. Feed CoverMap from the ledger folds and live lease claims into doable exclusion (offline, cached view), emit split_notice on child create/parent change and move_warning on ticket update --parent.
