---
id: T-0208
title: vet obfuscation scan pathologically slow -- high_entropy_strings dominates,
  no progress/timeout
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- tests/**
- docs/modules/vet.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_vet.py::TestObfuscationEnsemble::test_high_entropy_string_flagged
- tests/test_vet.py::TestObfuscationEnsemble::test_plain_string_not_flagged
- tests/test_vet.py::TestObfuscationEnsemble::test_bidi_override_is_fatal
- tests/test_vet.py::TestObfuscationEnsemble::test_clean_text_no_bidi
- tests/test_vet.py::TestObfuscationEnsemble::test_hex_identifier_ratio_flagged
- tests/test_vet.py::TestObfuscationEnsemble::test_normal_identifiers_not_flagged
- tests/test_vet.py::TestObfuscationEnsemble::test_high_entropy_strings_returns_the_literal
- tests/test_vet.py::TestObfuscationEnsemble::test_high_entropy_strings_empty_for_plain_text
- tests/test_vet.py::TestObfuscationEnsemble::test_scan_directory_obfuscation_finds_signal_in_one_file
- tests/test_vet.py::TestScanTreeTimeout::test_slow_package_returns_within_timeout_not_task_duration
designated_repro_test: null
threat: null
component: null
---
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 (all 3 repos): frob vet unusable -- lograder killed at 11m47s with 15/30 packages (101MB venv); aprog-public stuck on numpy at 120s. cProfile+SIGALRM around scan_tree(fetch=False): _obfuscation.py:70 high_entropy_strings consumed 82 of 120 profiled seconds (785 calls); tree-sitter/capability scans fine. Fix: cap candidate string count/length per file, skip literal-table files over a size threshold, optimize the entropy loop, add per-package progress lines and --timeout/--jobs. Acceptance: frob vet completes on lograder's venv under 2 minutes with progress output.