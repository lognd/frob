---
id: T-2856
title: FROB_WORKTREE/FROB_AGENT leak into tests/test_gates.py tmp_path repos causes
  spurious WorktreeLeaseViolation failures
state: queued
kind: bug
origin: human
created: '2026-08-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported third-hand by an agent working T-2843 while running
tests/test_gates.py: FROB_WORKTREE/FROB_AGENT exported in the invoking
shell (true for any dispatched worktree agent per T-0574) leak, unfiltered,
into tests/test_gates.py tests that build a throwaway tmp_path git repo and
call frob code directly (not via a subprocess), tripping the worktree-lease
guard against the WRONG cwd (the tmp_path fixture repo, not the leased
worktree) with a spurious WorktreeLeaseViolation.

VERIFIED directly before filing (not taken on say-so): with
FROB_WORKTREE=<a real worktree path> and FROB_AGENT=1 exported, `uv run
python -m pytest tests/test_gates.py -q` in that worktree fails 12 MORE
tests than the unset baseline (18 vs 6), all Err(WorktreeLeaseViolation)
against the test's own tmp_path repo, e.g.:

  tests/test_gates.py::TestDebtGate::test_rel001_not_land_owned_root_checkout_no_ticket
  tests/test_gates.py::TestDebtGate::test_rel001_land_owned_via_linked_worktree_no_ticket
  tests/test_gates.py::TestDebtGate::test_rel001_land_owned_via_ticket_lease
  tests/test_gates.py::TestFixEngineTierA::test_tick002_renumbers_draft_and_reverifies_clean
  tests/test_gates.py::TestFixEngineTierA::test_tick006_refiles_and_rewrites_citation
  tests/test_gates.py::TestFixEngineTierA::test_tick006_genuinely_nonexistent_id_still_fires_with_merge_target
  tests/test_gates.py::TestFixEngineTierA::test_tick006_ticket_id_scopes_to_landing_ticket_only
  tests/test_gates.py::TestFixEngineTierA::test_tick006_genuinely_lost_draft_still_caught_no_rename_no_duplicate
  tests/test_gates.py::TestFixEngineTierA::test_tick006_two_lands_citing_same_draft_produce_at_most_one_ticket
  tests/test_gates.py::TestCov002ScopeCoverage::test_ambiguous_overlapping_open_scopes_do_not_cover
  tests/test_gates.py::TestCov002ScopeCoverage::test_active_ticket_own_scope_wins_over_a_broader_open_ticket
  tests/test_gates.py::TestCov002ScopeCoverage::test_open_ticket_scope_covers_changed_symbol
  tests/test_gates.py::TestCov002StrataModuleCoverage::test_module_level_ticket_edge_covers_nested_declaration

Captured log line for the first case:
  ERROR frob.tickets._worktree_guard: worktree-guard: agent leased to
  <worktree>; refusing to mutate <tmp_path repo> (cwd resolved to
  <tmp_path repo>) -- cd into the leased worktree, or clear FROB_WORKTREE
  if this is deliberate

Unsetting FROB_WORKTREE/FROB_AGENT before the identical command drops the
failure count back to the 6-item pre-existing baseline (confirmed
independently, unrelated to this: TestWireGate, TestFixEngineTierABatch2,
TestAutofixManifest, TestOptInGates, TestDoc004ConsoleCommandDrift,
TestKnownGateRuleIds).

Likely the SAME underlying class T-2680 already tracks for
tests/test_ticket_land.py's TestSigkillMidStaging (direct
frob.tickets._land.land()/new_ticket() calls, not filtered by the T-0880
fix which only covers tests/system/conftest.py's subprocess helper) --
cross-referencing rather than filing as novel per this queue's documented
duplicate-filing problem. This report shows the same gap reaches at least
one more file (tests/test_gates.py) and at least three more underlying
call paths (release.stamp, the TICK002/TICK006 Tier-A fix engine,
COV002 scope-coverage checks) beyond T-2680's land()/new_ticket() list --
worth noting in whichever ticket ends up owning the actual fix, since the
real fix (whatever it turns out to be -- broadening T-0880's stripping,
or a shared tmp_path-repo pytest fixture that clears the two vars for
every test that builds its own throwaway git repo) needs to cover the
whole call-path class, not just T-2680's two named functions.
