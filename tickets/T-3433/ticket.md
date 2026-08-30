---
id: T-3433
title: 'PORT001-IDENT: src/frob/graph/cache.py hardcodes package name in fingerprint
  tuple'
state: in-progress
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/cache.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: record no-behavior-change front door for BUG002
  actor: logan
  at: '2026-08-29'
  old_length: 1005
  new_length: 1311
- mode: append
  reason: record no-behavior-change front door for BUG002
  actor: logan
  at: '2026-08-29'
  old_length: 1311
  new_length: 1617
evidence:
- tests/test_graph.py::TestBuildIncremental::test_fingerprint_bump_rebuilds
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-3275 (PORT001 rescope, do-not-fix-here instruction): T-3275's widened PORT001 scan found 16 PORT001-IDENT hits repo-wide; 15 of 16 are legitimate self-reference (frob invoking its own 'python -m frob' CLI, or maintainer-facing diagnostic message text naming a real file). The one genuine candidate: src/frob/graph/cache.py:104 -- _NON_LANGUAGE_FINGERPRINT_PACKAGES = ("frob", "strata-core") hardcodes this repo's own installed package names as the non-language cache-fingerprint inputs, instead of resolving them from the scanned repo's own declared dependencies/config. Evaluate whether this is genuinely a portability bug (would silently omit a consumer repo's own equivalent packages from its fingerprint) or an intentional frob-specific list (if strata-core is always frob's own native companion regardless of host repo, it may be a legitimate self-reference like the already-allowlisted _pii_structural/_self_match.py) -- decide and either allowlist with a stated reason or fix.



frob:no-behavior-change reason="T-3433 is a review-and-decide ticket: the fingerprint tuple is confirmed as legitimate self-reference (frob's own analyzer identity, not the scanned repo's), so the fix is documenting that decision in place, not changing code behavior. No caller-visible output changes."



frob:no-behavior-change reason="T-3433 is a review-and-decide ticket: the fingerprint tuple is confirmed as legitimate self-reference (frob's own analyzer identity, not the scanned repo's), so the fix is documenting that decision in place, not changing code behavior. No caller-visible output changes."