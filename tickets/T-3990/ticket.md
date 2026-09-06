---
id: T-3990
title: 'SYS111 lock: digest the declared via glob list, not just a count'
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: medium
parent: T-3984
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
acceptance:
- text: given the existing lock format, when this ticket's first step runs, then it
    reports whether the via glob list content (not just a count) is already digested,
    before any code change
  evidence: []
- text: given the gap is confirmed real, when fixed, then widening a may's via glob
    list with no matching ticketed lock edit is flagged by SYS111 (or a sibling rule)
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
F-202 (T-3984 item 7). VERIFIED: SYS111 (capability_ratchet_violations, src/frob/gates/_sys.py line ~674) already exists and enforces the capability ratchet ceiling itself. What is unverified/likely missing: whether the SYS111 lock entry (the capability-via-ratchet lock file, referenced elsewhere as docs/design/registry/capability-via-ratchet.lock.json) digests the DECLARED VIA GLOB LIST for a may grant, or only the capability name/count. src/frob/gates/_sys.py's own docstring near line 628 mentions "MayGrant.via tuple -- a count of declared globs/symbols," which suggests the lock may track a count rather than a content digest -- a count-only lock would let someone REPLACE the declared via globs (same count, different files) without the lock catching it.

FINDING THIS WOULD HAVE CAUGHT: silently widening a `may` grant's via glob list (e.g. adding a new file to the set of places allowed to exercise a capability) without the lock file registering it as a change, because the lock only checks a count or the capability name rather than digesting the actual glob list content. Without this, "a may is a ceiling" is unenforced -- the ceiling can move without anyone noticing or having to touch a ticketed lock edit.

FIRST STEP: read the actual lock file format and MayGrant.via handling in full (not just the docstring reference) to confirm whether it already digests the glob list content or only a count/name, before writing any new check -- this determines whether the gap is real or already closed.
