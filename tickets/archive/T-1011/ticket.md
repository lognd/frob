---
id: T-1011
title: auto-sync check-coverage gate_rule_entries at land + generate command tables
  from argparse registry
state: done
kind: feature
origin: human
created: '2026-07-27'
priority: medium
parent: T-1008
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
- src/frob/app/**
- docs/**
- tests/**
- src/frob/gates/_docblocks.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_docblocks.py
  reason: T-1011(b) implements DOC005 freshness check + generator inside frob.gates._docblocks
    (docs/audits/coordination-churn.md item 3 sibling deliverable)
  actor: logan
  at: '2026-07-27'
body_changes:
- mode: append
  reason: condense narrative into cited ticket body per T-4691 C5 sweep
  actor: logan
  at: '2026-09-19'
  old_length: 454
  new_length: 2254
evidence:
- tests/ticket_land_suite/test_push.py::TestSyncGateRulesCallback::test_sync_gate_rules_none_is_noop
- tests/ticket_land_suite/test_push.py::TestSyncGateRulesCallback::test_sync_gate_rules_applies_and_stages
- tests/ticket_land_suite/test_push.py::TestSyncGateRulesCallback::test_sync_gate_rules_failure_unwinds
- tests/test_docblocks_gate.py::TestCliCommandTableGenerator::test_generate_sorts_rows_across_sources
- tests/test_docblocks_gate.py::TestCliCommandTableGenerator::test_generate_no_config_is_none
- tests/test_docblocks_gate.py::TestCliCommandTableGenerator::test_sync_replaces_only_the_marked_block
- tests/test_docblocks_gate.py::TestCliCommandTableGenerator::test_sync_no_markers_returns_false
- tests/test_docblocks_gate.py::TestCliCommandTableGenerator::test_doc005_freshness_flags_stale_generated_block
- tests/test_docblocks_gate.py::TestCliCommandTableGenerator::test_doc005_freshness_passes_after_sync
- tests/unit/test_app_runners_batch5.py::TestDocsRunner::test_sync_commands_writes
designated_repro_test: null
acceptance:
- text: given a land whose diff adds a gate rule id, when it lands, then check-coverage.yaml
    carries the new row with no manual sync; given a new CLI subcommand, docs sync
    regenerates both tables and DOC005 verifies freshness
  evidence:
  - tests/ticket_land_suite/test_push.py::TestSyncGateRulesCallback::test_sync_gate_rules_applies_and_stages
  - tests/test_docblocks_gate.py::TestCliCommandTableGenerator::test_doc005_freshness_passes_after_sync
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Children 3+4 of T-1008 (bundled: both are generate-at-the-source items). (a) land runs the existing registry --sync-gate-rules automatically when _KNOWN_GATE_RULES changed in the landing diff, ending manual re-syncs (drifted twice this drive). (b) README and docs/modules/cli.md command tables become generated from the live argparse registry (frob docs sync-commands or equivalent), turning DOC005 from a hand-sync lock into a generator-freshness check.

<!-- narrative-moved:src/frob/graph/dsl.py:595:T-1011 -->
Verbs a DIFFERENT module owns and reads directly from markdown text --
never routed through `_directive_edge` at all, so reaching this function
with one of these is not evidence of anything broken:
- `generated-start`/`generated-end`: `frob.gates._docblocks`'s table
  fence markers (T-1011).
- `invariant`: `frob.gates._inv._DOC_INVARIANT_MARKER_RE` (INV002/
  INV003/INV004's own markdown-side anchor, T-1989 -- the code-comment
  form `# frob:invariant INV-###` already routes through `_VERB_TABLE`
  above; this is markdown's separate, independently-read form of the
  SAME verb, not a second directive).
- `claims`: `frob.gates._sys._CLAIMS_RE` (DOC003's exhaustiveness-proof
  marker, T-1989).
- `external-reader`: `frob.gates._root_asset_dirs._EXTERNAL_READER_RE`
  (ROOT001's own markdown-side anchor declaring that some process
  OUTSIDE this repo's code reads a root-level directory, T-3720).
  Deliberately its own dedicated regex there rather than routed through
  the full DSL edge machinery -- a repo-root directory audit is rare
  enough (a few times a year, per T-1611) that a dedicated DSL edge kind
  is not worth the maintenance surface. Before this fix, ROOT001's own
  prescribed remedy (add this exact directive) tripped DSL001 as an
  unhandled verb -- a gate remedy that another gate rejected, with no
  clean path through both.
- `_RESERVED_MARKER_VERBS` (used-by/secret-fake/raises): already
  recognized as owned-elsewhere for the code-comment path above; T-1989
  folds the same set in here since their own scanners (frob.gates._refs,
  frob.gates._secrets, frob.gates._exhaustive_handling) read raw text
  across every tracked file type, markdown included, not just source.
frob:ticket T-1989
frob:ticket T-3720