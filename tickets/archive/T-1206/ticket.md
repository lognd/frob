---
id: T-1206
title: 'perf: tickets archive YAML on pure-Python loader -- CSafeLoader + parsed-archive
  cache'
state: done
kind: feature
origin: agent
created: '2026-07-29'
priority: high
parent: T-1204
tier: ticket
sprint: null
scope:
- src/frob/tickets/_store.py
- tests/unit/test_ticket_store.py
- docs/modules/tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_ticket_store.py
  reason: T-1206 CSafeLoader/cache change needs its own test file and updates the
    storage-internals doc anchor
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/modules/tickets.md
  reason: T-1206 CSafeLoader/cache change needs its own test file and updates the
    storage-internals doc anchor
  actor: logan
  at: '2026-07-29'
evidence:
- tests/unit/test_ticket_store.py::TestYamlLoader::test_prefers_csafeloader_when_libyaml_present
- tests/unit/test_ticket_store.py::TestYamlLoader::test_falls_back_to_safeloader_without_libyaml
- tests/unit/test_ticket_store.py::TestLoadArchiveCache::test_skips_reparse_when_content_hash_unchanged
- tests/unit/test_ticket_store.py::TestLoadArchiveCache::test_reparses_when_archive_content_changes
designated_repro_test: null
acceptance:
- text: 'GIVEN load_queue parses the tickets-archive.md ledger (1235+ yaml documents)
    WHEN yaml.safe_load is replaced with yaml.CSafeLoader (with pure-python SafeLoader
    fallback if libyaml absent) plus a content-hash-keyed parsed-archive cache in
    .frob/ THEN frob ticket doable drops from ~2.33s toward ~0.5-0.8s and every frob
    check that resolves blockers/joins the archive drops ~1.5-2s (report section ''Ranked
    PERF ticket candidates'' #1)'
  evidence:
  - tests/unit/test_ticket_store.py::TestYamlLoader::test_prefers_csafeloader_when_libyaml_present
  - tests/unit/test_ticket_store.py::TestYamlLoader::test_falls_back_to_safeloader_without_libyaml
  - tests/unit/test_ticket_store.py::TestLoadArchiveCache::test_skips_reparse_when_content_hash_unchanged
  - tests/unit/test_ticket_store.py::TestLoadArchiveCache::test_reparses_when_archive_content_changes
threat: null
component: null
---
Root cause: src/frob/tickets/_store.py:347 and :373 call yaml.safe_load per document (1235 docs/load_queue) with the pure-python SafeLoader even though libyaml/CSafeLoader is installed and unused (yaml.__with_libyaml__ True). 67 pct of the _load_inputs profile. Fix: switch to yaml.CSafeLoader, and since the archive is append-mostly, add a content-hash-keyed cache of the parsed archive in .frob/ invalidated on file hash change. Companion lint rule (do not duplicate here -- covered by the sibling 'perf: PERF01x detectors' ticket): 'yaml.safe_load/yaml.load without C loader in non-test code'.