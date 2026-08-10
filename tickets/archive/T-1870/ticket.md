---
id: T-1870
title: 'Delete frob sys sync-interface: interface= must be declared intent, not an
  auto-measured mirror nothing reads'
state: done
kind: feature
origin: human
created: '2026-08-08'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_fix_engine_sync.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/_cli_parsers/_misc.py
- src/frob/_cli_parsers/_design.py
- src/frob/app/sys_runner.py
- src/frob/app/config.py
- docs/commands/sys.md
- docs/strata/surface.md
- docs/modules/gates.md
- docs/guides/agent-playbook.md
- src/frob/gates/_fix_engine.py
- src/frob/app/_config_external.py
- src/frob/strata/_sync_may.py
- src/frob/strata/_selfconform.py
- tests/unit/strata/test_selfconform.py
- tests/test_gates.py
- tests/test_ticket_work_and_land_finish.py
- src/frob/strata/_waive.py
- src/frob/gates/_waive.py
- docs/modules/strata.md
- docs/strata/waive.md
- docs/design/registry/check-coverage.yaml
- docs/design/registry/arch-checks.yaml
- src/frob/gates/__init__.py
- src/frob/gates/_fix_engine_text.py
- tests/unit/strata/test_structural_linter_hardening_totality.py
- tickets/T-1886/ticket.md
- tickets/T-1887/ticket.md
- tickets/archive/T-0341/ticket.md
- tickets/archive/T-0668/ticket.md
- tickets/archive/T-1113/ticket.md
- tickets/archive/T-1150/ticket.md
- tickets/archive/T-1198/ticket.md
- tickets/archive/T-1425/ticket.md
- tickets/archive/T-1531/ticket.md
- tickets/archive/T-1624/ticket.md
- tickets/archive/T-1625/ticket.md
- design/frob.strata
- tickets/T-1629/ticket.md
- src/frob/strata/_sync_interface.py
- tests/unit/strata/test_sync_interface.py
- rapid-debt.jsonl
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: ticket body requires SYS104's frob:enumerates member + docs row removed
    together (DOCENUM001), and the sync-interface mention in the agent playbook cleaned
    up
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/guides/agent-playbook.md
  reason: ticket body requires SYS104's frob:enumerates member + docs row removed
    together (DOCENUM001), and the sync-interface mention in the agent playbook cleaned
    up
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/gates/_fix_engine.py
  reason: 'discovered during survey: _fix_engine.py imports fix_sys104_interface_union
    and has the TIER_A_HANDLERS[SYS104] registration; _config_external.py''s from_external
    allowlist includes sys_check, which is entirely sync-interface-specific'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/app/_config_external.py
  reason: 'discovered during survey: _fix_engine.py imports fix_sys104_interface_union
    and has the TIER_A_HANDLERS[SYS104] registration; _config_external.py''s from_external
    allowlist includes sys_check, which is entirely sync-interface-specific'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/strata/_sync_may.py
  reason: 'sanctioned narrow touch: _sync_may.py imports _NODE_HEADER_RE/_node_body_span
    from the deleted _sync_interface.py; extracting them in as _sync_may.py''s own
    private helpers (coordinator-approved) rather than deleting or standing up a new
    shared module for two symbols with one importer. No other change to this file''s
    own SYS100 logic.'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/strata/_selfconform.py
  reason: SYS104's own check (_interface_conformance_violations) lives in _selfconform.py
    and must be deleted alongside its writer; test_selfconform.py's TestInterfaceConformance
    class covers it and must go too (TestDuplicateInterface/SYS108 stays untouched);
    test_sync_interface.py tests the deleted module wholesale; test_gates.py has the
    SYS104 Tier-A acceptance tests; test_ticket_work_and_land_finish.py covers _land_cmd.py's
    pre-land absorption step being changed
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/strata/test_selfconform.py
  reason: SYS104's own check (_interface_conformance_violations) lives in _selfconform.py
    and must be deleted alongside its writer; test_selfconform.py's TestInterfaceConformance
    class covers it and must go too (TestDuplicateInterface/SYS108 stays untouched);
    test_sync_interface.py tests the deleted module wholesale; test_gates.py has the
    SYS104 Tier-A acceptance tests; test_ticket_work_and_land_finish.py covers _land_cmd.py's
    pre-land absorption step being changed
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/strata/test_sync_interface.py
  reason: SYS104's own check (_interface_conformance_violations) lives in _selfconform.py
    and must be deleted alongside its writer; test_selfconform.py's TestInterfaceConformance
    class covers it and must go too (TestDuplicateInterface/SYS108 stays untouched);
    test_sync_interface.py tests the deleted module wholesale; test_gates.py has the
    SYS104 Tier-A acceptance tests; test_ticket_work_and_land_finish.py covers _land_cmd.py's
    pre-land absorption step being changed
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_gates.py
  reason: SYS104's own check (_interface_conformance_violations) lives in _selfconform.py
    and must be deleted alongside its writer; test_selfconform.py's TestInterfaceConformance
    class covers it and must go too (TestDuplicateInterface/SYS108 stays untouched);
    test_sync_interface.py tests the deleted module wholesale; test_gates.py has the
    SYS104 Tier-A acceptance tests; test_ticket_work_and_land_finish.py covers _land_cmd.py's
    pre-land absorption step being changed
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/test_ticket_work_and_land_finish.py
  reason: SYS104's own check (_interface_conformance_violations) lives in _selfconform.py
    and must be deleted alongside its writer; test_selfconform.py's TestInterfaceConformance
    class covers it and must go too (TestDuplicateInterface/SYS108 stays untouched);
    test_sync_interface.py tests the deleted module wholesale; test_gates.py has the
    SYS104 Tier-A acceptance tests; test_ticket_work_and_land_finish.py covers _land_cmd.py's
    pre-land absorption step being changed
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/strata/_waive.py
  reason: MULTI_INSTANCE_WAIVER_FAMILIES in _waive.py still lists SYS104, a rule id
    being deleted -- must be removed from the registry alongside the rule; docs/strata/surface.md's
    MULTI_INSTANCE_WAIVER_FAMILIES rule-id-count text and family list also cite SYS104
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/strata/surface.md
  reason: MULTI_INSTANCE_WAIVER_FAMILIES in _waive.py still lists SYS104, a rule id
    being deleted -- must be removed from the registry alongside the rule; docs/strata/surface.md's
    MULTI_INSTANCE_WAIVER_FAMILIES rule-id-count text and family list also cite SYS104
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/gates/_waive.py
  reason: src/frob/gates/_waive.py::_KNOWN_GATE_RULES lists SYS104 and is the frob:enumerates
    target docs/modules/gates.md's rule catalog already binds to -- must move together
    per DOCENUM001. docs/modules/strata.md has a dedicated '## SYS104 exact interface
    conformance' section with frob:describes anchors into the deleted module. docs/strata/waive.md's
    waivable-rule list also names SYS104.
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/modules/strata.md
  reason: src/frob/gates/_waive.py::_KNOWN_GATE_RULES lists SYS104 and is the frob:enumerates
    target docs/modules/gates.md's rule catalog already binds to -- must move together
    per DOCENUM001. docs/modules/strata.md has a dedicated '## SYS104 exact interface
    conformance' section with frob:describes anchors into the deleted module. docs/strata/waive.md's
    waivable-rule list also names SYS104.
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/strata/waive.md
  reason: src/frob/gates/_waive.py::_KNOWN_GATE_RULES lists SYS104 and is the frob:enumerates
    target docs/modules/gates.md's rule catalog already binds to -- must move together
    per DOCENUM001. docs/modules/strata.md has a dedicated '## SYS104 exact interface
    conformance' section with frob:describes anchors into the deleted module. docs/strata/waive.md's
    waivable-rule list also names SYS104.
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: 'REG008/REG010 registry entries: check-coverage.yaml''s CHK-GATE-SYS104
    entry asserts SYS104 is a live gate rule (false once deleted, entry removed);
    arch-checks.yaml''s SLH-SYS-EVA-03-UNDECLARED-PUBLIC-SURFACE disposition points
    handled_by:SYS104 at a rule that no longer exists, re-dispositioned to out_of_scope:reasoned-deferral
    citing T-1629 (which will re-cover undeclared-public-surface differently, as hand-declared-intent
    enforcement rather than a bidirectional mirror-equality check)'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/design/registry/arch-checks.yaml
  reason: 'REG008/REG010 registry entries: check-coverage.yaml''s CHK-GATE-SYS104
    entry asserts SYS104 is a live gate rule (false once deleted, entry removed);
    arch-checks.yaml''s SLH-SYS-EVA-03-UNDECLARED-PUBLIC-SURFACE disposition points
    handled_by:SYS104 at a rule that no longer exists, re-dispositioned to out_of_scope:reasoned-deferral
    citing T-1629 (which will re-cover undeclared-public-surface differently, as hand-declared-intent
    enforcement rather than a bidirectional mirror-equality check)'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'src/frob/gates/__init__.py::_KNOWN_RULE_FIXABILITY lists SYS104: auto --
    must be removed since SYS104 is no longer a Tier-A-fixable rule (it no longer
    exists). _fix_engine_text.py''s module docstring lists SYS104 among the sibling
    _fix_engine_sync handler family, now stale prose.'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/gates/_fix_engine_text.py
  reason: 'src/frob/gates/__init__.py::_KNOWN_RULE_FIXABILITY lists SYS104: auto --
    must be removed since SYS104 is no longer a Tier-A-fixable rule (it no longer
    exists). _fix_engine_text.py''s module docstring lists SYS104 among the sibling
    _fix_engine_sync handler family, now stale prose.'
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/strata/test_structural_linter_hardening_totality.py
  reason: test_structural_linter_hardening_totality.py needed editing for the SLH-SYS-EVA-03
    re-disposition (missed adding it earlier); the two drafts are new tickets filed
    for pre-existing, unrelated test failures found while verifying T-1870; the archived
    tickets are COV003 stale-evidence repairs (frob ticket evidence --replace) for
    tests deleted by this cut, each with its own recorded evidence_changes reason
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1886/ticket.md
  reason: test_structural_linter_hardening_totality.py needed editing for the SLH-SYS-EVA-03
    re-disposition (missed adding it earlier); the two drafts are new tickets filed
    for pre-existing, unrelated test failures found while verifying T-1870; the archived
    tickets are COV003 stale-evidence repairs (frob ticket evidence --replace) for
    tests deleted by this cut, each with its own recorded evidence_changes reason
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1887/ticket.md
  reason: test_structural_linter_hardening_totality.py needed editing for the SLH-SYS-EVA-03
    re-disposition (missed adding it earlier); the two drafts are new tickets filed
    for pre-existing, unrelated test failures found while verifying T-1870; the archived
    tickets are COV003 stale-evidence repairs (frob ticket evidence --replace) for
    tests deleted by this cut, each with its own recorded evidence_changes reason
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/archive/T-0341/ticket.md
  reason: test_structural_linter_hardening_totality.py needed editing for the SLH-SYS-EVA-03
    re-disposition (missed adding it earlier); the two drafts are new tickets filed
    for pre-existing, unrelated test failures found while verifying T-1870; the archived
    tickets are COV003 stale-evidence repairs (frob ticket evidence --replace) for
    tests deleted by this cut, each with its own recorded evidence_changes reason
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/archive/T-0668/ticket.md
  reason: test_structural_linter_hardening_totality.py needed editing for the SLH-SYS-EVA-03
    re-disposition (missed adding it earlier); the two drafts are new tickets filed
    for pre-existing, unrelated test failures found while verifying T-1870; the archived
    tickets are COV003 stale-evidence repairs (frob ticket evidence --replace) for
    tests deleted by this cut, each with its own recorded evidence_changes reason
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/archive/T-1113/ticket.md
  reason: test_structural_linter_hardening_totality.py needed editing for the SLH-SYS-EVA-03
    re-disposition (missed adding it earlier); the two drafts are new tickets filed
    for pre-existing, unrelated test failures found while verifying T-1870; the archived
    tickets are COV003 stale-evidence repairs (frob ticket evidence --replace) for
    tests deleted by this cut, each with its own recorded evidence_changes reason
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/archive/T-1150/ticket.md
  reason: test_structural_linter_hardening_totality.py needed editing for the SLH-SYS-EVA-03
    re-disposition (missed adding it earlier); the two drafts are new tickets filed
    for pre-existing, unrelated test failures found while verifying T-1870; the archived
    tickets are COV003 stale-evidence repairs (frob ticket evidence --replace) for
    tests deleted by this cut, each with its own recorded evidence_changes reason
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/archive/T-1198/ticket.md
  reason: test_structural_linter_hardening_totality.py needed editing for the SLH-SYS-EVA-03
    re-disposition (missed adding it earlier); the two drafts are new tickets filed
    for pre-existing, unrelated test failures found while verifying T-1870; the archived
    tickets are COV003 stale-evidence repairs (frob ticket evidence --replace) for
    tests deleted by this cut, each with its own recorded evidence_changes reason
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/archive/T-1425/ticket.md
  reason: test_structural_linter_hardening_totality.py needed editing for the SLH-SYS-EVA-03
    re-disposition (missed adding it earlier); the two drafts are new tickets filed
    for pre-existing, unrelated test failures found while verifying T-1870; the archived
    tickets are COV003 stale-evidence repairs (frob ticket evidence --replace) for
    tests deleted by this cut, each with its own recorded evidence_changes reason
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/archive/T-1531/ticket.md
  reason: test_structural_linter_hardening_totality.py needed editing for the SLH-SYS-EVA-03
    re-disposition (missed adding it earlier); the two drafts are new tickets filed
    for pre-existing, unrelated test failures found while verifying T-1870; the archived
    tickets are COV003 stale-evidence repairs (frob ticket evidence --replace) for
    tests deleted by this cut, each with its own recorded evidence_changes reason
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/archive/T-1624/ticket.md
  reason: test_structural_linter_hardening_totality.py needed editing for the SLH-SYS-EVA-03
    re-disposition (missed adding it earlier); the two drafts are new tickets filed
    for pre-existing, unrelated test failures found while verifying T-1870; the archived
    tickets are COV003 stale-evidence repairs (frob ticket evidence --replace) for
    tests deleted by this cut, each with its own recorded evidence_changes reason
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/archive/T-1625/ticket.md
  reason: test_structural_linter_hardening_totality.py needed editing for the SLH-SYS-EVA-03
    re-disposition (missed adding it earlier); the two drafts are new tickets filed
    for pre-existing, unrelated test failures found while verifying T-1870; the archived
    tickets are COV003 stale-evidence repairs (frob ticket evidence --replace) for
    tests deleted by this cut, each with its own recorded evidence_changes reason
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: src/frob/strata/_sync_interface.py
  reason: both files are deleted entirely by this ticket; a scope entry naming a nonexistent
    path trips PARSE001 in gates that try to read scope-listed files directly (PII010/RENDER001)
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: tests/unit/strata/test_sync_interface.py
  reason: both files are deleted entirely by this ticket; a scope entry naming a nonexistent
    path trips PARSE001 in gates that try to read scope-listed files directly (PII010/RENDER001)
  actor: logan
  at: '2026-08-08'
- op: add
  glob: design/frob.strata
  reason: design/frob.strata is the ticket's own explicit deletion target (self-model
    interface=/via cleanup); tickets/T-1629/ticket.md was touched via frob ticket
    accept to prevent the SLH-SYS-EVA-03 deferral from orphaning, per coordinator
    instruction
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tickets/T-1629/ticket.md
  reason: design/frob.strata is the ticket's own explicit deletion target (self-model
    interface=/via cleanup); tickets/T-1629/ticket.md was touched via frob ticket
    accept to prevent the SLH-SYS-EVA-03 deferral from orphaning, per coordinator
    instruction
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/strata/_sync_interface.py
  reason: both files are deleted BY this ticket -- must be in scope to justify the
    deletion at land time (UnownedDeletions); the earlier --remove was to silence
    a PARSE001 false-positive on a since-freed design/frob.strata reference, which
    is now independently fixed
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/strata/test_sync_interface.py
  reason: both files are deleted BY this ticket -- must be in scope to justify the
    deletion at land time (UnownedDeletions); the earlier --remove was to silence
    a PARSE001 false-positive on a since-freed design/frob.strata reference, which
    is now independently fixed
  actor: logan
  at: '2026-08-08'
- op: add
  glob: rapid-debt.jsonl
  reason: auto-appended by the rapid-profile deferred-sweep machinery during repeated
    land attempts on this ticket; append-only ledger, union merge driver
  actor: logan
  at: '2026-08-08'
evidence:
- tests/unit/strata/test_selfconform.py::TestDuplicateInterface::test_duplicate_symbol_fires
- tests/unit/strata/test_selfconform.py::TestDuplicateInterface::test_no_duplicates_silent
- tests/test_ticket_work_and_land_finish.py::TestAssertDesignLoadsPreLand::test_refuses_when_a_design_file_is_malformed
- tests/test_ticket_work_and_land_finish.py::TestAssertDesignLoadsPreLand::test_still_proceeds_when_design_dir_absent
- tests/unit/strata/test_structural_linter_hardening_totality.py::TestDenominatorFullyDispositioned::test_every_denominator_id_has_a_real_registry_entry
- tests/unit/strata/test_structural_linter_hardening_totality.py::TestDenominatorFullyDispositioned::test_every_denominator_id_is_dispositioned
- tests/unit/strata/test_structural_linter_hardening_totality.py::TestConformanceChecksBoundToDenominator::test_each_conformance_row_handled_by_its_real_check
- tests/unit/strata/test_structural_linter_hardening_totality.py::TestConformanceChecksBoundToDenominator::test_bound_rules_are_real_known_gate_rules
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
OWNER DIRECTIVE, 2026-08-08: "sync-interface shouldn't be a thing; it
should be removed. We're making strata actually an enforcement layer
instead of dumb useless accounting."

`frob sys sync-interface` (T-1150) mechanically MEASURES every node's
bound-code public surface and WRITES it into `design/frob.strata`'s
`interface=` attributes. The design file therefore MIRRORS the code
instead of CONSTRAINING it, which inverts the entire point of a design
layer. A declaration that is auto-derived from the thing it supposedly
governs cannot govern anything.

CORRECTION, 2026-08-08 (the original "ZERO readers" claim below is
WRONG as first written and is kept here, struck through in spirit but
literally corrected, rather than silently dropped -- a ticket that
ships with a wrong measurement is the same class of defect as a gate
that lies). The owner's original grep was `\.interface\b`, anchored on
the attribute-ACCESS form; that pattern structurally cannot see
`_selfconform.py::_duplicate_interface_violations` (SYS108, T-1624)
reading the SAME `interface=` node attrs a different way (iterating
the attrs list, not `.interface`-style access). An implementer
verified this before cutting anything (per standing instruction: stop
and report a real consumer rather than delete around it) and it
changed the scope of this ticket. The corrected picture:

    SYS104 asks "does the declaration match the code?" -- which is
    VACUOUS when the declaration is auto-written FROM the code by
    `sync-interface` in the first place. This is the mirror-check
    the rest of this ticket describes, and it is deleted below.

    SYS108 asks "is the declaration itself well-formed (no symbol
    named twice on one node)?" -- which is a REAL question regardless
    of who wrote the declaration, gets MORE useful once `interface=`
    becomes T-1629's hand-declared intent (a human hand-writing
    `interface=[foo, foo]` is a mistake no measurement-derived value
    could ever have contained), and has NO Tier-A auto-fix handler
    (confirmed: `fix_sys104_interface_union` is the only interface-
    related Tier-A registration) -- nothing silently re-derives it
    from a measurement. SYS108 is real, human-actionable enforcement,
    not accounting theater, and is explicitly OUT of this ticket's
    deletion scope (see KEEP below).

The lifecycle that actually IS a closed loop with no exit -- and the
part this ticket removes -- is narrower than originally stated:

    1. `sync-interface` measures the real public surface
    2. it writes that measurement into `interface=`
    3. SYS104 checks that the written value still matches the measurement
    4. `fix_sys104_interface_union` (a Tier-A handler) auto-repairs any
       drift, by re-measuring

Measure reality, write reality down, check the writing matches reality,
auto-fix it when it does not. No step in THIS loop can ever fail in a
way that means anything about the code being wrong. This is the exact
shape of the "catalogued is not enforced" failure this repo has already
paid for -- SYS104 and the sync/auto-fix machinery around it, not SYS108.

IT ALSO CAUSES ACTIVE HARM. `_sync_interface_pre_land_step`
(`src/frob/app/ticket_runner/_land_cmd.py:190`) runs it AUTOMATICALLY on
every land. So an unrelated ticket's land silently rewrites
`design/frob.strata`, which then trips SCOPE001/COV002 and forces the
implementer to scope-add a globally-contended shared file. That chain
was reproduced first-hand during T-1648 and is the confirmed root cause
behind T-1868's double-lease incident. Deleting this verb IS T-1868's
requirement 3 -- remove the pressure, do not build a mechanism to manage
it.

DELETE, do not deprecate:

- `src/frob/strata/_sync_interface.py` (484 lines) -- entirely
  (`apply_sync_interface`, `sync_interface_report`)
- the interface half of `src/frob/gates/_fix_engine_sync.py` (796 lines;
  it ALSO handles COV002 and `_sync_may`, so this is a partial removal,
  not a file delete -- read it before cutting)
- `_sync_interface_pre_land_step` and its call in `_land_cmd.py`
- `fix_sys104_interface_union` and its `TIER_A_HANDLERS["SYS104"]`
  registration
- `_interface_conformance_violations` (SYS104) and its call site in
  `_selfconform.py::check_self_conformance` -- SYS104 ONLY, its
  `_KNOWN_GATE_RULES` entry, and its row in `docs/modules/gates.md`
  AND that file's `frob:enumerates` member list (these two must move
  together or DOCENUM001 fires)
- CLI surface: `frob sys sync-interface` and its `--check` flag in
  `src/frob/_cli_parsers/_misc.py` and `_design.py`; `sys_command` /
  `sys_check` fields in `src/frob/app/config.py`; the runner in
  `src/frob/app/sys_runner.py`
- docs: SYS104/sync-interface content in `docs/commands/sys.md`,
  `docs/strata/surface.md`, `docs/modules/gates.md`,
  `docs/guides/agent-playbook.md`, and `design/frob.strata`'s own
  self-model

KEEP, unchanged -- `_duplicate_interface_violations` (SYS108, T-1624)
in its entirety: the function itself, its call in
`check_self_conformance`, its `_KNOWN_GATE_RULES` entry, its row in
`docs/modules/gates.md`'s catalog, and its waiver precedent at
`src/frob/gates/_waive.py:900-909`. Both SYS104 and SYS108 read the
same `interface=` node attrs, from the same file, but ask different
questions -- SYS104 (deleted) asks whether the declaration mirrors the
code, which is vacuous when the declaration is auto-written from the
code; SYS108 (kept) asks whether the declaration itself is well-formed
(no symbol declared twice), which stays real regardless of who writes
`interface=` and gets MORE useful once `interface=` is T-1629's
hand-declared intent, not less.

EXPLICITLY OUT OF SCOPE: `src/frob/strata/_sync_may.py` (707 lines,
capability `may=` sync). It is arguably the same anti-pattern, but the
directive named `sync-interface` and `may=` capability enforcement is
live work under T-1623/T-1628. Do not touch it. If removing the
interface half forces a shared-helper decision, extract rather than
delete, and say so.

WHAT REPLACES IT: nothing, here. `interface=` becomes a HAND-DECLARED
statement of INTENDED surface. Making it enforce -- flagging a public
symbol that is NOT declared, which is the check that actually has teeth
-- is T-1629 ("interface= should declare INTENDED surface, not mirror
every public symbol"), already raised to high priority by the owner.
This ticket removes the mirror; T-1629 adds the constraint. Landing this
one first is correct and leaves `interface=` inert in between, which is
strictly better than actively lying.

SEQUENCING: this touches `docs/modules/gates.md` and `design/frob.strata`,
both heavily contended. Consider `frob ticket runs-last` if the fleet is
busy. Expect a large DEAD001 sweep after the cut -- that is the point;
fix findings in touched code rather than waiving them.