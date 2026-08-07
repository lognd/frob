---
id: T-0209
title: capability scanner matches needles inside comments and strings
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability.py
- src/frob/lang/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_vet.py::TestCapabilityScan::test_comment_only_needle_does_not_fire
- tests/test_vet.py::TestCapabilityScan::test_real_code_needle_still_fires_alongside_comment
- tests/test_vet.py::TestCapabilityScan::test_string_literal_needle_still_fires
- tests/test_vet.py::TestCapabilityScan::test_capability_module_self_scan_documented_false_positive
- tests/test_vet.py::TestCapabilityScan::test_re_compile_alone_does_not_report_eval
- tests/test_vet.py::TestCapabilityScan::test_bare_compile_call_still_reports_eval
- tests/test_vet.py::TestCapabilityScan::test_genuine_eval_still_detected
- tests/test_vet.py::TestCapabilityScan::test_scan_directory_capabilities_excludes_own_module
designated_repro_test: null
threat: null
component: null
---
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 aprog-public: SYS100 reported capability net observed at assignments/api-harvester/assets/starter.py:22 -- that line is COMMENT text describing requests.get; the assignment forbids real network imports. Forced a false may declaration dragging bogus CWE-918 obligations -- corrupts the security posture the model attests (medium-high). Fix: consult tree-sitter comment/string spans (already produced by frob.lang) before substring matching; needle hits fully inside comment spans are dropped (string literals are subtler -- keep string hits for languages where code-in-string is an exec vector, e.g. eval payloads, but drop pure-comment hits everywhere). Litmus: comment-only fixture must NOT fire; code fixture still fires; the T-0151/T-0201 self-match tests stay green. Note duplicate-line issue too: the same site was reported twice (pilot gap 12) -- dedupe observations by (file,line,kind) while in there.