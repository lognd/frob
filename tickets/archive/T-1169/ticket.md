---
id: T-1169
title: 'vet/native: add missing frob:enforces CHK-GATE-NATIVE001 edge (REG008)'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_native_staleness.py
- docs/design/registry/check-coverage.yaml
- tests/unit/strata/test_native_staleness.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/strata/test_native_staleness.py
  reason: real evidence covering native_unavailable_warning, the CHK-GATE-NATIVE001
    enforcing site
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml
- tests/unit/strata/test_native_staleness.py::TestUnimportableNatives::test_warning_names_the_native_and_the_fix_command
- tests/unit/strata/test_native_staleness.py::TestUnimportableNatives::test_warning_is_none_when_nothing_broken
designated_repro_test: null
threat: null
component: null
---
Found while triaging T-1006 (widespread pre-existing test failures) and
its subsequent main-merge chase. NATIVE001 was synced into
docs/design/registry/check-coverage.yaml via `frob registry audit
--sync-gate-rules` (needed to fix REG010 in the same file, another
T-1006 finding) but has no matching `frob:enforces CHK-GATE-NATIVE001`
edge anywhere in code yet, so
tests/test_registry_exhaustiveness.py::TestCheckCoverageReg008BurnDown::test_no_reg008_findings_for_check_coverage_yaml
fails again.

This is a recurring pattern in a fast-moving repo: any newly-landed gate
rule needs BOTH a CHK-GATE registry entry (REG010, fixed mechanically by
--sync-gate-rules) AND a real frob:enforces edge at its enforcing call
site (REG008, needs a human/agent to find and annotate that site) --
they land on different cadences and this ticket's own merge-chase hit
the gap live. Locate NATIVE001's enforcing call site (likely
src/frob/strata/_native_staleness.py, landed alongside this rule per
the merge history) and add `frob:enforces CHK-GATE-NATIVE001` there, or
re-disposition the check-coverage.yaml entry if no single site owns it.

An earlier version of this ticket (T-1168, 11 different rules)
was filed and then dropped as moot once main's own concurrent work
resolved it -- this is a fresh, distinct finding (single rule,
NATIVE001), not a re-file of the same one.