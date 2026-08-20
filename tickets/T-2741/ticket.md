---
id: T-2741
title: Fix 2 remaining PII012 waiver-placement gaps T-2712 could not touch
state: done
kind: bug
origin: human
created: '2026-08-20'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/serve/_socketd.py
- tests/test_capability_registry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002: comment-only waiver placement fix, no executable behavior change
    for a mutation test to prove'
  actor: logan
  at: '2026-08-20'
  old_length: 1900
  new_length: 2211
evidence:
- tests/test_capability_registry.py::TestBoto3NextTierServiceBindingResolution::test_secretsmanager_put_secret_value_reports_net_mutate
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 79c9e4a436160f20b1c1f7712b676ec450784e0e
---
T-2712's detector-side fixes (symref path-prefix, directive-comment
continuation exclusion, single-char-TLD email exemption, wrapped
frob:secret-fake marker reconstruction) in
src/frob/gates/_pii_structural/** resolved 19 of the 21 unwaived
PII010/011/012 findings T-2696's symref population exposed. Two sites
remain unwaived and require a same-line disposition OUTSIDE that
scope, so T-2712 could not touch them:

1. src/frob/serve/_socketd.py:530 -- PII012 on `allow_reuse_address =
   True`. A `frob:waive PII012` comment sits directly above it (lines
   527-529), but the DSL's comment.following binding does not target
   plain class-attribute assignments the way it targets a def/class:
   the waiver's `waiver.src` resolves to the NEXT real symbol
   (`_DaemonServer.__init__`), not the class itself, while the
   violation's own symref (via enclosing_qualname, correctly, since
   there is no enclosing function) is just `_DaemonServer`. Two
   different strings, never a match under T-2438's exact-match rule.
   This is a real false positive (SO_REUSEADDR, not a person's
   address) -- needs either a DSL-aware waiver placement fix or
   confirmation from someone who owns the comment-binding DSL
   (src/frob/lang or src/frob/strata, not _pii_structural) on the
   correct way to target a plain assignment statement.

2. tests/test_capability_registry.py:902 -- PII012 on
   `test_secretsmanager_put_secret_value_reports_net_mutate` (matches
   "secret" keyword via "secretsmanager"). No existing waiver at this
   site at all -- this one is a plain missing-disposition case, not a
   DSL mismatch: it is a false positive (AWS Secrets Manager API
   capability-scan test, not a real secret) and just needs a
   `frob:waive PII012 reason="..."` comment added above the def.

Both fixes are single-comment-line edits with no detector code
involved; scope should be exactly these two files.

frob:waive BUG002 reason="T-2741 is a comment-only waiver-placement fix (moving/adding frob:waive PII012 directives) with no behavior change to the code paths themselves -- there is no wiring for a mutation-killing repro to reach, since the fix is entirely in comment placement/content, not executable logic."