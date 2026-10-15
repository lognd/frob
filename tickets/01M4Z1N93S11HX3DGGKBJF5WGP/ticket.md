+++
id = "01M4Z1N93S11HX3DGGKBJF5WGP"
title = "Land train: close N tickets in one ledger commit on green fast-forward"
type = "task"
category = "todo"
priority = "high"
points = 5
parent = "01M4Z1KTKEVF53GWM6ZN7PFN4Q"
reporter = "lognd"
created = "2026-10-15T05:48:15Z"
updated = "2026-10-15T05:48:15Z"
idempotency_key = "train-ledger-close"
labels = ["area:land"]
scope = ["crates/frob-ledger/**,crates/frob-land/src/train_close.rs"]

[[acceptance]]
text = "Given a green batch, when it lands, then all tickets close in one ledger commit"
bound = false

[[acceptance]]
text = "Given a base that moved, then the CAS retries and either lands or reports E-LAND-STALE per policy"
bound = false

[[acceptance]]
text = "Given a crash after fast-forward, then resume closes the remaining tickets"
bound = false
+++

On a green candidate: fast-forward base to the candidate oid (compare-and-swap, same bounded retry as ledger commits) and close all member tickets, with events and LAND-PROOF per ticket, in ONE ledger commit. Partial failure leaves base advanced with the remaining tickets recorded as pending-close in train state, never lost.
