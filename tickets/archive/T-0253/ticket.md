---
id: T-0253
title: self-path exclusion breaks under non-editable installs -- global frob self-audit
  shows 36 false SYS100s
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
- src/frob/strata/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_does_not_fire_when_vetting_a_dependency
- tests/test_vet.py::TestFingerprintScan::test_self_pattern_exclusion_survives_a_foreign_install_copy
designated_repro_test: null
threat: null
component: null
---
T-0156 closing-review finding, now reproducible on main: is_self_pattern_path (T-0201) resolves the RUNNING package's module file paths, so the exclusion only matches when the scanned tree IS the running package (editable install). Under the uv-tool global binary, scanning frob's own checkout self-matches all pattern-catalog needle literals again: frob sys audit = 36 SYS100 false gaps; uv run frob sys audit = 0. Only affects auditing frob's own repo with a non-editable binary (sibling repos have no pattern files), but that is exactly what CI or a user would do. Fix: match by repo-relative path suffix of the KNOWN pattern files (src/frob/vet/_capability.py, _capability_registry.py, strata/_cve_fingerprint.py) against the SCANNED tree, not identity of the running package's files; keep the T-0201 drift-lock and extend it with a test that simulates a foreign-install scan (copy the tree to a tmp path, scan with the exclusion, assert zero self-matches).