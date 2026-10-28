+++
id = "01M5D9NM6D3DSGD980M52CRMYV"
title = "Envelope-wide freshness field and E-SYNC-STALE refusal in doable/work/land"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T18:37:37Z"
updated = "2026-10-28T12:55:42Z"
labels = ["no-story"]
scope = ["crates/gob-diagnostics/src/envelope.rs", "crates/frob/src/ticket/mod.rs"]
+++

found while working ~8PE22M6: freshness assessment (refresh_cmd/freshness.rs) only reaches refresh; promote to shared module, add envelope field, wire verbs, feed real diverged/ledger_conflict signals. Do after ~EV5KK0X lands.

no-story: internal engineering task in gob-diagnostics; it has no direct user-visible outcome of its own, which is carried by its parent/epic or by the release notes.
