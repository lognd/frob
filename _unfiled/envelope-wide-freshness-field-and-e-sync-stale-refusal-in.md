+++
id = "01M5D9NM6D3DSGD980M52CRMYV"
title = "Envelope-wide freshness field and E-SYNC-STALE refusal in doable/work/land"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-20T18:37:37Z"
updated = "2026-10-20T18:37:37Z"
scope = ["crates/gob-diagnostics/src/envelope.rs", "crates/frob/src/ticket/mod.rs"]
+++

found while working ~8PE22M6: freshness assessment (refresh_cmd/freshness.rs) only reaches refresh; promote to shared module, add envelope field, wire verbs, feed real diverged/ledger_conflict signals. Do after ~EV5KK0X lands.
