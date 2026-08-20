---
id: T-2712
title: Re-triage 20 newly-unwaived PII010/011/012 findings after T-2696's symref population
state: in-progress
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_pii_structural/**
- tests/test_pii_structural_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_pii_structural_gate.py
  reason: evidence for the PII010/011/012 re-triage fixes lives in this gate's own
    test file; the pii_structural/** scope covered the source fix but not its test
  actor: logan
  at: '2026-08-20'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2696 populated `Violation.symref` for PII010/011/012 (a genuine
per-symbol gap, distinct from PERF's intentionally file-scoped design --
`Violation.symref`'s own docstring in `src/frob/gates/_models.py` never
names PII010/011/012 among the intentionally file-scoped rules). That
change is real, tested engineering (`enclosing_qualname` in
`src/frob/gates/_pii_structural/_node_index.py`, reusing the SAME
`_NodeIndex` bucketing pass every PII sub-scan already builds, T-1209 --
no second AST walk, no re-parse) and is kept OUT of this ticket
deliberately, mirroring the T-1659 (fix) / T-1666 (classify) precedent
this whole family already established for OPAQUE001.

Measured consequence of the fix (T-2696's own re-run, per its own final
instruction): `frob check`'s waiver matching became symbol-exact for
PII010/011/012 wherever a symref now resolves (`_match_waiver`'s
`_canonical_symref`-normalized exact-match path, T-2438), so every
existing `frob:waive PII010/011/012 reason="..."` comment that was
matching only via the OLD file-wide fallback now needs to sit ABOVE the
actual symbol it is meant to cover, or it silently stops matching.

Before this fix: 1 unwaived PII012 error repo-wide (T-1666's own
baseline measurement).
After this fix: 20 unwaived findings repo-wide (measured via
`run_gates(GateConfig(gates=frozenset({"pii_structural"})))`,
counting `v.waived is None` for `v.rule in ("PII010","PII011","PII012")`
-- 15 PII012, 4 PII011, 1 PII010... note: re-count at pickup time, this
was measured once, immediately after T-2696 landed, and is disclosed AS
A MEASUREMENT, not re-verified against a fresh HEAD by whoever picks
this ticket up).

Every one of the newly-unwaived findings is either:
1. A pre-existing `frob:waive` comment now sitting at the wrong site
   relative to its intended symbol (needs to move, not a new
   disposition), or
2. A finding that was previously discharged only by accident (the old
   file-wide fallback waived it alongside an unrelated, correctly-waived
   finding in the same file) and needs its OWN, honest disposition.

Re-triage each site individually, same discipline T-1666/T-1668 used for
OPAQUE001's own symref-population aftermath: read the finding, read the
nearest existing waiver comment (if any) and whether it is now
mis-targeted vs. genuinely absent, and either move/re-word the waiver or
add a new one with real reasoning. Do NOT blanket-re-forgive by widening
match precision back to file-scope or waiving all 20 with one generic
reason -- T-1579's mass-invalidation incident (55 waivers deleted from
one over-broad liveness check) and the standing WAIVE004 hardening this
repo carries are exactly the failure shape a rushed blanket pass here
would repeat in reverse (mass-CREATE instead of mass-delete, same root
cause: reasoning from shape/count instead of per-site).
