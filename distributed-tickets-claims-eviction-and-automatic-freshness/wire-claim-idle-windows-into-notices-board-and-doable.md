+++
id = "01M5DCZ3PVHP2ZNP9SVYFFQSVP"
title = "Wire claim idle windows into notices, board and doable"
type = "task"
category = "todo"
priority = "medium"
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T19:35:13Z"
updated = "2026-10-20T19:35:13Z"

[[links]]
kind = "blocked-by"
target = "01M5CW04TYF2SQ101BQB1BGNPJ"
+++

Follow-up of ~FGTCB9E: feed ClaimWindows::status (frob_ledger::claim_window) with the observed first-seen times from claim activity observation; show holder_notice/aggregate_holder_notice on the next verb, others_notice on board and doable, add frob claim notices with acknowledgement (acked rank), read ticket field claim_idle_days and the holder kind (FROB_AGENT) from the lease event, and use FrobConfig.claims. See distributed-tickets.md 4.4.
