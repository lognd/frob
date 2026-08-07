---
id: T-0928
title: profile frob check end-to-end and produce ranked hot-path audit (dogfood frob
  perf collect/hot)
state: done
kind: docs
origin: human
created: '2026-07-26'
priority: high
parent: T-0927
tier: ticket
sprint: null
scope:
- docs/audits/check-performance.md
- src/frob/perf/**
- docs/index.md
- docs/audits/README.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/index.md
  reason: 'Adding docs/index.md and docs/audits/README.md to scope: linking the new
    audit doc into the audit index/README so DOC001 (orphaned doc) does not fire,
    per this repo''s own house style of one bullet per audit doc.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/audits/README.md
  reason: 'Adding docs/index.md and docs/audits/README.md to scope: linking the new
    audit doc into the audit index/README so DOC001 (orphaned doc) does not fire,
    per this repo''s own house style of one bullet per audit doc.

    '
  actor: logan
  at: '2026-07-27'
evidence:
- cmd:bash /tmp/claude-1000/-home-logan-projects-frob/5bfbdf34-54a2-426c-89be-ade390652f3f/scratchpad/verify_audit.sh
  exit=0 sha256=de02c1947993
designated_repro_test: null
acceptance:
- text: given a full frob check run on this repo profiled with the T-0765/T-0712 tooling
    (frob perf collect --sampler or equivalent), when the audit doc is written, then
    it contains a ranked table of hot paths (function-level, with per-gate attribution
    and cumulative percentages) covering at least 80 percent of total runtime, each
    row marked python-optimizable / rust-candidate / io-bound with a one-line justification
  evidence:
  - cmd:bash /tmp/claude-1000/-home-logan-projects-frob/5bfbdf34-54a2-426c-89be-ade390652f3f/scratchpad/verify_audit.sh
    exit=0 sha256=de02c1947993
- text: given the ranked table, when candidate fixes are enumerated, then each top-10
    row names a concrete remedy and an estimated payoff, and every generalizable anti-pattern
    found is ALSO encoded per the both-layers rule (PERF00x detector + .strata obligation)
    or explicitly dispositioned why not
  evidence:
  - cmd:bash /tmp/claude-1000/-home-logan-projects-frob/5bfbdf34-54a2-426c-89be-ade390652f3f/scratchpad/verify_audit.sh
    exit=0 sha256=de02c1947993
threat: null
component: null
---
Child 1 of T-0927. Profile-first: no optimization without measurement. Dogfood our own perf tooling on frob check itself (python sampler over a full run plus per-stage wall timings already emitted in gate-summary). Deliverable is docs/audits/check-performance.md in the audit-doc style of docs/audits/. Known suspects to confirm/refute: archgate tree-walks, test-gate pytest collection, sys/strata native round-trips, coverage graph loads, pii/secrets file scans re-reading the same files per gate (shared file-content cache candidate), load_graph cache-drift rebuilds (the 'drifted from cache' warnings on every land).