---
id: T-0978
title: Wire frob:secret-fake into WAIVE004 zero-findings staleness detection
state: done
kind: security
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/graph/dsl.py
- src/frob/gates/__init__.py
- tests/**
- src/frob/gates/_secrets.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_secrets.py
  reason: 'Detecting whether a frob:secret-fake reason="..." site still trips a real

    SEC00x pattern hit this run requires the private pattern table and

    _looks_fake/_scan_line internals that only src/frob/gates/_secrets.py owns

    (mirrors T-0968''s own scope extension for the same module). Keeping the

    staleness predicate here (secrets_gate''s own module) matches this ticket''s

    "implement staleness at the GATE level" mandate -- gates/__init__.py only

    wires the resulting WAIVE004-shaped violations into the existing

    all_violations assembly, it does not re-implement pattern matching.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/gates.md
  reason: 'fake_marker_staleness_gate carries a frob:doc docs/modules/gates.md#public-api

    directive (AFFECT001 requires the target doc actually change in this diff);

    documenting the new gate function alongside secrets_gate''s existing entry

    is the minimal doc-as-you-go update this ticket''s own new public symbol

    requires.

    '
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_secrets_gate.py::TestFakeMarkerStaleness::test_stale_marker_fires_waive004
- tests/test_secrets_gate.py::TestFakeMarkerStaleness::test_stale_marker_on_line_above_fires_waive004
- tests/test_secrets_gate.py::TestFakeMarkerStaleness::test_live_marker_does_not_fire
- tests/test_secrets_gate.py::TestFakeMarkerStaleness::test_marker_discharging_email_shaped_pii_does_not_fire
- tests/test_secrets_gate.py::TestFakeMarkerStaleness::test_bare_marker_without_reason_is_not_a_staleness_site
- tests/test_secrets_gate.py::TestFakeMarkerStaleness::test_docstring_style_mention_is_not_a_staleness_site
designated_repro_test: null
threat: null
component: null
---
T-0968 shipped requiring `reason="..."` on `frob:secret-fake`/PII011's shared
marker (mirroring WAIVE001) and added SEC004 for a bare marker, but the
marker is still a DSL-reserved, graph-invisible verb
(`frob.graph.dsl._RESERVED_MARKER_VERBS`) per the original T-0157 decision
(`src/frob/gates/_secrets.py`'s module docstring) -- it never becomes a real
WAIVE `Edge`, so `frob.gates._waive004_violations`'s zero-findings
staleness detector (which iterates real `frob:waive` edges only) does not
watch it. That piece of the audit ask genuinely requires touching
`src/frob/graph/dsl.py` and/or `src/frob/gates/__init__.py`
(`_apply_waivers`/`_match_waiver`/`_waive_edges`/`_waive004_violations`),
both outside T-0968's declared scope
(`src/frob/gates/_secrets.py`, `src/frob/gates/_pii_structural.py`,
`src/frob/app/telemetry.py`, `tests/**`).

Two options to actually close this gap, either is a real design decision
that should get its own ticket rather than being forced into T-0968:
(a) retire the reserved-marker special case and let `frob:secret-fake`
become a real `frob.graph.dsl` verb that mints a WAIVE-shaped edge (target
= the rule it discharges), so it flows through `_apply_waivers`/WAIVE004
for free; or (b) teach `_waive004_violations` (and friends) a second,
non-graph waiver source specifically for this marker family (scan tracked
text directly for `frob:secret-fake reason="..."` sites the way
`_bare_fake_marker_violations` already does, then check each site still
has >=1 real SEC00x/PII011 hit).