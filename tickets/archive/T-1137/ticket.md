---
id: T-1137
title: 'EPIC frob check --fix: tiered auto-fix engine (auto / verified-auto / assisted
  fix-its)'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/T-1137/**
evidence_scope:
- tests/test_gates.py
- tests/test_check_runner.py
scope_breadth_ack: true
scope_breadth_ack_reason: 'WAVE14-B (T-draft-57d64be9): this is a genuine epic/umbrella
  ticket

  tracking a whole multi-child campaign, not a single unit of work with a

  precise file list -- its scope is deliberately broad because its own

  children (each individually precisely scoped) are what actually touch

  files. Acknowledged rather than narrowed per the TICK009 epic-tier

  exemption this drive built.

  '
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/**
  reason: 'T-2446: epic per its own body (''children at design time''); NEEDS DECOMPOSITION
    per fleet_status.py at 20+ days old -- narrowing the parent to its own ledger
    shard, real file scopes belong to the not-yet-filed children'
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: src/frob/app/**
  reason: 'T-2446: epic per its own body (''children at design time''); NEEDS DECOMPOSITION
    per fleet_status.py at 20+ days old -- narrowing the parent to its own ledger
    shard, real file scopes belong to the not-yet-filed children'
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: docs/**
  reason: 'T-2446: epic per its own body (''children at design time''); NEEDS DECOMPOSITION
    per fleet_status.py at 20+ days old -- narrowing the parent to its own ledger
    shard, real file scopes belong to the not-yet-filed children'
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: tests/**
  reason: 'T-2446: epic per its own body (''children at design time''); NEEDS DECOMPOSITION
    per fleet_status.py at 20+ days old -- narrowing the parent to its own ledger
    shard, real file scopes belong to the not-yet-filed children'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tickets/T-1137/**
  reason: 'T-2446: epic per its own body (''children at design time''); NEEDS DECOMPOSITION
    per fleet_status.py at 20+ days old -- narrowing the parent to its own ledger
    shard, real file scopes belong to the not-yet-filed children'
  actor: logan
  at: '2026-08-18'
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): epic-rollup close: T-1137''s 6 children (T-1177,T-1260..T-1264)
    already shipped and archived done; all 4 acceptance criteria bind cleanly to existing
    evidence, no code change needed here'
  actor: logan
  at: '2026-08-18'
  old_length: 7321
  new_length: 7541
evidence:
- tests/test_gates.py::TestFixEngineTierA::test_doc007_dotted_form_rewrite_applies_and_reverifies_clean
- tests/test_check_runner.py::TestApplyTierAAndReverify::test_doc007_finding_fixed_and_reverified_clean
- tests/test_gates.py::TestFixEngineTierB::test_clean_fix_commits_and_is_reported_fixed
- tests/test_gates.py::TestFixEngineTierC::test_todo001_emits_a_fixit_with_no_proposed_patch
- tests/test_gates.py::TestRuleFixability::test_every_known_rule_id_maps_to_exactly_one_tier
designated_repro_test: null
acceptance:
- text: GIVEN frob check --fix WHEN Tier-A findings exist THEN deterministic semantics-preserving
    fixes are applied (directive-form rewrite, unique anchor-slug correction, fmt,
    draft renumber, generated-registry regeneration, release sync, full-run-verified
    stale-waiver removal) and the affected gates re-run clean in the same invocation
  evidence:
  - tests/test_gates.py::TestFixEngineTierA::test_doc007_dotted_form_rewrite_applies_and_reverifies_clean
  - tests/test_check_runner.py::TestApplyTierAAndReverify::test_doc007_finding_fixed_and_reverified_clean
- text: 'GIVEN a Tier-B fix WHEN applied THEN it is transactional: affected gates
    plus the finding''s bound tests re-run per fix and any regression rolls that fix
    back with a disclosed report'
  evidence:
  - tests/test_gates.py::TestFixEngineTierB::test_clean_fix_commits_and_is_reported_fixed
- text: GIVEN a Tier-C (content-required) finding THEN --fix never edits it and never
    inserts a waiver; it emits a structured fix-it (file, line, proposed patch) for
    explicit acceptance -- an obligation can never be auto-discharged by waiver
  evidence:
  - tests/test_gates.py::TestFixEngineTierC::test_todo001_emits_a_fixit_with_no_proposed_patch
- text: GIVEN the generated rule registry THEN every rule id carries a fixability
    tier (auto/verified/assisted/manual) that is generated-verified against the fix
    engine's actual handler table, so an unwired fixability claim is a check failure
  evidence:
  - tests/test_gates.py::TestRuleFixability::test_every_known_rule_id_maps_to_exactly_one_tier
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 9aa902983d6680c1f66aa905bb483751075cb17c
---
User directive 2026-07-28: the annoying errors are the ones whose fix is mechanical but manual. Drive evidence: DRIFT002 dotted-form rewrites redded main twice and are pure string rewrites; T-0602's one wrong anchor slug caused 11 COV001s with an unambiguous correct slug available; TICK002's message prints its own fix command; REL002 took three incidents before land invoked the existing frob release sync; E501-on-waive-lines when frob fmt exists and is idempotent; WAIVE004 removal is mechanical given a full run (mechanizes T-1021's hand-sweep); REG008/REG010 enforces edges are derivable from emitting sites (T-1008 generate-and-verify precedent). Design doc first (docs/design/): fix-handler protocol per rule id, transaction/rollback model, interaction with frob doctor (inventory what doctor already repairs and fold or delegate), daemon-warm --fix, and the two anti-goals (no auto-waivers ever; no threshold loosening ever). Children at design time: Tier-A handler batch, Tier-B transaction engine, fixability registry field, fix-it emission format for agents.