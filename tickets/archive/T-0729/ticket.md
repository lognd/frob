---
id: T-0729
title: 'sys audit red on main: _srp.py classifier string tables read as graphlang
  capability observations (4x SYS100)'
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: critical
parent: T-0330
tier: ticket
sprint: null
scope:
- src/frob/arch/_srp.py
- design/frob.strata
- src/frob/strata/**
- src/frob/vet/_capability.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/vet/_capability.py
  reason: the established self-pattern-path exemption mechanism (T-0201/T-0253) that
    classifier corpora use to escape SYS100 lives in this file (_SELF_PATTERN_SUFFIXES/is_self_pattern_path);
    mirroring it for _srp.py's tables requires adding _srp.py's own suffix entry here
  actor: logan
  at: '2026-07-22'
evidence:
- tests/unit/test_arch_srp.py::TestMixedConcernFunction::test_io_compute_and_formatting_together_trigger
- tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_covers_every_needle_table_module
- tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_survives_a_foreign_install_copy
designated_repro_test: null
acceptance:
- text: GIVEN main after the fix WHEN frob sys audit runs THEN zero SYS100 gaps and
    no dishonest may declarations were added
  evidence: []
threat: null
component: null
---
T-0616's landed _srp.py carries curated classifier tables (_IO_MODULE_PREFIXES: socket., subprocess., requests., urllib. ...) that the capability scanner -- which keys on string-literal content by design, for evasion detection -- reads as live net/exec/fetch_url observations on the graphlang node: frob sys audit on main now reports 4 SYS100 gaps (zero-errors violation). These strings are classifier DATA, not capability usage. Disposition honestly at the correct layer: per-observation waiver with reason (classifier corpus, not usage -- cite the file/lines) via the established SYS waive channel, OR if the scanner has a data-table exemption convention, use it; declaring may net/exec on graphlang would be DISHONEST (the node does no such thing). Found by T-0724's rework (its T-draft-890e0667 duplicates this -- reconcile at land).