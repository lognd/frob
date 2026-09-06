---
id: T-4079
title: 'L-1: document.cookie write pattern for client_storage scanner'
state: queued
kind: bug
origin: agent
created: '2026-09-06'
priority: low
parent: T-4071
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_capability_registry/_dangerous_ops_other.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a document.cookie = assignment in TS source, when frob vet's capability
    scan runs, then it is recognized as client_storage
  evidence: []
- text: given the sessionStorage pattern already registered, when this ticket is worked,
    then it is NOT re-implemented as if missing -- only the cookie-write gap and the
    unverified file-walk hypothesis are addressed
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
L-1 (F-273). VERIFIED, and this PARTIALLY REFUTES the consumer's own stated hypothesis rather than confirming it: src/frob/vet/_capability_registry/_dangerous_ops_other.py already registers "sessionStorage" (and "localStorage") as literal client_storage patterns for typescript (lines ~74-84) -- so the scanner DOES recognize sessionStorage.* calls as client_storage in principle. That half of their two hypotheses ("the scanner does not recognise sessionStorage") is not supported by what the registry actually contains.

WHAT IS CONFIRMED MISSING: git grep for "document.cookie" or a "cookie" pattern anywhere in src/frob/vet/_capability_registry/ found NOTHING -- there is no registered pattern for a document.cookie WRITE (or read) at all. The consumer's own note that client.ts IS flagged for a document.cookie read is therefore not explained by any pattern in this registry; it may be a coincidental match against something else in client.ts, or the registry has changed since their measurement. This needs verification against the actual scanner behavior on a real document.cookie assignment before concluding what the true gap is.

THE CONSUMER'S SECOND HYPOTHESIS IS UNVERIFIED FROM THIS SIDE: whether frontend/src/mocks/** is being skipped as test-adjacent cannot be checked from frob's own source alone -- it depends on the consumer's own frob.toml scan-path configuration, not on frob's registry. Their own F-283 (referenced in the same FROBLEMS.md) already notes the specific file in question, mocks/handlers.ts, is not even tracked on the branch being measured against, which independently explains a non-finding without needing a scanner bug at all.

PROPOSED WORK, narrowed by the above: (1) add a document.cookie assignment pattern (`document.cookie =`) to the client_storage registry for typescript -- this is confirmed missing and cheap to add regardless of the rest. (2) do NOT assume the sessionStorage recognition is broken; if the consumer re-measures from an unparked branch (their own pending F-283 follow-up) and it still fails to fire, that is a second, separate bug in the SCANNER'S FILE-WALK rather than its pattern table, and should be filed then with the actual repro.
