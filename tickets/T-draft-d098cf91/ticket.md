---
id: T-draft-d098cf91
title: 'PERF015-018: N+1 spawn, per-iteration git pathspec, success-only cache write,
  discarded hoisted value -- the rule family the 2026-09-20 audit found missing'
state: queued
kind: feature
origin: human
created: '2026-09-20'
priority: high
blocked_by:
- T-draft-bbd4f5a9
parent: null
tier: story
sprint: v0.533.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/perf/*.py
- docs/design/coding-performance-corpus.md
- docs/modules/gates.md
- frob.toml
scope_breadth_ack: true
scope_breadth_ack_reason: four sibling detectors in one package plus their corpus
  rows and gate docs
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given the pre-fix _flow.py, _unlanded.py and gates/__init__.py, when frob
    check runs, then PERF016 fires on each per-ticket git spawn
  evidence: []
- text: given the pre-fix _rapid_sweep._reproducing_identities_cached, when frob check
    runs, then PERF017 fires naming the success-only cache write
  evidence: []
- text: given the pre-fix _land._sibling_branch_ref chain, when frob check runs, then
    PERF018 fires naming the discarded leases hoist
  evidence: []
- text: given [[perf.heavy]] populated, when frob check runs on dev, then PERF007
    reports at least one finding instead of zero
  evidence: []
threat: null
component: perf
anchor: false
anchor_reason: null
land_commit: null
---
Perf-findings-become-lint-rules directive. Every HIGH in the attached audit (T-draft-bbd4f5a9) was invisible to PERF001-014 for one of three reasons, each becoming a rule. WHY THE GATE MISSED THEM: PERF008 fires only when EVERY argument of a spawn-reaching call in a loop is loop-invariant; all five HIGHs pass a loop-variant ticket id or path, so they are exempt by construction (guard exempts the normal case). PERF007 cross-stage redundancy is advisory and driven by [[perf.heavy]] in frob.toml, which is EMPTY on this repo, so it fires on nothing (catalogued is not enforced). Nothing models cost across invocations: a cache written on the success path only, or a cache that exists but is unreachable from a command entry point. RULES, ship in this order: PERF016 (first, LOW false-positive): a git spawn inside a loop whose argv carries the loop variable as a pathspec or revision; remedy names the batched form (cat-file --batch, one log -- <dir>, grep -l <rev>). PERF017: an effect (spawn/timeout) whose result cache is written on the success branch only; detect a function that calls a *cache_write* helper on one branch of a try/if and returns on the other after a Timeout/None. PERF018: a value hoisted above a loop (assigned from an expensive callee per [[perf.heavy]] or the spawn tables) while a transitive callee inside the loop calls the same expensive callee with no parameter carrying the hoisted value. PERF015 (advisory WARN, HIGH volume: ~106 candidate sites): the negation of PERF008, any loop-variant spawn-reaching call; ship behind a config threshold on estimated iteration source (tickets, files, commits). Also: populate [[perf.heavy]] in frob.toml with read_all_leases, load_queue, parse_file, build_graph, git ls-files so PERF007 actually fires; positive-control test per rule that plants each audit shape and asserts the finding.