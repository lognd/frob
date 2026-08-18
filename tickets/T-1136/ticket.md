---
id: T-1136
title: 'EPIC ledger v2: per-ticket files replace the tickets.md monofile (design first,
  then migration)'
state: queued
kind: feature
origin: human
created: '2026-07-28'
priority: high
parent: null
tier: epic
sprint: null
runs_last: false
scope:
- docs/design/**
- tests/**
scope_breadth_ack: true
scope_breadth_ack_reason: 'WAVE14-B (T-draft-57d64be9): this is a genuine epic/umbrella
  ticket

  tracking a whole multi-child campaign, not a single unit of work with a

  precise file list -- its scope is deliberately broad because its own

  children (each individually precisely scoped) are what actually touch

  files. Acknowledged rather than narrowed per the TICK009 epic-tier

  exemption this drive built.

  '
scope_changes:
- op: remove
  glob: src/frob/tickets/**
  reason: no code touch required to close this epic -- rollup is a Done report + evidence
    binding only; the broad glob collides with T-2360's live lease on src/frob/tickets/_profile.py
  actor: logan
  at: '2026-08-17'
evidence:
- tests/test_tickets_migration.py::TestGoldenFixtureRoundTrip::test_checked_in_fixture_round_trips_to_v2_and_back
- tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_v2_mode_repo_with_a_lingering_monofile_errors
designated_repro_test: null
acceptance:
- text: GIVEN the design doc WHEN reviewed THEN it covers file-per-ticket layout (block
    + done report), draft lifecycle without splice restores, cross-ticket operations
    (renumber with reference rewrite, doable ordering, archive as git mv, flow/velocity
    mining), lock model, merge story with the frob-ledger driver retired, greppability,
    and a reversible migration plan with a compatibility window
  evidence:
  - tests/test_tickets_migration.py::TestGoldenFixtureRoundTrip::test_checked_in_fixture_round_trips_to_v2_and_back
  - tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_v2_mode_repo_with_a_lingering_monofile_errors
- text: GIVEN the migration lands THEN tickets.md/tickets-archive.md are deleted,
    a v2-mode repo with a lingering monofile errors (LEDGERV1001), two agents landing
    disjoint tickets produce no ledger merge conflict, and the TICK002/TICK006 draft-death
    classes are structurally impossible or auto-repaired -- while _land_merge.py/_land_merge_zones.py
    correctly remain as live generic land-closeability/union-zone code, not monofile-splice
    residue (design section 5 corrected accordingly)
  evidence:
  - tests/test_tickets_migration.py::TestLedgerV1DeprecationGate::test_v2_mode_repo_with_a_lingering_monofile_errors
  - tests/test_tickets_migration.py::TestGoldenFixtureRoundTrip::test_checked_in_fixture_round_trips_to_v2_and_back
acceptance_amendments:
- op: replace
  index: 1
  old_text: GIVEN the migration lands THEN the land path performs no monofile splice,
    two agents landing disjoint tickets produce no ledger merge conflict, and the
    TICK002/TICK006 draft-death classes are structurally impossible or auto-repaired
  new_text: GIVEN the migration lands THEN tickets.md/tickets-archive.md are deleted,
    a v2-mode repo with a lingering monofile errors (LEDGERV1001), two agents landing
    disjoint tickets produce no ledger merge conflict, and the TICK002/TICK006 draft-death
    classes are structurally impossible or auto-repaired -- while _land_merge.py/_land_merge_zones.py
    correctly remain as live generic land-closeability/union-zone code, not monofile-splice
    residue (design section 5 corrected accordingly)
  reason: 'Verified against commit e2ed60480f76189b19157b99c6357a8d563068e7 (T-2356
    land):

    tickets.md (-11252 lines) and tickets-archive.md (-203330 lines) are both

    deleted. gates/_tickets_gate.py gained LEDGERV1001 (errors on a lingering

    monofile in a v2-mode repo). The migration is landed and the compatibility

    window is closed.


    The original criterion assumed _land_merge.py/_land_merge_zones.py would be

    deleted as monofile-splice residue -- design section 5''s stale text. The

    landing agent (T-2356) measured zero DEAD001/WIRE001/REF002 hits against

    both files and confirmed by reading the code that T-1189/T-1194/T-1251 had

    already split the real monofile-merge logic out into

    _land_ledger_merge.py/_land_git_ops.py long ago; what remains in

    _land_merge.py is generic closeability validation every land depends on,

    and _land_merge_zones.py''s union zones (frob.toml, gates/__init__.py,

    docs/audits/*.md) were never about tickets.md at all. Deleting either would

    have broken the live land pipeline. Neither was deleted; design section 4/5

    was corrected instead (see the same commit''s docs/design/ledger-v2.md diff).

    Amending the criterion to match the corrected design rather than the

    now-known-stale original text.

    '
  actor: logan
  at: '2026-08-17'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
User directive 2026-07-28: too much manual work rides on tickets.md mechanics. The monofile is the root cause of a documented incident museum: land splice regression (T-0577), archive clobber (T-0959), ledger churn rewrites (T-1036), id collision (T-1090), draft deaths in 10b restores (4 coordinator refiles on 2026-07-28 alone: T-1115, T-1126, T-1127, T-1128), DirtyMain transitions (T-1054), hand splices where the merge driver is unregistered in worktrees, ledger-lock starvation and deadlocks (T-0933, T-0982). Per-ticket files make disjoint tickets disjoint git objects so merge/lease/draft/renumber/archive become ordinary git operations. The global convention (tickets/ tracked in git) already names the directory form. Design doc in docs/design/ first; migration is a separate child with golden round-trip tests; T-1125 (draft-id prose rewrite) stays valuable pre-migration and its engine is reusable for renumber-with-references after.