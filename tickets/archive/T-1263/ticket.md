---
id: T-1263
title: gates --fix Tier-C fix-it emission format for agents
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: T-1137
tier: ticket
sprint: null
scope:
- src/frob/gates/_fix_engine_tier_c.py
- tests/test_gates.py
- docs/design/check-fix-engine.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/design/check-fix-engine.md
  reason: Tier-C emitter's frob:doc anchor lives there; must update in the same diff
    (AFFECT001)
  actor: logan
  at: '2026-08-03'
- op: add
  glob: design/frob.strata
  reason: capability effects/interface declarations for the new module must live in
    the same node
  actor: logan
  at: '2026-08-03'
evidence:
- tests/test_gates.py::TestFixEngineTierC::test_todo001_emits_a_fixit_with_no_proposed_patch
- tests/test_gates.py::TestFixEngineTierC::test_no_eligible_findings_returns_an_empty_list
- tests/test_gates.py::TestFixEngineTierC::test_no_violations_at_all_returns_an_empty_list
- tests/test_gates.py::TestFixEngineTierC::test_todo001_emitter_never_touches_any_file
designated_repro_test: null
acceptance:
- text: GIVEN a content-required finding with a registered Tier-C emitter WHEN --fix
    runs THEN no file is edited and a FixIt record with a non-empty reason_unfixable
    is emitted
  evidence:
  - tests/test_gates.py::TestFixEngineTierC::test_todo001_emits_a_fixit_with_no_proposed_patch
- text: GIVEN --fix --json THEN the output includes a `fixits` array; on a repo with
    zero Tier-C-eligible findings the array is empty, never a missing key
  evidence:
  - tests/test_gates.py::TestFixEngineTierC::test_no_eligible_findings_returns_an_empty_list
  - tests/test_gates.py::TestFixEngineTierC::test_no_violations_at_all_returns_an_empty_list
- text: GIVEN a FixIt's message field THEN it is the original violation's message
    verbatim, never paraphrased
  evidence:
  - tests/test_gates.py::TestFixEngineTierC::test_todo001_emits_a_fixit_with_no_proposed_patch
threat: null
component: null
---
Build Tier-C fix-it emission per docs/design/check-fix-engine.md
"Fix-it emission format" section: new src/frob/gates/_fix_engine_tier_c.py
with a FixIt model (rule, file, line, message, proposed_patch: str | None,
reason_unfixable: str) and TIER_C_EMITTERS: dict[str, TierCEmitter]. Wire
`--fix --json`'s output to include a `fixits` array (empty when no Tier-C
emitter fires) alongside the existing violations array -- additive only,
never replacing frob check's existing --json shape. Ship at least one
real Tier-C emitter (a content-required finding with no mechanical
rewrite -- e.g. TODO001's "bind this to a ticket" case, or a DOC002
finding with 0 or 2+ fuzzy candidates, reusing fix_doc002_unique_slug's
own already-computed candidate set to populate proposed_patch when
exactly the wrong number of candidates exist, or null when zero).