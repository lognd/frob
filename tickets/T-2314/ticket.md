---
id: T-2314
title: frob:waive PERF004/PERF008 is silently ignored by gate:PERF, so a non-hoistable
  finding can be neither fixed nor waived
state: done
kind: bug
origin: agent
created: '2026-08-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_waive.py
- src/frob/perf/_rules.py
- src/frob/gates/__init__.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'scope for the PERF waiver investigation: _match_waiver/_apply_waivers spine,
    perf_gate/_violation construction, and the gate test file'
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/perf/_rules.py
  reason: 'scope for the PERF waiver investigation: _match_waiver/_apply_waivers spine,
    perf_gate/_violation construction, and the gate test file'
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'scope for the PERF waiver investigation: _match_waiver/_apply_waivers spine,
    perf_gate/_violation construction, and the gate test file'
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/test_gates.py
  reason: 'scope for the PERF waiver investigation: _match_waiver/_apply_waivers spine,
    perf_gate/_violation construction, and the gate test file'
  actor: logan
  at: '2026-08-17'
evidence:
- tests/test_gates.py::TestOptInGates::test_perf_gate_reports_a_repo_relative_file_not_absolute
- tests/test_gates.py::TestOptInGates::test_frob_waive_perf004_suppresses_the_named_finding
- tests/test_gates.py::TestOptInGates::test_frob_waive_perf004_does_not_blanket_suppress_other_sites
- tests/test_gates.py::TestOptInGates::test_the_preexisting_rapid_sweep_waiver_now_actually_suppresses
designated_repro_test: tests/test_gates.py::TestOptInGates::test_perf_gate_reports_a_repo_relative_file_not_absolute
acceptance:
- text: given a PERF site carrying a frob:waive PERF00x directive, when gate:PERF
    runs, then the finding is suppressed
  evidence:
  - tests/test_gates.py::TestOptInGates::test_frob_waive_perf004_suppresses_the_named_finding
- text: given a PERF site with no waiver, when gate:PERF runs, then the finding is
    still reported (not a blanket suppression)
  evidence:
  - tests/test_gates.py::TestOptInGates::test_frob_waive_perf004_does_not_blanket_suppress_other_sites
- text: given the investigation confirmed gate:PERF's Python producer (perf_rules)
    already routes through the same _apply_waivers spine as every other gate (no architectural
    inability to honour waivers), the fix corrects the path-shape bug instead of adding
    a refuse-loudly path; verified via the same evidence proving waivers now work
  evidence:
  - tests/test_gates.py::TestOptInGates::test_the_preexisting_rapid_sweep_waiver_now_actually_suppresses
acceptance_amendments:
- op: replace
  index: 2
  old_text: given a native gate that cannot honour waivers by design, when a waive
    directive names one of its rules, then check refuses loudly rather than accepting
    it silently
  new_text: given the investigation confirmed gate:PERF's Python producer (perf_rules)
    already routes through the same _apply_waivers spine as every other gate (no architectural
    inability to honour waivers), the fix corrects the path-shape bug instead of adding
    a refuse-loudly path; verified via the same evidence proving waivers now work
  reason: 'investigated and confirmed: this was a plain path-shape bug (absolute vs
    relative), not a native-gate design limitation -- the refuse-loudly fallback in
    criterion 2''s original text does not apply, so this criterion is reworded to
    record what was actually verified instead of leaving an inapplicable acceptance
    unbound'
  actor: logan
  at: '2026-08-17'
threat: null
component: gates
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-08-17 by an implementer working T-2303, empirically, not
inferred.

`frob:waive PERF004` / `frob:waive PERF008` directives do NOT suppress
`gate:PERF`'s findings. The agent applied the codebase's own documented
waiver pattern at all 3 PERF sites in
`src/frob/app/ticket_runner/_land_cmd.py` -- matching working examples in
`src/frob/perf/_advisories.py`, `_hotgraph.py` and `_dup_spawn.py` -- and
the findings persisted unchanged.

THE DECISIVE CONTROL: an ALREADY-EXISTING waiver in the tree, at
`src/frob/app/ticket_runner/_rapid_sweep.py:1652`, likewise does not
suppress its own finding. So this is not a malformed-directive mistake by
one agent; the mechanism itself does not apply here.

LIKELY CAUSE (implementer to confirm, do not assume): `gate:PERF` runs in
the native `gates-native` stage, while the waiver machinery that demonstrably
works belongs to the deep `src/frob/perf/` Python analysis tool. Two
producers of the same rule ids, only one of which honours waivers.

WHY THIS IS WORSE THAN NOISE:
 - A PERF finding cannot be waived, so it can never be legitimately
   dismissed -- only "fixed". T-2303's investigation found all 3 sites are
   genuinely NON-hoistable (arguments vary per loop iteration: `new_defs`
   recomputed per file, `lines[0]` per porcelain block; and one is a
   deliberate retry against changing external state, the T-1913 ref-
   visibility race). Hoisting them would be a CORRECTNESS REGRESSION.
 - So the only two exits are both closed: the fix is wrong, and the waiver
   does not work. Any ticket carrying a PERF finding is unclosable, and the
   pressure on an agent is to "fix" it by making the code wrong.
 - Unwaivable findings accumulate in the floor forever and feed the
   post-land sweep's regression tickets, manufacturing recurring noise.

This is an instance of the standing "catalogued is not enforced" lesson
inverted: the waiver is documented and looks applied, and reads as honoured
by anyone grepping for it, while having zero effect.

REQUIRED:
 1. Determine which producer emits gate:PERF's findings and whether it
    consults the waiver registry at all.
 2. Make `frob:waive PERF00x` actually suppress the finding it names -- or,
    if a native gate deliberately cannot honour waivers, make it REFUSE a
    waive directive loudly at check time rather than accepting it silently.
    A directive that is silently ignored is the worst of the three options.
 3. Re-measure the PERF floor afterwards and report how many existing
    findings were being silently unwaived.

POSITIVE CONTROLS: (1) a waived PERF site produces no finding;
(2) must-still-pass -- an UNWAIVED genuine PERF site still produces one, so
the fix is not a blanket suppression; (3) the existing waiver at
`_rapid_sweep.py:1652` stops reporting.