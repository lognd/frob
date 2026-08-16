---
id: T-2193
title: 'Evidence discipline only proves the bug existed, never that the fix kept the
  capability: --check-repro verifies a test FAILED at parent, so a fix that disables
  the feature entirely passes every gate'
state: queued
kind: bug
origin: human
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_mutation_evidence.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: THREE measured instances this session, all of which passed every existing
    gate. (1) T-2156 narrowed cross-file symbol resolution to import-verified candidates;
    the primitive it depends on, resolve_local_import, returns None for every intra-repo
    import form this codebase uses, so the fix accepts NO cross-file candidate at
    all. Certified by two verify-explain queries, one going UNATTRIBUTED and one attributing
    via a SAME-FILE path -- both outcomes are exactly what a disabled capability produces.
    (2) T-2177's scope-plausibility check warns on a wildly unrelated file but NOT
    on any of the three real mis-scopings it was built for. (3) frob cycle finds a
    planted cycle in a top-level layout and misses the identical one in src-layout,
    so its clean verdict on frob's own repo is vacuous. This test MUST fail against
    current main.
  evidence: []
- text: 'Add a MUST-STILL-PASS control alongside the repro: a designated test (or
    set) that must PASS at the fix commit AND would have passed at the parent, asserting
    the capability the fix narrows is still exercised. --designate-repro/--check-repro
    cover only the negative direction (the test FAILED at parent, proving the bug
    was real). Nothing asserts the positive direction, so ''false positives disappeared''
    is indistinguishable from ''the feature stopped running''. Require it specifically
    for fixes that NARROW a decision rule -- resolution, matching, filtering, gating
    -- where over-correction is silent.'
  evidence: []
- text: 'Do NOT satisfy this by requiring ''more tests'' or a coverage threshold --
    the missing thing is a SPECIFIC claim (this capability still works), not volume,
    and a coverage number cannot express it. Do NOT infer the control automatically
    from the existing suite passing: in all three instances above the suite passed,
    because the disabled capability had no test asserting it still functioned. The
    control must be an explicit, named designation the author makes, the same way
    --designate-repro is.'
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
---
