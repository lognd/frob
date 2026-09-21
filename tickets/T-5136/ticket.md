---
id: T-5136
title: 'PERF015-018: N+1 spawn, per-iteration git pathspec, success-only cache write,
  discarded hoisted value -- the rule family the 2026-09-20 audit found missing'
state: in-progress
kind: feature
origin: human
created: '2026-09-20'
priority: high
blocked_by:
- T-5135
parent: null
tier: story
sprint: v0.533.0
runs_last: false
milestone: 1.0.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/perf/*.py
- docs/design/coding-performance-corpus.md
scope_breadth_ack: true
scope_breadth_ack_reason: four sibling detectors in one package plus their corpus
  rows and gate docs
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: docs/modules/gates.md
  reason: docs/modules/gates.md locked by live T-5121 lease; add PERF015-018 rows
    in a follow-up once T-5121 releases it
  actor: logan
  at: '2026-09-21'
- op: remove
  glob: frob.toml
  reason: frob.toml locked by live T-5138 lease; add PERF015-018 severities in a follow-up
    once T-5138 releases it
  actor: logan
  at: '2026-09-21'
triage_changes:
- field: milestone
  old_value: null
  new_value: 1.0.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-20'
evidence:
- tests/unit/perf/test_loop_variant.py::TestPerf016::test_git_spawn_with_loop_variable_pathspec_is_flagged
- tests/unit/perf/test_loop_variant.py::TestPerf016::test_loop_invariant_spawn_is_not_flagged_by_perf016
- tests/unit/perf/test_loop_variant.py::TestPerf015::test_loop_variant_ticket_id_spawn_is_flagged_advisory
- tests/unit/perf/test_loop_variant.py::TestPerf015::test_loop_variant_call_without_iteration_source_name_is_not_flagged
- tests/unit/perf/test_cache_effects.py::TestPerf017::test_success_only_cache_write_is_flagged
- tests/unit/perf/test_cache_effects.py::TestPerf017::test_both_branches_writing_cache_is_not_flagged
- tests/unit/perf/test_cache_effects.py::TestPerf018::test_hoisted_value_recomputed_in_loop_is_flagged
- tests/unit/perf/test_cache_effects.py::TestPerf018::test_hoisted_value_threaded_through_is_not_flagged
designated_repro_test: null
acceptance:
- text: given the pre-fix _flow.py, _unlanded.py and gates/__init__.py, when frob
    check runs, then PERF016 fires on each per-ticket git spawn
  evidence:
  - tests/unit/perf/test_loop_variant.py::TestPerf016::test_git_spawn_with_loop_variable_pathspec_is_flagged
- text: given the pre-fix _rapid_sweep._reproducing_identities_cached, when frob check
    runs, then PERF017 fires naming the success-only cache write
  evidence:
  - tests/unit/perf/test_cache_effects.py::TestPerf017::test_success_only_cache_write_is_flagged
- text: given the pre-fix _land._sibling_branch_ref chain, when frob check runs, then
    PERF018 fires naming the discarded leases hoist
  evidence:
  - tests/unit/perf/test_cache_effects.py::TestPerf018::test_hoisted_value_recomputed_in_loop_is_flagged
acceptance_amendments:
- op: remove
  index: 4
  old_text: given [[perf.heavy]] populated, when frob check runs on dev, then PERF007
    reports at least one finding instead of zero
  new_text: null
  reason: criterion 4 (PERF007 fires once [[perf.heavy]] is populated) requires editing
    frob.toml, which carried a live cross-worktree lease (T-5138) when T-5136 started
    and was removed from scope; filed as T-draft-a4b2ce94
  actor: logan
  at: '2026-09-21'
threat: null
component: perf
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5136
branch: t-5136
---
Perf-findings-become-lint-rules directive. Every HIGH in the attached audit (T-5135) was invisible to PERF001-014 for one of three reasons, each becoming a rule. WHY THE GATE MISSED THEM: PERF008 fires only when EVERY argument of a spawn-reaching call in a loop is loop-invariant; all five HIGHs pass a loop-variant ticket id or path, so they are exempt by construction (guard exempts the normal case). PERF007 cross-stage redundancy is advisory and driven by [[perf.heavy]] in frob.toml, which is EMPTY on this repo, so it fires on nothing (catalogued is not enforced). Nothing models cost across invocations: a cache written on the success path only, or a cache that exists but is unreachable from a command entry point. RULES, ship in this order: PERF016 (first, LOW false-positive): a git spawn inside a loop whose argv carries the loop variable as a pathspec or revision; remedy names the batched form (cat-file --batch, one log -- <dir>, grep -l <rev>). PERF017: an effect (spawn/timeout) whose result cache is written on the success branch only; detect a function that calls a *cache_write* helper on one branch of a try/if and returns on the other after a Timeout/None. PERF018: a value hoisted above a loop (assigned from an expensive callee per [[perf.heavy]] or the spawn tables) while a transitive callee inside the loop calls the same expensive callee with no parameter carrying the hoisted value. PERF015 (advisory WARN, HIGH volume: ~106 candidate sites): the negation of PERF008, any loop-variant spawn-reaching call; ship behind a config threshold on estimated iteration source (tickets, files, commits). Also: populate [[perf.heavy]] in frob.toml with read_all_leases, load_queue, parse_file, build_graph, git ls-files so PERF007 actually fires; positive-control test per rule that plants each audit shape and asserts the finding.