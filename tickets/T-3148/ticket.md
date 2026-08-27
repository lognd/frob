---
id: T-3148
title: _KNOWN_RULE_FIXABILITY literal missing SYS100 (T-3140 item 4)
state: in-progress
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_gates.py
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/
  reason: 'narrowed: only the checked-in _KNOWN_RULE_FIXABILITY literal needs the
    SYS100 entry added'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: src/frob/gates/_wire.py
  reason: 'narrowed: only the checked-in _KNOWN_RULE_FIXABILITY literal needs the
    SYS100 entry added'
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tests/test_gates.py
  reason: 'narrowed: only the checked-in _KNOWN_RULE_FIXABILITY literal needs the
    SYS100 entry added'
  actor: logan
  at: '2026-08-27'
- op: remove
  glob: src/frob/gates/_wire.py
  reason: 'Verified before working: _KNOWN_RULE_FIXABILITY actually lives in

    src/frob/gates/__init__.py, not _wire.py (no match for the symbol in

    _wire.py at all). Also the failure direction is inverted from the

    ticket''s own description: T-2922 deliberately REMOVED SYS100''s Tier-A

    handler (a security-relevant decision -- an auto-fix that widens a "may"

    capability grant must never be automatic), so a fresh

    generated_fixability() scan now correctly reports SYS100 as "manual"

    (excluded from the checked-in literal). The checked-in _KNOWN_RULE_

    FIXABILITY literal was never regenerated after that removal and still

    carries a stale "SYS100": "auto" entry -- the literal has an entry the

    fresh scan does NOT report, not the other way around. Correcting scope

    to the real file before making the (opposite-direction) fix.

    '
  actor: logan
  at: '2026-08-27'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'Verified before working: _KNOWN_RULE_FIXABILITY actually lives in

    src/frob/gates/__init__.py, not _wire.py (no match for the symbol in

    _wire.py at all). Also the failure direction is inverted from the

    ticket''s own description: T-2922 deliberately REMOVED SYS100''s Tier-A

    handler (a security-relevant decision -- an auto-fix that widens a "may"

    capability grant must never be automatic), so a fresh

    generated_fixability() scan now correctly reports SYS100 as "manual"

    (excluded from the checked-in literal). The checked-in _KNOWN_RULE_

    FIXABILITY literal was never regenerated after that removal and still

    carries a stale "SYS100": "auto" entry -- the literal has an entry the

    fresh scan does NOT report, not the other way around. Correcting scope

    to the real file before making the (opposite-direction) fix.

    '
  actor: logan
  at: '2026-08-27'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description
tests/test_gates.py::TestRuleFixability::test_checked_in_literal_matches_a_fresh_scan
fails: the checked-in `_KNOWN_RULE_FIXABILITY` literal (production file
under src/frob/gates/, out of T-3140's declared scope) is missing
`{'SYS100': 'auto'}` that a fresh scan now reports. A new rule SYS100 was
added with auto-fixability and the checked-in literal was never
regenerated against it.

## Plan
Locate `_KNOWN_RULE_FIXABILITY` (src/frob/gates/), regenerate/add the
SYS100 entry, and re-run the test to confirm it passes.
