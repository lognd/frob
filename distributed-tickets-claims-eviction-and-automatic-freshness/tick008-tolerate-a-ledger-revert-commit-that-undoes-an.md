+++
id = "01M5XF9XTH9F34VCAVDKJ6VSYA"
title = "TICK008: tolerate a ledger revert commit that undoes an import (or record it as an allowed commit)"
type = "bug"
category = "in-progress"
priority = "high"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-27T01:23:56Z"
updated = "2026-10-27T01:59:16Z"
scope = ["crates/frob-check/**", "docs/reference/rules/TICK008.md", "crates/frob-ledger/**", "crates/frob/tests/it/ticket_moves.rs"]

[[acceptance]]
text = "TICK008 does not report a ledger commit that is a git revert of an earlier ledger commit (or carries an explicit allowed-commit trailer), proven by a test using the e958528049 shape"
bound = true

[[acceptance]]
text = "A genuine non-reindex move or edit of an event still fires TICK008"
bound = true
+++

Revert e958528049 on frob-tickets (chore(tickets): revert duplicate crunk import) touches 427 event files and makes TICK008 report an error on every ticket check and land (currently shown as pre-existing). Find the rule implementation (grep TICK008 under crates/) and fix; scope above is a guess, widen the lease as needed.
