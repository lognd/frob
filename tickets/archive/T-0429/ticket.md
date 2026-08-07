---
id: T-0429
title: 'Exhaustive-researcher: mechanism to emit into the universe corpus (stable
  ids, schema, denominator proof) so research -> registry -> enforcement is one loop'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: T-0407
tier: ticket
sprint: null
scope:
- .claude/agents/
- src/frob/
- docs/guides/
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_registry_corpus.py::TestFormatEntryBlock::test_pending_disposition_always
- tests/test_registry_corpus.py::TestFormatEntryBlock::test_source_doc_included_when_given
- tests/test_registry_corpus.py::TestFormatEntryBlock::test_source_doc_omitted_when_blank
- tests/test_registry_corpus.py::TestAppendEntry::test_append_adds_entry_and_bumps_total
- tests/test_registry_corpus.py::TestAppendEntry::test_append_always_pending_never_a_real_disposition
- tests/test_registry_corpus.py::TestAppendEntry::test_duplicate_id_rejected
- tests/test_registry_corpus.py::TestAppendEntry::test_missing_file_rejected
- tests/test_registry_corpus.py::TestAppendEntry::test_missing_key_rejected
- tests/test_registry_corpus.py::TestAppendEntry::test_no_declared_total_left_untouched
designated_repro_test: null
threat: null
component: null
---
User (2026-07-20): ensure the exhaustive researcher has the mechanisms to MAKE the exhaustive registries. Today the exhaustive-researcher agent enumerates to an external store but there is no clean mechanism to emit its findings INTO the universe corpus in the format the registry/exhaustiveness gate consumes -- so research and enforcement are disconnected (the root of the orphaned-registry breach). Give the researcher the mechanism: (1) the corpus SCHEMA (stable per-entry ids, name, source/citation, the append-only universe format) documented + a helper/command to append entries (frob registry add / a corpus-emit tool) so a research pass writes directly into the universe SSOT, not a prose doc that later has to be transcribed. (2) The DENOMINATOR/EXHAUSTIVENESS proof: research declares the TOTAL it enumerated so the exhaustiveness gate (T-0343 REG005 / the derived model in the sibling ticket) can verify count == entries -- nothing dropped between research and corpus. (3) Under the DERIVED-registry model (sibling ticket), the researcher does NOT assign dispositions (those are code-derived) -- it only enumerates the universe COMPLETELY; make the researcher agent brief + tooling reflect that (append to universe, prove the denominator, done). Acceptance: an exhaustive-research pass emits N corpus entries with stable ids + a declared total; the exhaustiveness gate confirms N==entries; a follow-up code change adding frob:enforces for some of them shows coverage rise automatically; nothing the researcher found is left as untranscribed prose. Closes the research->registry->enforcement loop so a future corpus cannot become orphaned docs.