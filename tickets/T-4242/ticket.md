---
id: T-4242
title: 'SYS111: a declared grant with no lock entry at all (an unlocked ceiling) must
  fail as loudly as a changed one'
state: queued
kind: bug
origin: agent
created: '2026-09-07'
priority: medium
parent: T-4135
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_sys.py
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
Consumer F-326/H2-4: a repo-side test (via_sha256) was invented to patch a gap in SYS111's own ratchet -- a repo-side test guarding a repo-side lock file is circular, since the same agent can edit both. The lock must enumerate a closed set: every subject present in the source must appear in the lock, or the lock must name the exemption explicitly; a missing entry defaulting to 'not my concern' is never safe for a ratchet. Adjacent to T-3990 (SYS111 lock: digest the declared via glob list, not just a count -- a magnitude/content-change defect) and T-3833 (SYS111 ratchet fires the moment a via-list is introduced) -- this is a third, distinct SYS111 defect: entry ABSENCE, not content or introduction-timing. Fixture-testable: YES, frob's own SYS111/via_sha256 mechanism.