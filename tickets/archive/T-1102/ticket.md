---
id: T-1102
title: 'gates/arch: wire large-file category into the GATE (LARGE001 WARN first-turn-on)
  + single-file-mode parity'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_arch.py
- src/frob/arch/__init__.py
- tests/test_arch_gate.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn
- tests/test_arch_gate.py::TestArchGateLargeFile::test_test_file_exempt_from_large001
- tests/test_arch_gate.py::TestArchGateLargeFile::test_single_file_mode_matches_directory_walk
designated_repro_test: null
acceptance:
- text: given a production source file over max_file_lines in any language in the
    obligation surface, when frob check runs, then a registered LARGE001 violation
    surfaces at WARN first-turn-on tier with the turn-on count disclosed
  evidence:
  - tests/test_arch_gate.py::TestArchGateLargeFile::test_large_file_fires_large001_warn
- text: given frob arch invoked on a single file over the threshold, when it runs,
    then the large-file finding prints exactly as the directory walk prints it
  evidence:
  - tests/test_arch_gate.py::TestArchGateLargeFile::test_single_file_mode_matches_directory_walk
threat: null
component: null
---
Refile: the original filing (f40dbd27) was eaten by the 4th pre-T-1090 id collision -- the id T-1098 now holds T-1087's land-debt ticket instead. Content: strata-core/src/parse.rs (4346 lines) is invisible to frob check because _ARCH_CATEGORY_TO_RULE maps only long-function/ARCH101-103/cpp-noexcept-throws; large-file is advisory-only and single-file mode skips the file-level check ('no architectural issues found' on a 4346-line file). Wire LARGE001, register + enforces edge, litmus-first tests, keep test-file/fixtures exemptions. Known offenders at filing: parse.rs 4346 (split = T-1099), frob-core/lib.rs 2277, tickets/_land.py 4762 (split = T-1089 in flight).