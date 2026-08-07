---
id: T-0500
title: 'strata audit G4: FOREIGN file in an already-modeled directory (or loose under
  src/frob/) escapes ALL sys rules + THREAT004/005'
state: done
kind: security
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_selfconform.py
- design/frob.strata
- tests/unit/strata/test_selfconform.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: closing SYS102's per-file grain surfaced 3 real top-level src/frob/*.py
    files (__init__.py, doctor.py, excludes.py) with no code= glob owner; must extend
    the self-model to keep TestRealGateGreen green, and update selfconform unit tests
    for the new per-file violation grain
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/strata/test_selfconform.py
  reason: closing SYS102's per-file grain surfaced 3 real top-level src/frob/*.py
    files (__init__.py, doctor.py, excludes.py) with no code= glob owner; must extend
    the self-model to keep TestRealGateGreen green, and update selfconform unit tests
    for the new per-file violation grain
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/strata/test_selfconform.py::TestUnmodeledCodeForeignFileGranularity::test_foreign_file_in_otherwise_owned_directory_fires
- tests/unit/strata/test_selfconform.py::TestUnmodeledCodeForeignFileGranularity::test_loose_top_level_file_fires
- tests/unit/strata/test_selfconform.py::TestUnmodeledCodeForeignFileGranularity::test_loose_top_level_file_discharges_once_globbed
- tests/unit/strata/test_selfconform.py::TestUnmodeledCode::test_unmodeled_code_fires
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
designated_repro_test: null
threat: null
component: null
---
docs/audits/strata.md G4 (HIGH), from T-0401. _selfconform.py:538 _unmodeled_violations marks a directory owned if ANY file in it is non-FOREIGN; SYS100/101 and effect-extraction scan only _sorted_owned_files. A new .py/.ts file placed in an existing modeled directory but matched by no code= glob is FOREIGN -> invisible to capability observation AND does not trip SYS102 (its directory is already prefix_owned). SYS102 also only iterates directories (_top_level_dirs), so a FOREIGN file placed directly under src/frob/ (not in a subdir) also escapes. Repro: src/frob/vet/backdoor.py doing subprocess.run(user_input) where no node's code= glob matches backdoor.py -> frob sys audit stays clean. Fix direction: SYS102 must fire per-FOREIGN-file (or per unowned file within an owned dir), not per fully-FOREIGN top-level dir; effect extraction should raise on any FOREIGN capability-scannable file rather than skipping it.