---
id: T-0519
title: T-0187/T-0198 evidence test_no_clone_group_at_any_threshold does not resolve
  (COV003) after T-0494 flipped its assertion
state: done
kind: bug
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tickets.md
- tickets-archive.md
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tickets-archive.md
  reason: T-0519 dedupes the T-0187/T-0198 archived evidence lines that live in tickets-archive.md,
    not tickets.md
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/integration/test_interfaces.py
  reason: 'route 2 evidence-scope binding (D-02): the recorded T-0167-precedent CLI-dispatch
    evidence file must itself be in scope for close to recognize it as covering'
  actor: logan
  at: '2026-07-21'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
---
found while working T-0494: T-0494 legitimately removed tests/test_dup_cross_lang.py::TestCrossLanguageCloneNotYetDetected::test_no_clone_group_at_any_threshold (its assertion, report.groups == (), is now FALSE at every threshold since T-0487's _KEYWORDS fix made R5 correctly fire cross-language for this fixture -- see T-0494's Done report and the new TestCrossLanguageR5NowFires class replacing it). This leaves T-0187 (1 evidence id) and T-0198 (5 evidence ids, one per threshold parametrization) in tickets-archive.md pointing at a test id that no longer exists, firing COV003 for both archived tickets on every frob check. Same shape as the T-0416/T-0472 precedent (evidence pointing at a removed/renamed test). Remedy: update T-0187's and T-0198's archived evidence lists to point at still-valid replacement ids (e.g. TestCrossLanguageR5NowFires::test_r5_group_fires_at_every_threshold[*] for the threshold-parametrized ones, or drop the stale id with a note that the original claim inverted) via the tickets CLI against tickets-archive.md. Out of T-0494's declared scope (scope=tests/test_dup_cross_lang.py, docs/modules/dup.md -- does not include editing OTHER tickets' archived evidence).