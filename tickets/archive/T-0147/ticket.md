---
id: T-0147
title: 'frob vet: match dependencies against a local cvelistV5 mirror, link CVEs to
  the threat catalog'
state: done
kind: feature
origin: human
created: '2026-07-18'
priority: medium
blocked_by:
- T-0146
parent: null
tier: ticket
sprint: null
scope:
- src/frob/cve/**
- src/frob/vet/**
- tests/unit/cve/**
- docs/modules/vet.md
- tickets.md
- src/frob/app/config.py
- src/frob/app/vet_runner.py
- src/frob/__main__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/cve/test_vet_match.py::test_affected_within_clean_semver_range
- tests/unit/cve/test_vet_match.py::test_unaffected_via_less_than_boundary
- tests/unit/cve/test_vet_match.py::test_unaffected_via_default_status
- tests/unit/cve/test_vet_match.py::test_indeterminate_versiontype_custom_never_silently_unaffected
- tests/unit/cve/test_vet_match.py::test_indeterminate_default_status_unknown
- tests/unit/cve/test_vet_match.py::test_rejected_record_skipped_never_matched
- tests/unit/cve/test_vet_match.py::test_cwe_linkage_catalog_out_of_scope_and_unmapped
- tests/unit/cve/test_vet_match.py::test_log4shell_end_to_end_cwe_linkage_via_mirror
- tests/unit/cve/test_vet_match.py::test_missing_mirror_is_loud_typed_failure
- tests/unit/cve/test_vet_match.py::test_no_dependencies_still_walks_mirror_cleanly
- tests/unit/cve/test_vet_match.py::test_unconfigured_mirror_is_a_silent_no_op
designated_repro_test: null
threat: null
component: null
---
Build on the T-0146 parser: frob vet gains CVE matching against a local cvelistV5 mirror directory (configured via [tool.frob] in pyproject.toml; explicit CLI flag override). Match project dependencies (name plus installed version) against affected[] product/version ranges honoring lessThan/lessThanOrEqual/versionType/status semantics; report CVE id, CVSS score/severity, and description. Link each CVE's problemTypes CWE ids to the strata threat catalog (CWE_CATALOG plus CWE_TOP_25_CATALOG) so a dependency CVE citing e.g. CWE-89 names the catalog entry and mitigation that covers it, and OutOfScopeEntry ids are reported as such. Loud typed failure when a mirror path is configured but missing or unreadable (vacuous-pass doctrine); clean no-op only when no mirror is configured. Tests: fixture mirror dir with a handful of real records; matching cases covering range semantics, rejected records skipped-with-log, and the CWE linkage.

Scope note (added during implementation): the ticket's own "explicit CLI flag override" requirement for the mirror path is unsatisfiable without touching CLI wiring, which lives outside src/frob/vet/**/src/frob/cve/** -- src/frob/app/config.py (AppConfig.vet_cve_mirror field, [tool.frob] wiring), src/frob/app/vet_runner.py (--cve-mirror dispatch, output), and src/frob/__main__.py (the --cve-mirror argparse flag) were added to scope for this reason. No other files outside the original scope were touched.