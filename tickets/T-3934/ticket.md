---
id: T-3934
title: 'CI red: T-3787 target_branch kwarg breaks 6 land-proof tests on all platforms'
state: queued
kind: bug
origin: human
created: '2026-09-05'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_ticket_land_proof_claims.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Run 34005559354 (28a511c9f) fails on ubuntu, macOS AND windows with 6 identical failures:

TypeError: <lambda>() got an unexpected keyword argument 'target_branch'

in tests/test_ticket_land_proof_claims.py -- TestLandProofClaimsOutcome and TestLandProofOrphanEvidenceOutcome. Commit 68fe479f7 (land T-3787, non-main target branch) added a target_branch kwarg to the landing call site; the test doubles are lambdas with the old signature, so every one raises on call.

This is a landed regression from our own most recent commit and is the single largest shared cause of red across all three platforms.

FIX: update the test doubles to accept target_branch. Do NOT change production code to restore the old signature -- T-3787's kwarg is intended. Assert the doubles receive the value they should rather than swallowing it with a bare catch-all, so the test still constrains the call.

ACCEPTANCE: the 6 named tests pass locally; no other test in the file regresses.