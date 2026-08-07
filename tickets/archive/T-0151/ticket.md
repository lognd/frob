---
id: T-0151
title: vet capability scanner self-matches its own pattern-table literals
state: done
kind: bug
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability.py
- tests/test_vet.py
- design/frob.strata
- docs/modules/vet.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_vet.py::TestCapabilityScan::test_re_compile_alone_does_not_report_eval
- tests/test_vet.py::TestCapabilityScan::test_bare_compile_call_still_reports_eval
- tests/test_vet.py::TestCapabilityScan::test_genuine_eval_still_detected
- tests/test_vet.py::TestCapabilityScan::test_capability_module_self_scan_documented_false_positive
- tests/test_vet.py::TestCapabilityScan::test_scan_directory_capabilities_excludes_own_module
designated_repro_test: null
threat: null
component: null
---
Found while measuring real capabilities for T-0150's design/frob.strata may declarations: scan_file_capabilities/scan_directory_capabilities substring-matches _PATTERNS' own needle literals (e.g. "subprocess.", "compile(", "cmdclass") when scanning src/frob/vet/_capability.py itself, since those needles are stored as plain string data in that same file. This inflates vet's own observed capability set (T-0150 measured vet as declaring eval/exec/ffi/install-hook/env/net almost entirely from this one file matching itself) and would similarly inflate the scan of any OTHER file that happens to embed one of these substrings in a comment/string/docstring (T-0150's own _threat.py DEFAULT_BENIGN_CAPABILITIES reason strings tripped this exact false-positive during T-0150's rework, before rewording). Needs either: excluding the pattern-table-defining file itself from self-scanning, or a smarter match (e.g. AST-based real call-site detection instead of raw substring match), or a documented/accepted false-positive-rate note in docs/modules/vet.md. Out of scope for T-0150 (scope excludes src/frob/vet -- T-0147 concurrently edits it).