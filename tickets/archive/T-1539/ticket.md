---
id: T-1539
title: 'PERF012 registry-entry gap: PERF012 detector exists with no CHK-GATE-PERF012
  registry row'
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- docs/design/registry/check-coverage.yaml
- src/frob/gates/_waive.py
- tickets/T-1539/**
- tests/test_gates.py
- tickets/T-1800/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: 'T-1539: add missing CHK-GATE-PERF012 row'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/perf/_rules.py
  reason: 'T-1539: PERF012 registry row also needs a frob:enforces directive in perf_rules
    to satisfy REG008'
  actor: logan
  at: '2026-08-07'
- op: remove
  glob: src/frob/perf/_rules.py
  reason: 'T-1539: revert - fix belongs in _waive.py''s _KNOWN_GATE_RULES, not a new
    frob:enforces edge (avoids closure blowup)'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'T-1539: PERF012 missing from _KNOWN_GATE_RULES (why REG010 never caught
    the gap); tickets dir needed for own Done report/ledger files'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1539/**
  reason: 'T-1539: PERF012 missing from _KNOWN_GATE_RULES (why REG010 never caught
    the gap); tickets dir needed for own Done report/ledger files'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_gates.py
  reason: 'T-1539: TestKnownGateRuleIds verifies the _KNOWN_GATE_RULES literal this
    ticket edits'
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1800/**
  reason: 'T-1539: filing this follow-up ticket during T-1539''s own work created
    this file in the touched set'
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_gate_rule_entries_match_live_known_rules
- tests/test_check_coverage_registry.py::TestExhaustivenessGateOverRealCheckCoverage::test_no_check_coverage_violations
designated_repro_test: null
threat: null
component: null
---
Refiled: original draft T-1539 (filed during T-1225's perf-detector work) died in the t-1350 ledger corruption spans. PERF012 fires from src/frob/perf but docs/design/registry/check-coverage.yaml has no CHK-GATE-PERF012 entry -- pre-existing gap found (not caused) by T-1225.

## Done report

Fixed the disclosed gap: added CHK-GATE-PERF012 to docs/design/registry/check-coverage.yaml
(disposition handled_by:PERF012), bumped gate_rule_total 288->289, and added the missing
"PERF012" entry to src/frob/gates/_waive.py's _KNOWN_GATE_RULES literal (it was the real
root cause the ticket asked to investigate: REG002 rejected the new row until PERF012 was
also a known rule, and REG010's detector-without-row check could never have caught this
gap in the first place because it only compares against _KNOWN_GATE_RULES, and PERF012 was
missing from BOTH places at once).

Bidirectional correspondence check already exists, in both directions:
- REG002 (ERROR): a check-coverage.yaml row's handled_by:<rule> must name a rule present in
  _KNOWN_GATE_RULES -- row-references-nonexistent-detector.
- REG010 (WARN, advisory): a live rule in _KNOWN_GATE_RULES with no CHK-GATE-<rule> entry in
  check-coverage.yaml -- detector-with-no-row. src/frob/gates/_registry_exhaustiveness.py's
  _reg010_gate_rule_staleness, wired at WARN specifically because this repo's own registry
  already carried other pre-existing gaps of this shape at the time REG010 landed (T-0560).

So nothing new needed to be built for bidirectional coverage -- it exists. What let PERF012's
gap through both checks simultaneously is that src/frob/perf/** sits outside the
_rule_id_scan.py SCANNED_BASES (a disclosed, documented v1 gap in that module's own
docstring: PERF00x ids are "hand-added to _KNOWN_GATE_RULES exactly as before" rather than
picked up by the generator scan) -- so _KNOWN_GATE_RULES' PERF01x block is maintained purely
by a human remembering to paste every new id, and PERF012 was the one that got missed when
PERF010/011/013/014 were added (T-1225). Filed T-1800 for a second, unrelated
instance of the exact same failure mode found in the process (SYS108 missing from
_KNOWN_GATE_RULES, tests/test_gates.py::TestKnownGateRuleIds red on main already) -- not
fixed here, out of this ticket's scope.

No frob:enforces CHK-GATE-PERF012 directive was added to code (would have satisfied REG008,
currently WARN for this entry) -- src/frob/perf/_rules.py and src/frob/perf/_dup_spawn.py
both carry pre-existing frob:tests/frob:doc directives whose targets (tests/test_perf.py,
docs/modules/perf.md, several other test files) would have had to enter this ticket's scope
under the scope-closure check, for a change with no test/behavior impact. Left as a WARN,
matching the existing precedent this same gate already carries for CHK-GATE-TEST018.

### Changed
```
 tickets/T-1539/ticket.md           | 46 +++++++++++++++++++++++++++++++++++++-
 tickets/T-1800/ticket.md | 21 +++++++++++++++++
 2 files changed, 66 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_gate_rule_entries_match_live_known_rules` (pytest node id, verified passing when recorded)
- `tests/test_check_coverage_registry.py::TestExhaustivenessGateOverRealCheckCoverage::test_no_check_coverage_violations` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 1157 warning(s), 725 waived
- error-findings: none (measured, zero errors)
