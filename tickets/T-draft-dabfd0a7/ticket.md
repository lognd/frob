---
id: T-draft-dabfd0a7
title: 'SCOPE002 closure gap: _ticket CLI parser package + ref_gate''s doc/test anchors
  never terminate under --ticket scoping'
state: queued
kind: bug
origin: human
created: '2026-09-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/_cli_parsers/_ticket/_closeout.py
- src/frob/_cli_parsers/_ticket/_metadata.py
- src/frob/_cli_parsers/_ticket/_new.py
- src/frob/_cli_parsers/_ticket/_progress.py
- src/frob/_cli_parsers/_ticket/_query.py
- src/frob/gates/_refs.py
- docs/guides/agentic-workflow.md
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: 'T-4145 follow-up: this is a decision/investigation ticket
  about SCOPE002''s closure-cascade behavior itself, not a ticket that edits any of
  the overlapping files -- a real fix scope will be decided once the SCOPE002 gate''s
  own remediation approach (a/b/c in the body) is chosen'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-4145 (split _closeout.py, fixed REF001/REF002 on GitHub convention files). `frob check --ticket <id>` for ANY ticket that touches src/frob/_cli_parsers/_ticket/_closeout.py or src/frob/gates/_refs.py trips SCOPE002 (promoted to ERROR in this repo's frob.toml) because those files' frob:doc/frob:tests anchors point into docs/guides/agentic-workflow.md and docs/modules/gates.md -- both large hub docs whose OWN doc-anchor/frob:tests closure fans out into 50-450+ further warnings/errors across the _ticket package's other submodules (_metadata.py/_new.py/_progress.py/_query.py) and unrelated test files (e.g. tests/unit/test_land_finish_guard.py), never terminating within a reasonably-scoped ticket. T-4145 worked around this by declining to add these files to its own scope and leaving the pre-existing SCOPE002 findings unresolved under --ticket-scoped checks (they do not appear in CI's unscoped self-gate run, which has no active ticket context, so this is not currently release-blocking -- but it will refuse the NEXT ticket that legitimately needs to touch _closeout.py or _refs.py with --ticket verification).

WHAT TO DO: either (a) narrow docs/guides/agentic-workflow.md and docs/modules/gates.md's own frob:doc granularity so a ticket touching one function does not pull in the whole hub doc's transitive closure, or (b) give SCOPE002 a per-symbol closure cap / cycle-breaker so a hub doc's own fan-out cannot cascade past the ticket's own touched files, or (c) demote SCOPE002 back to WARN in frob.toml if ERROR-severity closure was never meant to apply to hub-doc-anchored symbols. Reproduce: from a T-4145-shaped worktree, run "frob ticket scope <id> --add docs/guides/agentic-workflow.md" and watch the collapsed-warning count.
