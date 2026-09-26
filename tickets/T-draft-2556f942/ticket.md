---
id: T-draft-2556f942
title: strata/source `frob:waive SYS113` applies on one run and not the next identical
  run (cache); make waiver resolution deterministic
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
flavour: null
due: null
rank: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/gates/_waive.py
- src/frob/strata/_selfconform.py
- src/frob/graph/cache.py
- tests/unit/strata/test_sys113_waiver_determinism.py
- docs/modules/gates.md
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
Source: logand.app-v2 FROBLEMS.md (peer coordinator report, 2026-09-26, frob 0.531.1.dev332). Reproduction lives in that repo (read-only for frob agents); the frob-side positive control must be a fixture here.

F-400: with identical text in design/logand-app.strata (form (a): `// frob:waive SYS113 reason=... follow_up=...` as the last line inside the node block; form (b): the strata-native `waive "SYS113" reason "..." follow_up="...";`), one `frob sys audit` run showed all browser/backend SYS113 gaps waived and a later run of the same text showed none waived (all 36 back). Also: form (b)'s grammar needs `reason "text"` (space, not `=`) and refuses an escaped quote inside the string. Deliver: (1) find the non-determinism (graph/strata cache keyed without the waiver text? node-level waiver parsed only on a cold cache?) with a test that runs audit twice with and without the cache and asserts identical waived sets; (2) accept `reason=` and escaped quotes in the strata `waive` statement or document the exact grammar in the error; (3) `frob sys audit --explain SYS113:<node>` prints which waiver (form, file, line) it matched or why none did.
