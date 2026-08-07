---
id: T-0556
title: 'gates: DRIFT001 default sig facet is blind to behavior/body rewrites (B2)'
state: done
kind: bug
origin: auditor
created: '2026-07-21'
priority: high
parent: T-0403
tier: ticket
sprint: null
scope:
- src/frob/gates/ src/frob/graph/
- src/frob/graph/
- tests/test_graph_lock.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/graph/
  reason: ticket's original scope field was a single malformed glob string 'src/frob/gates/
    src/frob/graph/' instead of two entries; splitting it out, plus tests/test_graph_lock.py
    for the behavior-change regression updates
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_graph_lock.py
  reason: ticket's original scope field was a single malformed glob string 'src/frob/gates/
    src/frob/graph/' instead of two entries; splitting it out, plus tests/test_graph_lock.py
    for the behavior-change regression updates
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_graph_lock.py::TestAckDrift::test_ack_then_sig_edit_yields_stale
- tests/test_graph_lock.py::TestAckDrift::test_ack_then_body_only_rewrite_yields_stale
- tests/test_graph_lock.py::TestAckDrift::test_acknowledge_records_every_describes_facet
designated_repro_test: null
threat: null
component: null
---
docs/audits/gates-accounting.md B2/E2. lock.py _DEFAULT_FACET='sig'; a frob:doc/DESCRIBES ack at the default facet only tracks the signature digest. Rewriting a documented function's body (behavior) after ack never trips DRIFT001 -- the doc can lie about behavior forever. Repro: ack a frob:doc at default facet, rewrite only the body, run frob check -> green. RIGHT-WAY fix direction: default ack facet to sig+body (or require an explicit facet and drift-check body+sig together) so a doc can't silently desync from behavior. Cross-cutting: touches every existing ack in the repo's lock file and the ack CLI UX -- too large for the T-0403 sweep budget.