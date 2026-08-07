---
id: T-1076
title: 'arch: split 2000-5000 line files (T-0395 remainder tier 2)'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/app/ticket_runner.py
- src/frob/dup/_pipeline.py
- src/frob/__main__.py
- src/frob/gates/_pii_structural.py
- src/frob/_cli_parsers/**
- docs/commands/cli-vocabulary.md
- docs/modules/app.md
- tests/integration/test_interfaces.py
- tests/unit/test_main_entry.py
- docs/commands/check.md
- docs/guides/agentic-workflow.md
- docs/commands/exports.md
- docs/commands/scaffold.md
- docs/guides/install.md
- design/frob.strata
- docs/strata/roadmap.md
- docs/modules/cli.md
- src/frob/gates/_pii_structural/**
- docs/modules/gates.md
- tests/test_pii_structural_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/**
  reason: T-1076 __main__.py split into a package (T-1072 pattern); scope closure
    needs these doc/test targets
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/commands/cli-vocabulary.md
  reason: T-1076 __main__.py split into a package (T-1072 pattern); scope closure
    needs these doc/test targets
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/app.md
  reason: T-1076 __main__.py split into a package (T-1072 pattern); scope closure
    needs these doc/test targets
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/integration/test_interfaces.py
  reason: T-1076 __main__.py split into a package (T-1072 pattern); scope closure
    needs these doc/test targets
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/test_main_entry.py
  reason: T-1076 __main__.py split into a package (T-1072 pattern); scope closure
    needs these doc/test targets
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/commands/check.md
  reason: 'T-1076 scope closure: __main__.py -> _cli_parsers split moved frob:doc-target
    symbols; docs describing them must be in scope'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/guides/agentic-workflow.md
  reason: 'T-1076 scope closure: __main__.py -> _cli_parsers split moved frob:doc-target
    symbols; docs describing them must be in scope'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/commands/exports.md
  reason: 'T-1076 scope closure: __main__.py -> _cli_parsers split moved frob:doc-target
    symbols; docs describing them must be in scope'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/commands/scaffold.md
  reason: 'T-1076 scope closure: __main__.py -> _cli_parsers split moved frob:doc-target
    symbols; docs describing them must be in scope'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/guides/install.md
  reason: 'T-1076 scope closure: __main__.py -> _cli_parsers split moved frob:doc-target
    symbols; docs describing them must be in scope'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: design/frob.strata
  reason: 'T-1076: __main__.py split off a new src/frob/_cli_parsers/ package; the
    cli node''s code= glob in design/frob.strata must own it too or SELFAUDIT001 fires
    (unmodeled code)'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/strata/roadmap.md
  reason: 'T-1076: design/frob.strata''s cli node code= glob edit pulls in every node''s
    shared affects()-closure doc target'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/cli.md
  reason: 'T-1076: design/frob.strata''s cli node code= glob edit pulls in every node''s
    shared affects()-closure doc target'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: src/frob/gates/_pii_structural/**
  reason: 'T-1076: fix pre-existing scope glob left over from the earlier _pii_structural.py
    -> package split (T-1076 first commit), which the file->package rename made stale'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/gates.md
  reason: 'T-1076: fix pre-existing scope glob left over from the earlier _pii_structural.py
    -> package split (T-1076 first commit), which the file->package rename made stale'
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_pii_structural_gate.py
  reason: 'T-1076: earlier _pii_structural.py -> package split (first commit) touched
    this test file but never added it to scope'
  actor: logan
  at: '2026-07-28'
evidence:
- tests/unit/test_main_entry.py::TestMainSigint::test_keyboard_interrupt_prints_clean_message_and_exits_130
- tests/unit/test_main_entry.py::TestMainSigint::test_normal_dispatch_is_unaffected
- tests/unit/test_main_entry.py::TestDidYouMean::test_unknown_subcommand_suggests_closest
- tests/test_gates.py::TestCoverageGate::test_cov003_remediation_hint_names_no_nonexistent_flag
- tests/test_ticket_land.py::TestSkipMutationEvidenceCliWiring::test_flag_parses_to_true
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
---
Filed from T-0395 (failed as too large for one pass). Second tier of the
large-file residue (2000-5000 lines, in-scope after excluding
src/frob/strata/**/vet/**): src/frob/tickets/_land.py (4658),
src/frob/tickets/__init__.py (4048), src/frob/app/ticket_runner.py
(3923), src/frob/dup/_pipeline.py (2628), src/frob/__main__.py (2593),
src/frob/gates/_pii_structural.py (2170). Each needs its own module-split
plan (real decomposition into cohesive sibling files, mirroring each
package's existing pattern where one exists) and full-suite
verification per file -- do not batch all six into one diff; land
incrementally. large-file is unwaivable (docs/modules/gates.md); a file
that genuinely does not decompose cleanly still needs the ticket to say
so explicitly with the specific reason (not a silent skip), per this
ticket's own acceptance framing.