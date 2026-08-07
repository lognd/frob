---
id: T-1424
title: 'T-1270 file splits left 24 errors on main: stale doc edges, orphaned invariant
  waivers, and a relocated 392-line function'
state: done
kind: bug
origin: human
created: '2026-08-02'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- docs/guides/**
- src/frob/app/_config_external.py
- src/frob/_cli_parsers/_ticket/**
- invariants/**
- docs/modules/arch.md
- tests/unit/test_app_lazy_dispatch.py
- tests/unit/test_app_lazy_exports.py
- tests/unit/test_arch.py
- tests/unit/test_ticket_runner_land_cmd_flags.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/arch.md
  reason: T-1424's own DRIFT002/INV005 findings name these files directly (stale doc
    edges, evidence edges) -- not scope creep, the fix targets
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/unit/test_app_lazy_dispatch.py
  reason: T-1424's own DRIFT002/INV005 findings name these files directly (stale doc
    edges, evidence edges) -- not scope creep, the fix targets
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/unit/test_app_lazy_exports.py
  reason: T-1424's own DRIFT002/INV005 findings name these files directly (stale doc
    edges, evidence edges) -- not scope creep, the fix targets
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/unit/test_arch.py
  reason: T-1424's own DRIFT002/INV005 findings name these files directly (stale doc
    edges, evidence edges) -- not scope creep, the fix targets
  actor: logan
  at: '2026-08-02'
- op: add
  glob: tests/unit/test_ticket_runner_land_cmd_flags.py
  reason: T-1424's own DRIFT002/INV005 findings name these files directly (stale doc
    edges, evidence edges) -- not scope creep, the fix targets
  actor: logan
  at: '2026-08-02'
evidence:
- tests/unit/test_app_lazy_dispatch.py::TestResolveRunner::test_imports_only_the_requested_subcommands_module
- tests/unit/test_app_lazy_exports.py::TestLazyRunnerRunAttrs::test_accessing_one_alias_does_not_import_the_others
- tests/unit/test_ticket_runner_land_cmd_flags.py::TestAllowCrossTicketFlagParsing::test_flag_sets_the_namespace_dest
- tests/unit/test_arch.py::TestLargeFile::test_calibrated_frob_toml_threshold_suppresses_600_line_flag
designated_repro_test: null
acceptance:
- text: GIVEN main after T-1270 WHEN an UNSCOPED frob check runs THEN it reports zero
    errors
  evidence:
  - tests/unit/test_app_lazy_dispatch.py::TestResolveRunner::test_imports_only_the_requested_subcommands_module
  - tests/unit/test_app_lazy_exports.py::TestLazyRunnerRunAttrs::test_accessing_one_alias_does_not_import_the_others
  - tests/unit/test_ticket_runner_land_cmd_flags.py::TestAllowCrossTicketFlagParsing::test_flag_sets_the_namespace_dest
  - tests/unit/test_arch.py::TestLargeFile::test_calibrated_frob_toml_threshold_suppresses_600_line_flag
- text: GIVEN _build_external_config_kwargs WHEN the arch gate runs THEN it is under
    the 60-line threshold by genuine decomposition, not a waiver
  evidence:
  - tests/unit/test_app_lazy_dispatch.py::TestResolveRunner::test_imports_only_the_requested_subcommands_module
  - tests/unit/test_app_lazy_exports.py::TestLazyRunnerRunAttrs::test_accessing_one_alias_does_not_import_the_others
  - tests/unit/test_ticket_runner_land_cmd_flags.py::TestAllowCrossTicketFlagParsing::test_flag_sets_the_namespace_dest
  - tests/unit/test_arch.py::TestLargeFile::test_calibrated_frob_toml_threshold_suppresses_600_line_flag
- text: GIVEN each re-acked doc edge WHEN reviewed THEN the doc still accurately describes
    the symbol it points at, confirmed per edge rather than blanket-acked
  evidence:
  - tests/unit/test_app_lazy_dispatch.py::TestResolveRunner::test_imports_only_the_requested_subcommands_module
  - tests/unit/test_app_lazy_exports.py::TestLazyRunnerRunAttrs::test_accessing_one_alias_does_not_import_the_others
  - tests/unit/test_ticket_runner_land_cmd_flags.py::TestAllowCrossTicketFlagParsing::test_flag_sets_the_namespace_dest
  - tests/unit/test_arch.py::TestLargeFile::test_calibrated_frob_toml_threshold_suppresses_600_line_flag
threat: null
component: null
---
T-1270's file splits (commit 1dc8ce86) landed 24 errors onto main. The splits themselves are good work with real seams and should NOT be reverted; this ticket cleans up the residue they left outside their own scope.

MEASURED on main 2026-08-02, unscoped frob check:

  18 x DRIFT002 -- doc describes-edges and test edges pointing at code that moved. Six still name src/frob/_cli_parsers/_ticket.py, which no longer exists (it became a package). Twelve name src/frob/app/config.py and src/frob/app/_config_meta.py, whose digests changed when from_external and the repo-metadata helpers were extracted. docs/guides/agentic-workflow.md carries several of them.
  5 x INV006 -- each of the five new src/frob/_cli_parsers/_ticket/ modules now makes an exclusivity or normative claim. The original _ticket.py carried a single file-level waiver for that claim; splitting the file split the claim across five files and left the waiver behind on none of them.
  1 x INV005 -- INV-049's evidence never reaches its frob:invariant anchor.
  1 x ARCH001 -- _build_external_config_kwargs in the new src/frob/app/_config_external.py has 392 lines against a 60-line threshold. This is the 380-line argparse field-copy loop extracted verbatim from config.py. The extraction moved a LARGE001 violation and created an ARCH001 one; the function itself was never broken up.

WHY IT GOT THROUGH, worth recording because it will recur. The implementing agent drove frob check --ticket T-1270 to zero errors and reported it honestly. That is a TICKET-SCOPED zero. Every one of these 24 findings lives outside the ticket's declared scope -- in docs/, in tests/, or in files the split created -- so the scoped run could not see them. This is exactly the hazard playbook section 6c documents, and the scope-note it prints was not enough to catch it. Coordinators must re-measure UNSCOPED after landing a refactor that moves symbols between files; a scoped zero is not a repo zero.

THE WORK.

For DRIFT002: repoint each stale edge at the symbol's new home, then re-ack the ones whose target is unchanged but whose digest moved (frob ack is the designed remedy for a re-verified reference). Do not blanket-ack -- read each edge and confirm the doc still describes what it points at. An ack on a doc that is now wrong is worse than the drift finding.

For INV006: carry the original file-level waiver onto whichever of the five modules genuinely makes the claim, with its reason intact. If a module does not actually make an exclusivity claim, it needs no waiver -- check rather than copying all five.

For ARCH001: split _build_external_config_kwargs properly. A 392-line argparse field-copy loop is mechanical and should decompose cleanly by field group. Do not waive it -- the whole point of T-1270 was reducing genuine size, and accepting a 392-line function would make the parent ticket a wash.

For INV005: bind evidence that reaches INV-049's anchor, or explain why it cannot.

Verify UNSCOPED before reporting: an unscoped frob check must be back to zero errors. A --ticket-scoped zero is not acceptable evidence for this ticket specifically, given that a scoped zero is what let the regression land.