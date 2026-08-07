---
id: T-1168
title: 'vet: add 11 missing frob:enforces CHK-GATE edges (REG008 burn-down, VET007-010/SYSWAIVE003/VET-JS004/VET-PY001-3/VET-RS001-2)'
state: dropped
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- docs/design/registry/check-coverage.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Found while triaging T-1006 (widespread pre-existing test failures).
tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml
fails: REG008 reports 11 docs/design/registry/check-coverage.yaml entries
dispositioned handled_by:<RULE> with no matching `frob:enforces
CHK-GATE-<RULE>` edge anywhere in code:

VET007, VET008, VET009, VET010, SYSWAIVE003, VET-JS004, VET-PY001,
VET-PY002, VET-PY003, VET-RS001, VET-RS002

The last 6 (VET-JS004, VET-PY001/2/3, VET-RS001/2) are newly-registered
via `frob registry audit --sync-gate-rules` under T-1006 (they previously
had no CHK-GATE entry at all, hence no REG008 finding for them either --
REG010 was the finding before sync). VET007-010 and SYSWAIVE003 predate
that sync and were already missing their enforcement edge.

Plan: locate the enforcing call site for each of these 11 gate rules in
src/frob/vet/** (and wherever SYSWAIVE003 is enforced) and add the
`frob:enforces CHK-GATE-<RULE>` directive comment at each site, per the
T-1101 precedent (11 similar SC-* edges landed recently). Re-disposition
any entry in check-coverage.yaml instead if a rule turns out to have no
single enforcing site.

Scope deliberately not widened under T-1006 to cover this -- it touches
several files under src/frob/vet/** outside T-1006's own declared scope
and needs its own triage of each rule's real enforcement site.

## Drop reason
- 2026-07-28: T-1006's merge of main (daada10f, T-1134 and other concurrent waves) resolved this independently before this ticket started -- fresh run of TestCheckCoverageReg008BurnDown shows 0 REG008 findings, 1 passed. No remaining work.