---
id: T-3220
title: frob clean --deep wholesale-deletes .frob/, which now also deletes rapid-debt.jsonl
  (T-2997)
state: done
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/clean/_rules.py
- src/frob/clean/_core.py
- tests/test_clean.py
- docs/modules/clean.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_clean.py
  reason: test file for the new protection logic in _core.py/_rules.py
  actor: logan
  at: '2026-08-28'
- op: add
  glob: docs/modules/clean.md
  reason: new frob:doc anchor for TIER3_PROTECTED_PATHS
  actor: logan
  at: '2026-08-28'
body_changes:
- mode: append
  reason: condense deep-clean-protects rationale into T-3220 body, keep frob:doc anchor
  actor: logan
  at: '2026-09-19'
  old_length: 811
  new_length: 1853
evidence:
- tests/test_clean.py::test_deep_clean_preserves_rapid_debt_jsonl
- tests/test_clean.py::test_deep_clean_still_wholesale_removes_frob_without_the_ledger
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: c5ea05d6947c0c69d6ef31d6b80bbee987259f39
---
T-2997 moved rapid-debt.jsonl's write target from the tracked repo root to .frob/rapid-debt.jsonl (gitignored). frob clean --deep (tier 3, src/frob/clean/_rules.py _TIER3_PATTERNS) shutil.rmtrees the ENTIRE .frob/ directory, which now includes this debt ledger -- a real data-loss mode T-2997's own acceptance bar ('do not silently discard it') explicitly warns against, discovered while verifying T-2997's 'confirm nothing depends on reading it' requirement rather than assumed. Decide and implement a fix: either carve rapid-debt.jsonl out of the tier-3 walk (an explicit exclude pattern), or move its write target outside .frob/'s clean --deep blast radius, or get an explicit owner sign-off that clean --deep may destroy this telemetry too (matching the T-2997 tradeoff already accepted for clone-survival).

<!-- narrative-moved:src/frob/clean/_rules.py:55:T-3220 -->
frob:ticket T-3220
: Paths (relative to the scan root) that `_TIER3_PATTERNS`' wholesale
: `.frob` match must never carry into `clean`'s actual removal, even
: though the glob itself matches the whole directory. T-2997 moved
: `rapid-debt.jsonl` (a durable RECORD -- the T-1681 rapid-profile debt
: ledger, not a regenerable measurement cache) from the tracked repo
: root into `.frob/` specifically because `.frob/` used to be entirely
: disposable per-checkout scratch state; `frob clean --deep` still
: `shutil.rmtree`s that whole directory unconditionally, which now
: means "regenerate `.frob/`'s caches" also silently destroys the one
: piece of `.frob/` content that is NOT regenerable -- a real data-loss
: mode T-2997's own acceptance bar ("do not silently discard it")
: explicitly warned against. `frob.clean._core._protect_excluded_paths`
: is what actually keeps this out of a DEEP clean's removal set; this
: tuple is the single place that decides WHAT is protected.