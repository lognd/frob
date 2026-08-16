---
id: T-2223
title: Capability scan misses cross-file call indirection (wrapper laundering across
  node boundary)
state: queued
kind: security
origin: human
created: '2026-08-16'
priority: critical
parent: T-1623
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/vet/_capability.py
- src/frob/vet/_capability_scan.py
- src/frob/vet/_capability_core.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Measured (T-1623 premise check): scan_file_capabilities is strictly per-file with no cross-file call resolution. Positive control: file A defines run(cmd) calling os.system(cmd) (scans as exec, correctly); file B does 'from a import run; run(x)' and calls nothing else dangerous directly -- scan_file_capabilities(B) returns frozenset() on current main. Any node whose code= binds only file B therefore shows zero observed capabilities even though its code exercises exec through A's wrapper, so SYS100/THREAT004 never flags B for an undeclared exec grant and a reviewer auditing B's node sees a clean capability surface. This is the concrete instance of T-1623's 'capability detection is lexical rather than symbol-resolved' claim -- not fixable by adding more substring needles (token/grammar directive: no re.search escape hatch). Acceptance: a regression test with the two-file fixture above MUST fail on current main (asserting B's resolved capability set includes exec, or that the selfconform join surfaces it for B's node) and must pass after the fix. The fix must follow same-package local-import call edges to at least one hop (extend the existing _python_resolved_candidates/binding machinery already used for import aliasing rather than inventing a parallel path) -- do not special-case the fixture's function name. Do NOT attempt full points-to/whole-program resolution; state explicitly in the module docstring what hop-depth is covered and what remains an honest limit, same style as the existing T-0209/T-0244 gap statements in _capability.py.