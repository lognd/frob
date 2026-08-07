---
id: T-1575
title: 'Development profiles: frob.toml profile=rapid|standard|fortress with one-way
  auto-ratchet'
state: done
kind: feature
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/app/**
- src/frob/_cli_parsers/**
- docs/**
- tests/**
- src/frob/tickets/_profile.py
- src/frob/tickets/_land.py
- src/frob/app/ticket_runner/_land_cmd.py
- tests/unit/test_profile.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_profile.py
  reason: 'T-1575 dev profiles: new profile module, land-path stage-seam gating'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/tickets/_land.py
  reason: 'T-1575 dev profiles: new profile module, land-path stage-seam gating'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: 'T-1575 dev profiles: new profile module, land-path stage-seam gating'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/unit/test_profile.py
  reason: 'T-1575 dev profiles: new profile module, land-path stage-seam gating'
  actor: logan
  at: '2026-08-05'
- op: add
  glob: docs/modules/tickets.md
  reason: 'T-1575 dev profiles: new profile module, land-path stage-seam gating'
  actor: logan
  at: '2026-08-05'
evidence:
- tests/unit/test_profile.py::TestConfiguredProfile::test_absent_frob_toml_is_standard
- tests/unit/test_profile.py::TestConfiguredProfile::test_explicit_rapid_parses
- tests/unit/test_profile.py::TestConfiguredProfile::test_unknown_value_errors
- tests/unit/test_profile.py::TestEffectiveProfile::test_standard_is_unaffected_by_ratchet
- tests/unit/test_profile.py::TestEffectiveProfile::test_rapid_below_threshold_stays_rapid
- tests/unit/test_profile.py::TestEffectiveProfile::test_rapid_above_threshold_ratchets_to_standard
- tests/unit/test_profile.py::TestEffectiveProfile::test_persisted_ratchet_wins_even_if_thresholds_no_longer_trip
- tests/unit/test_profile.py::TestDowngrade::test_downgrade_clears_persisted_ratchet
- tests/unit/test_profile.py::TestDowngrade::test_downgrade_is_noop_when_nothing_ratcheted
designated_repro_test: null
threat: null
component: null
---
Small/new repos pay the same fixed land ceremony as this 950-file repo: TEST016 mutation evidence, double sweep, baseline snapshot worktree, REL001 -- ~30 min to land a trivial ticket in a repo with a couple of tickets. The ceremony does not scale down with repo size because it is fixed-cost, not proportional.

Add frob.toml [profile] with profile = rapid | standard | fortress (default standard = today's behavior).

rapid: no TEST016 on the land path; single post-land sweep with revert-on-red (no pre-commit sweep); no baseline snapshot worktree; evidence/done-report requirements light for kind=docs/chore; REL001 off. NEVER relaxed: ledger integrity checks, LAND-PROOF verification.

fortress: reserved stricter tier (placeholder wiring only; semantics in a follow-up).

ONE-WAY AUTO-RATCHET: rapid auto-upgrades to standard when any threshold trips (repo file count, total ticket count, concurrent agent/lease count -- exact thresholds to be tuned in implementation). Upgrades are automatic and logged; DOWNGRADES are never automatic -- an explicit CLI decision that is loudly logged.

Note T-1518 (land pipeline stages) and T-1444 (merge-queue) already deliver adjacent pieces; implementer should branch the land path at the stage seams T-1518 defines rather than adding profile conditionals inline.