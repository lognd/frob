---
id: T-3260
title: Split oversized V-model files under LARGE001 (T-3044 growth)
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
- strata-core/src/graph/vmodel/**
- strata-core/src/parse/grammar_vmodel.rs
- strata-core/src/parse/mod.rs
- tests/unit/strata/test_vmodel_check.py
- strata-core/src/parse/grammar_core.rs
- frob.lock
- docs/strata/vmodel.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: strata-core/src/graph/vmodel.rs
  reason: 'T-3260 real split: vmodel.rs -> vmodel/{mod,closure}.rs, grammar_core.rs''s
    vmodel productions -> new grammar_vmodel.rs (both spliced back via mod.rs''s existing
    include! pattern), plus updated frob:tests path refs in test_vmodel_check.py'
  actor: logan
  at: '2026-08-29'
- op: remove
  glob: strata-core/src/parse/grammar_core.rs
  reason: 'T-3260 real split: vmodel.rs -> vmodel/{mod,closure}.rs, grammar_core.rs''s
    vmodel productions -> new grammar_vmodel.rs (both spliced back via mod.rs''s existing
    include! pattern), plus updated frob:tests path refs in test_vmodel_check.py'
  actor: logan
  at: '2026-08-29'
- op: add
  glob: strata-core/src/graph/vmodel/**
  reason: 'T-3260 real split: vmodel.rs -> vmodel/{mod,closure}.rs, grammar_core.rs''s
    vmodel productions -> new grammar_vmodel.rs (both spliced back via mod.rs''s existing
    include! pattern), plus updated frob:tests path refs in test_vmodel_check.py'
  actor: logan
  at: '2026-08-29'
- op: add
  glob: strata-core/src/parse/grammar_vmodel.rs
  reason: 'T-3260 real split: vmodel.rs -> vmodel/{mod,closure}.rs, grammar_core.rs''s
    vmodel productions -> new grammar_vmodel.rs (both spliced back via mod.rs''s existing
    include! pattern), plus updated frob:tests path refs in test_vmodel_check.py'
  actor: logan
  at: '2026-08-29'
- op: add
  glob: strata-core/src/parse/mod.rs
  reason: 'T-3260 real split: vmodel.rs -> vmodel/{mod,closure}.rs, grammar_core.rs''s
    vmodel productions -> new grammar_vmodel.rs (both spliced back via mod.rs''s existing
    include! pattern), plus updated frob:tests path refs in test_vmodel_check.py'
  actor: logan
  at: '2026-08-29'
- op: add
  glob: tests/unit/strata/test_vmodel_check.py
  reason: 'T-3260 real split: vmodel.rs -> vmodel/{mod,closure}.rs, grammar_core.rs''s
    vmodel productions -> new grammar_vmodel.rs (both spliced back via mod.rs''s existing
    include! pattern), plus updated frob:tests path refs in test_vmodel_check.py'
  actor: logan
  at: '2026-08-29'
- op: add
  glob: strata-core/src/parse/grammar_core.rs
  reason: still modified (LARGE001 debt/waive header removed, doc-comment updated)
    even though the moved code lives elsewhere
  actor: logan
  at: '2026-08-29'
- op: add
  glob: frob.lock
  reason: frob.lock records the T-3260 acks made during this ticket's split; docs/strata/vmodel.md
    needed path-location notes added alongside the acks so the affects()-closure docs
    actually reflect the new file layout
  actor: logan
  at: '2026-08-29'
- op: add
  glob: docs/strata/vmodel.md
  reason: frob.lock records the T-3260 acks made during this ticket's split; docs/strata/vmodel.md
    needed path-location notes added alongside the acks so the affects()-closure docs
    actually reflect the new file layout
  actor: logan
  at: '2026-08-29'
evidence:
- tests/unit/strata/test_vmodel_check.py::TestVmodelCheckClosureSemantics::test_mutual_satisfies_pair_with_zero_requirements_now_fires
- tests/unit/strata/test_vmodel_check.py::TestVmodelCheckClosureSemantics::test_genuine_four_level_chain_is_quiet
- tests/unit/strata/test_vmodel_check.py::TestVmodelCheckClosureSemantics::test_satisfies_cycle_fires_through_vmodel_check
- tests/unit/strata/test_vmodel_check.py::TestVmodelCheckNodePayload::test_artifact_node_missing_code_ref_is_a_construction_error
- tests/unit/strata/test_vmodel_check.py::TestVmodelCheckNodePayload::test_test_node_missing_runnable_is_a_construction_error
- tests/unit/strata/test_vmodel_check.py::TestVmodelCheckNodePayload::test_supersedes_edge_missing_reason_is_a_construction_error
- tests/unit/strata/test_vmodel_check.py::TestVmodelCheckNodePayload::test_payload_present_on_every_kind_stays_quiet
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-3079's post-land sweep re-measurement confirmed strata-core/src/graph/vmodel.rs (992 lines) and strata-core/src/parse/grammar_core.rs (831 lines) are genuinely over the 800-line LARGE001 threshold, both grown past it by T-3044 (V-model H3). T-3079 waived both findings (frob:waive LARGE001) to unblock the sweep-regression ticket rather than doing a real split inline. This ticket is the deferred real fix: split vmodel.rs's closure-rule logic and grammar_core.rs's parse_vmodel_node/parse_vmodel_edge into their own modules, then remove the waivers.