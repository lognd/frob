---
id: T-0915
title: 'fix: exclude frob.arch._async_hazards from SELFAUDIT001 net/exec self-match'
state: done
kind: bug
origin: human
created: '2026-07-26'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/_capability.py
- tests/test_vet.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_vet.py
  reason: regression tests for the exclusion live here per T-0910 precedent
  actor: logan
  at: '2026-07-26'
evidence:
- tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_covers_async_hazards_needle_tuples
- tests/test_vet.py::TestFingerprintScan::test_line_effects_reports_no_capability_on_async_hazards_module
designated_repro_test: null
threat: null
component: null
---
frob check --only gates-security's SELFAUDIT001/SYS100 stage flags
src/frob/arch/_async_hazards.py (T-0696) as undeclared 'net'/'exec'
capability usage on the graphlang node: capability 'net' observed at
line 67, capability 'exec' observed at line 72. Both are false positives
of the same class already fixed for src/frob/arch/_srp.py (T-0729) and
src/frob/arch/_logging_checks.py (T-0910): _BLOCKING_CALL_TABLE is a
curated dotted-name classifier table (time.sleep, requests.get/post/...,
urlopen, subprocess.run/call/...) this module's _blocking_label compares
a CALLEE STRING against -- the scanner keys on string-literal CONTENT by
design (for evasion detection), so naming these substrings as data reads
as live capability usage even though _async_hazards.py does no such I/O
itself (a syntactic, tree-sitter-only scan).

Fix: add ("frob", "arch", "_async_hazards.py") to
src/frob/vet/_capability.py's _SELF_PATTERN_SUFFIXES tuple, mirroring the
_srp.py/_logging_checks.py entries and their doc comments. Out of T-0696's
declared scope (src/frob/arch/**, tests/unit/test_arch.py only), which is
why this is filed separately rather than fixed inline.