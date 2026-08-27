---
id: T-3026
title: 'Post-land findings from the T-3006/T-2995/T-3014 batch: ARCH103, DOC001, E501,
  2x LARGE001, REF001, REF002'
state: in-progress
kind: bug
origin: human
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_new_renumber.py
- docs/strata/entity_architecture.md
- src/frob/narrative/_cli.py
- src/frob/__main__.py
- src/frob/stats/_agentic.py
- tests/unit/strata/entity_arch/storage_cheap.strata
- docs/strata/surface.md
- docs/index.md
- docs/commands/narrative.md
evidence_scope:
- tests/test_narrative_migrate.py
- tests/unit/test_lang_strata_entity_arch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_new_renumber.py
  reason: 'T-3026: fix ARCH103/DOC001/E501/2xLARGE001/REF001/REF002 post-land findings'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/strata/entity_architecture.md
  reason: 'T-3026: fix ARCH103/DOC001/E501/2xLARGE001/REF001/REF002 post-land findings'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/narrative/_cli.py
  reason: 'T-3026: fix ARCH103/DOC001/E501/2xLARGE001/REF001/REF002 post-land findings'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/__main__.py
  reason: 'T-3026: fix ARCH103/DOC001/E501/2xLARGE001/REF001/REF002 post-land findings'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/stats/_agentic.py
  reason: 'T-3026: fix ARCH103/DOC001/E501/2xLARGE001/REF001/REF002 post-land findings'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/strata/entity_arch/storage_cheap.strata
  reason: 'T-3026: fix ARCH103/DOC001/E501/2xLARGE001/REF001/REF002 post-land findings'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/strata/surface.md
  reason: 'T-3026: REF001/REF002/DOC001 fix for entity_architecture.md needs a second
    real inbound doc reference'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/index.md
  reason: 'T-3026: REF001/REF002/DOC001 fix for entity_architecture.md needs a second
    real inbound doc reference'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/commands/narrative.md
  reason: 'T-3026: touch affects()-closure doc for run_narrative_command (AFFECT001)'
  actor: logan
  at: '2026-08-26'
body_changes:
- mode: append
  reason: 'T-3026: BUG002 escape -- this ticket''s changes (doc links, waivers, frob:debt,
    line-wraps) have no runtime behavior delta to reproduce'
  actor: logan
  at: '2026-08-26'
  old_length: 0
  new_length: 242
evidence:
- tests/test_narrative_migrate.py::TestNarrativeCli::test_dry_run_reports_without_writing
- tests/unit/test_lang_strata_entity_arch.py::TestEntityArchitectureFixtures::test_cheap_architecture_is_a_second_realization_of_the_same_entity
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
<!-- frob:no-behavior-change reason="every change in this ticket is a doc link/waiver/frob:debt directive addition or a pure line-wrap (E501) -- no runtime behavior changed; verified by running the touched test files unchanged and green" -->