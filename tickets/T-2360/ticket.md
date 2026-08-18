---
id: T-2360
title: 'Profile-collapse: build LandProfileSettings resolver for the 5 remaining if-rapid
  branches'
state: done
kind: feature
origin: human
created: '2026-08-17'
priority: medium
parent: T-1696
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/verify/_backpressure.py
- src/frob/tickets/_profile.py
- docs/modules/tickets-verify-sweep.md
evidence_scope:
- tests/unit/verify/test_backpressure.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/verify/test_backpressure.py::TestSettingsForProfile::test_fortress_matches_current_branch_logic
- tests/unit/verify/test_backpressure.py::TestSettingsForProfile::test_standard_matches_current_branch_logic
- tests/unit/verify/test_backpressure.py::TestSettingsForProfile::test_rapid_matches_current_branch_logic
- tests/unit/verify/test_backpressure.py::TestSettingsForProfile::test_settings_are_frozen
- tests/unit/verify/test_backpressure.py::TestSettingsForProfile::test_unknown_profile_value_raises
designated_repro_test: null
threat: null
component: tickets
anchor: false
anchor_reason: null
land_commit: null
---
Split from T-1696 (queue-depth-dial collapse epic) after a re-measurement
of the "if-rapid seams" following T-2290/T-2310/T-2317/T-2324/T-2065
(all landed 2026-08-17).

MEASURED 2026-08-17 via `frob explore xref ProfileName` (semantic
call-graph, not grep): live ProfileName branches still exist in 5
files outside src/frob/tickets/_profile.py (line numbers as of this
measurement, expect drift):

  src/frob/tickets/_land.py:2878        _land_is_rapid -- gates whether
    a land-evidence-scope-unbound finding is recorded as DEBT (rapid) vs
    presumably an error (non-rapid)
  src/frob/tickets/_land.py:3103        TEST016 mutation-evidence skip
    under rapid (subprocess AND deferred batch sweep both skipped)
  src/frob/app/ticket_runner/_land_cmd.py:4324   pre-commit sweep skip
    under rapid (T-1575: "single post-land sweep, no pre-commit sweep")
  src/frob/app/ticket_runner/_land_cmd.py:4519   rapid "soft backpressure
    warning" branch -- LAYERED ON TOP of ceilings_for_profile (T-2290),
    which ALREADY resolves rapid to unbounded ceilings; this branch is
    redundant with that resolution and could be derived from
    `ceilings.max_depth is None` instead of re-testing ProfileName
  src/frob/tickets/_evidence.py:323     _is_rapid -- generic profile-check
    helper, used by evidence-leniency callers
  src/frob/app/ticket_runner/_close_cmd.py:463   REL001 preflight skip
    under rapid (T-1705)

PRECEDENT ALREADY LANDED: `frob.verify._backpressure.ceilings_for_profile`
(T-1692, extended by T-2290) is the target pattern working today for ONE
axis -- it resolves ProfileName to a `BackpressureCeilings(max_depth,
max_age_s)` settings record in exactly one place, and every backpressure
caller reads the record, never the profile name. fortress=depth 0,
standard=bounded (frob.toml-overridable), rapid=None/None (unbounded).
This ticket generalizes that SAME pattern to the other 5 branches above.

Build a `LandProfileSettings` (or extend `BackpressureCeilings`'s sibling
shape) pydantic model (frozen=True, extra="forbid") with fields for:
  - pre_commit_sweep_enabled: bool
  - mutation_evidence_required: bool  (TEST016)
  - rel001_preflight_enabled: bool
  - evidence_scope_unbound_is_debt: bool  (vs a hard error)
One `settings_for_profile(ProfileName, root) -> LandProfileSettings`
resolver, colocated with (or beside) `ceilings_for_profile` -- do not
duplicate the frob.toml-read/override plumbing that function already has.

Behavior-preserving: fortress/standard/rapid's CURRENT observable
resolution for each of the 4 fields above must round-trip through the
new resolver unchanged -- write the settings-resolution tests FIRST,
asserting today's behavior, before touching any call site (that migration
is the next child, not this one).

Standing constraints from the parent epic apply unchanged (symbolic not
lexical, typani Result/ErrorSet, frozen pydantic models, log everything,
docs same-change, no waivers).

Acceptance:
- LandProfileSettings (or equivalent) resolves all 4 boolean/enum fields
  correctly for all 3 profiles, verified against TODAY's branch logic at
  each of the 5 call sites (read the current code, do not guess).
- No call site is migrated yet (that is the next child) -- this ticket
  only builds and tests the resolver.
- docs/modules/tickets-verify-sweep.md (or the settings module's own doc
  anchor) documents the new settings record alongside the existing
  BackpressureCeilings section.