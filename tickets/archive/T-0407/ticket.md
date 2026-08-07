---
id: T-0407
title: 'First-class REGISTRY capability: unified model, single source of truth, exhaustiveness
  gate (no early-exit)'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: T-0397
tier: ticket
sprint: null
scope:
- src/frob/
- docs/design/registry/
- pyproject.toml
- CHANGELOG.md
- .frob-release.json
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: pyproject.toml
  reason: REL001 required a version bump (0.59.0 -> 0.60.0) for T-0407's new public
    API (frob.registry module + frob registry CLI subcommand); pyproject.toml/CHANGELOG.md/.frob-release.json/uv.lock
    (uv sync regen) are the mechanical release-stamp artifacts that change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: REL001 required a version bump (0.59.0 -> 0.60.0) for T-0407's new public
    API (frob.registry module + frob registry CLI subcommand); pyproject.toml/CHANGELOG.md/.frob-release.json/uv.lock
    (uv sync regen) are the mechanical release-stamp artifacts that change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: REL001 required a version bump (0.59.0 -> 0.60.0) for T-0407's new public
    API (frob.registry module + frob registry CLI subcommand); pyproject.toml/CHANGELOG.md/.frob-release.json/uv.lock
    (uv sync regen) are the mechanical release-stamp artifacts that change
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: REL001 required a version bump (0.59.0 -> 0.60.0) for T-0407's new public
    API (frob.registry module + frob registry CLI subcommand); pyproject.toml/CHANGELOG.md/.frob-release.json/uv.lock
    (uv sync regen) are the mechanical release-stamp artifacts that change
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_registry_models.py::TestParseDisposition::test_handled_by
- tests/test_registry_models.py::TestParseDisposition::test_deferred
- tests/test_registry_models.py::TestParseDisposition::test_duplicate_of_underscore_and_hyphen
- tests/test_registry_models.py::TestParseDisposition::test_out_of_scope_paren_form
- tests/test_registry_models.py::TestParseDisposition::test_undispositioned_pending
- tests/test_registry_models.py::TestParseDisposition::test_undispositioned_none
- tests/test_registry_models.py::TestParseDisposition::test_undispositioned_bare_addressed
- tests/test_registry_models.py::TestParseDisposition::test_undispositioned_unparseable
- tests/test_registry_models.py::TestLoadRegistryDir::test_loads_typed_entries
- tests/test_registry_models.py::TestLoadRegistryDir::test_absent_file_not_in_result
- tests/test_registry_models.py::TestLoadRegistryDir::test_malformed_yaml_is_err
- tests/test_registry_models.py::TestLoadRegistryDir::test_not_a_mapping_is_err
- tests/test_registry_models.py::TestLoadRegistryDir::test_malformed_entry_counted
- tests/test_registry_models.py::TestLoadRegistryDir::test_split_entries_key_total
- tests/test_registry_models.py::TestAuditRegistryFile::test_counts_each_kind
- tests/test_registry_models.py::TestAuditRegistryFile::test_fully_dispositioned_file_is_exhausted
- tests/test_registry_exhaustiveness.py::TestMalformedEntry::test_malformed_entry_fails
- tests/test_registry_exhaustiveness.py::TestMalformedEntry::test_entry_missing_id_fails
- tests/test_registry_exhaustiveness.py::TestMalformedEntry::test_all_well_formed_entries_no_reg006
- tests/test_registry_exhaustiveness.py::TestDuplicateId::test_duplicate_id_across_files_fails
- tests/test_registry_exhaustiveness.py::TestDuplicateId::test_duplicate_id_same_file_fails
- tests/test_registry_exhaustiveness.py::TestDuplicateId::test_no_duplicate_ids_no_reg007
designated_repro_test: null
threat: null
component: null
---
User insight (2026-07-20): the REAL gap in vibe-coded capabilities is EARLY EXIT WITHOUT EXHAUSTING THE REGISTRY -- research enumerates a whole universe (CWEs, patterns, dangerous ops, languages, compliance regs, capabilities) then implementation handles only the top of the stack and the rest silently disappears. Every specific failure today is an instance: orphaned .yaml registries, ~30 of 944 CWEs enforced, TS/Rust/C++ unresolved, split-across-files corpus entries. FIX = make REGISTRY a first-class frob capability, not a pile of ad-hoc YAMLs + scattered code that desync.

Design: (1) UNIFIED MODEL -- one Registry abstraction (typed schema) that ALL registries instantiate (CWE/threat, design patterns, dangerous-operations, language-facet conformance, compliance, pii, secrets, capability kinds, supply-chain). (2) SINGLE SOURCE OF TRUTH per registry -- one canonical home; the gate rejects duplicate/split entries (same item under two ids, or an entry present in prose but not the registry). (3) EVERY ENTRY carries a DISPOSITION -- handled_by:<check/rule id verified to EXIST and FIRE> | deferred:<OPEN ticket id> | out_of_scope:{reason, caught_by verified}. No pending/missing allowed. (4) RESEARCH APPENDS TO THE REGISTRY -- the "file a ticket for everything" discipline becomes "every enumerated item is a registry entry", so nothing found is ever dropped; a research pass that finds N items must leave N dispositioned-or-explicitly-deferred entries. (5) EXHAUSTIVENESS GATE (fail-closed, ships + runs in every frob repo per T-0406): TOTAL enumerated == handled + deferred + out_of_scope; any undispositioned entry, any dangling handled_by/deferred, any split/duplicate, reds the build -- this is the anti-early-exit lock. (6) frob registry audit command surfaces per-registry coverage (X handled / Y deferred / Z out-of-scope / W UNACCOUNTED) so "did we exhaust it" is a one-line honest answer, never a vibe.

This SUBSUMES/GENERALIZES: T-0343 (design-corpus drift-lock -> one instance), T-0405 (language-facet conformance -> one instance), T-0384..0392 (per-registry reconciliation -> become "disposition every entry via the unified model"), the vet capability/dangerous-op tables (-> registry instances with resolvers). Reparent/relink those as instances/consumers of this model. Acceptance: a Registry with an undispositioned entry reds frob check; a handled_by naming a nonexistent rule fails; a duplicate entry across two files fails; frob registry audit reports honest per-registry accounting; adding a new registry is implementing the schema once. This is the structural guarantee that makes early-exit impossible across all projects.