---
id: T-2733
title: remove now-redundant frob:waive RENDER001 directives in .claude/hooks and scripts/fleet_status.py
state: done
kind: docs
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
- .claude/hooks/*.py
- scripts/fleet_status.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- cmd:/tmp/verify_t2733.sh exit=0 sha256=d0e352f3be03
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: dffadbb70f2212e8c5a97bcfdfa218225cc2883d
---
T-2719 landed a directory/file exemption in RENDER001 (frob.gates._render_lint._EXEMPT_PREFIXES) covering .claude/hooks/ and scripts/fleet_status.py, and widened the gate's scan to genuinely cover those paths (previously unscanned). The 11 frob:waive RENDER001 directives across .claude/hooks/frob-timeout-guard.py (x2), .claude/hooks/pending-background-guard.py, .claude/hooks/root-cleanliness-detector.py, .claude/hooks/root-write-guard.py, and scripts/fleet_status.py (x6) are now genuinely redundant -- confirmed by T-2719's own before/after measurement that removing the exemption (scan left widened) reproduces exactly these findings, and restoring it drops them back to zero. Remove the per-line waivers now that the structural exemption exists on main; verify RENDER001 stays at 0 in these files after removal via frob check --only render_lint --no-cache.