---
id: T-0180
title: 'closed-world unknown-import accounting: vetted-library cache engine (T-0158
  addendum 2 remainder)'
state: done
kind: security
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- tests/**
- docs/modules/vet.md
- pyproject.toml
- CHANGELOG.md
- .frob-release.json
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_vet.py::TestClosedWorldAccounting::test_walk_python_imports_collects_absolute_imports_only
- tests/test_vet.py::TestClosedWorldAccounting::test_walk_python_imports_skips_unparseable_files
- tests/test_vet.py::TestClosedWorldAccounting::test_resolve_import_registry_match
- tests/test_vet.py::TestClosedWorldAccounting::test_resolve_import_registry_match_via_pypi_name_override
- tests/test_vet.py::TestClosedWorldAccounting::test_resolve_import_no_capability_match
- tests/test_vet.py::TestClosedWorldAccounting::test_resolve_import_vetted_via_local_source_scan_and_cache
- tests/test_vet.py::TestClosedWorldAccounting::test_resolve_import_unknown_when_unresolvable
- tests/test_vet.py::TestClosedWorldAccounting::test_closed_world_accounting_source_unavailable
- tests/test_vet.py::TestClosedWorldAccounting::test_closed_world_accounting_full_pass
- tests/test_vet.py::TestClosedWorldAccounting::test_closed_world_accounting_closed_when_no_unknowns
- tests/test_vet.py::TestClosedWorldAccounting::test_import_resolution_model_fields
designated_repro_test: null
threat: null
component: null
---
T-0158 shipped the single-source dangerous-operations registry, the (kind x language) coverage matrix with 0 unexcused cells, and the sys-audit matrix-verdict proof line. NOT shipped (too large for one pass, explicitly deferred per T-0158's own escape valve): addendum 2 deliverable (2), full CLOSED WORLD accounting -- resolving every third-party import in a vetted dependency's source to (a) a registry entry, (b) a VETTED library (same scanner engine run over the installed third-party source, cached per package+version, e.g. reusing the frob.vet._cache.py sqlite pattern), or (c) a LOUD 'unknown, unvetted, uninspected' failure -- with the audit accounting line (N registry ops, M vetted libraries, K explicit no-capability entries, 0 unknown) T-0158's addendum 2 describes. T-0158's sys-audit line covers the (kind x language) MATRIX proof only, not this import-resolution closed-world proof. Needs: an import-graph walk per vetted package (python ast.parse imports at minimum), a resolution function classifying each imported name against DANGEROUS_OPERATIONS/registry libraries vs NO_CAPABILITY_MODULES vs unresolved, and a persistent per-package+version cache keyed like _cache.py's verdict cache.