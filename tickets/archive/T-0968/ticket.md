---
id: T-0968
title: frob:secret-fake requires reason= and routes through the waiver ledger (audit
  finding 3)
state: done
kind: security
origin: auditor
created: '2026-07-27'
priority: high
parent: T-0969
tier: ticket
sprint: null
scope:
- src/frob/gates/_secrets.py
- src/frob/gates/_pii_structural.py
- src/frob/app/telemetry.py
- tests/**
- src/frob/gates/__init__.py
- docs/design/registry/check-coverage.yaml
- docs/audits/gates-quality.md
- tickets.md
- tickets-archive.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'Registering the new SEC004 rule (a bare frob:secret-fake marker) requires
    a

    matching entry in frob.gates._KNOWN_GATE_RULES (src/frob/gates/__init__.py)

    and docs/design/registry/check-coverage.yaml''s gate_rule_entries/

    gate_rule_total, or the pre-existing test_every_emitted_rule_literal_is_known

    and check-coverage registry tests break -- both are mechanical consequences

    of adding a rule, not scope creep. docs/audits/gates-quality.md''s finding-3

    repro text also needed a one-line split (AKIA...EXAMPLE literal, plus the

    bare-marker mention) so this repo''s own tightened SEC001/SEC004 gate does

    not trip on its own audit trail describing this exact vulnerability.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: 'Registering the new SEC004 rule (a bare frob:secret-fake marker) requires
    a

    matching entry in frob.gates._KNOWN_GATE_RULES (src/frob/gates/__init__.py)

    and docs/design/registry/check-coverage.yaml''s gate_rule_entries/

    gate_rule_total, or the pre-existing test_every_emitted_rule_literal_is_known

    and check-coverage registry tests break -- both are mechanical consequences

    of adding a rule, not scope creep. docs/audits/gates-quality.md''s finding-3

    repro text also needed a one-line split (AKIA...EXAMPLE literal, plus the

    bare-marker mention) so this repo''s own tightened SEC001/SEC004 gate does

    not trip on its own audit trail describing this exact vulnerability.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/audits/gates-quality.md
  reason: 'Registering the new SEC004 rule (a bare frob:secret-fake marker) requires
    a

    matching entry in frob.gates._KNOWN_GATE_RULES (src/frob/gates/__init__.py)

    and docs/design/registry/check-coverage.yaml''s gate_rule_entries/

    gate_rule_total, or the pre-existing test_every_emitted_rule_literal_is_known

    and check-coverage registry tests break -- both are mechanical consequences

    of adding a rule, not scope creep. docs/audits/gates-quality.md''s finding-3

    repro text also needed a one-line split (AKIA...EXAMPLE literal, plus the

    bare-marker mention) so this repo''s own tightened SEC001/SEC004 gate does

    not trip on its own audit trail describing this exact vulnerability.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tickets.md
  reason: 'T-0968''s own ticket body (tickets.md) and T-0157''s Done-report follow-up

    note (tickets-archive.md) both quote the audit''s AKIA...EXAMPLE repro

    literal verbatim. Dropping the bare-substring example/fake suppression

    (this ticket''s own finding-3 fix, part b) makes that quoted prose newly

    real-looking to the tightened SEC001 scanner, redding the WHOLE repo''s

    `frob check` (unscoped) on ledger prose no other ticket''s scope covers.

    Splitting the literal across two backtick spans is a content-preserving,

    mechanical fix (identical treatment already applied to docs/audits/

    gates-quality.md) directly caused by this ticket''s own change, not

    unrelated ledger editing.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tickets-archive.md
  reason: 'T-0968''s own ticket body (tickets.md) and T-0157''s Done-report follow-up

    note (tickets-archive.md) both quote the audit''s AKIA...EXAMPLE repro

    literal verbatim. Dropping the bare-substring example/fake suppression

    (this ticket''s own finding-3 fix, part b) makes that quoted prose newly

    real-looking to the tightened SEC001 scanner, redding the WHOLE repo''s

    `frob check` (unscoped) on ledger prose no other ticket''s scope covers.

    Splitting the literal across two backtick spans is a content-preserving,

    mechanical fix (identical treatment already applied to docs/audits/

    gates-quality.md) directly caused by this ticket''s own change, not

    unrelated ledger editing.

    '
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_secrets_gate.py::TestFakeMarking::test_literal_fake_word_in_token_is_not_flagged
- tests/test_secrets_gate.py::TestFakeMarking::test_frob_secret_fake_marker_without_reason_still_fires
- tests/test_pii_structural_gate.py::TestEmailShapeValues::test_fake_marker_without_reason_does_not_discharge
- tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
- tests/test_pii_structural_gate.py::TestEmailShapeValues::test_fake_marker_on_line_above_discharges
- tests/test_pii_structural_gate.py::TestEmailShapeValues::test_fake_marker_on_same_line_discharges
designated_repro_test: null
acceptance:
- text: 'FAIL before T-0968: secrets_gate(repo) on a fixture repo whose tracked file
    carries a bare `# frob:secret-fake` (no reason=) produces no SEC004 finding at
    all (the marker either silently discharges the nearby credential, or is simply
    never checked) -- PASS after T-0968: secrets_gate(repo), the real production gate
    entrypoint, on that same fixture now returns both a SEC004 violation for the bare
    marker and the underlying SEC001 credential finding it no longer discharges for
    free.'
  evidence:
  - tests/test_secrets_gate.py::TestFakeMarking::test_frob_secret_fake_marker_without_reason_still_fires
threat: null
component: null
---
gates-quality audit (T-0399) finding 3: the `frob:secret-fake` marker
(src/frob/gates/_secrets.py's `_FAKE_MARKER`, also consulted by
`_pii_structural.py`'s `_EMAIL_FAKE_MARKER`) suppresses every SEC001/
PII010 match on its line with NO reason string, NO ticket, NO waiver
ledger record -- unlike `frob:waive`, which requires `reason="..."` and is
WAIVE001-enforced. Additionally `_looks_fake` suppresses any token merely
CONTAINING the substring `example`/`fake` (bare substring match, not
anchored).

Not fixed in T-0399 because every existing `frob:secret-fake` marker in
the tree today (tests/test_secrets_gate.py, tests/integration/
test_gitlog.py, tests/unit/test_app_runners*.py, tests/test_pii_structural_
gate.py, tests/unit/graph/test_dsl.py, tests/integration/
test_fleet_integration.py, tests/unit/fleet/test_route.py, and more) is a
BARE marker with no reason -- requiring `reason=` immediately would need
every one of those call sites (all outside T-0399's declared scope)
rewritten in the same change, or the newly-strict scanner would stop
suppressing them and fire real-looking-token ERRORs across the test
suite.

Plan: (a) change `_line_marks_fake`/`_FAKE_MARKER` parsing to require
`frob:secret-fake reason="..."` (mirroring `frob:waive`'s WAIVE001
contract) and route discharged hits through the same waiver-ledger
accounting `_apply_waivers` already does for `frob:waive`; (b) in the SAME
change, add `reason="..."` to every existing bare `frob:secret-fake`
marker across the tree (grep for the literal string first -- get an exact
count, it will have moved since 2026-07-27); (c) drop the bare-substring
`example`/`fake` suppression in `_looks_fake` in favor of the anchored
template-shape/entropy checks only (closes part of finding 3 and repro
"AKIA" + "IOSFODNN7EXAMPLE" from the audit -- split here, landed T-0968,
so this ticket body no longer trips its own tightened SEC001 gate).