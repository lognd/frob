---
id: T-2585
title: 'frob check has no durable result: replay an unchanged-tree verdict automatically,
  never as a flag'
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
scope:
- src/frob/check/_python.py
- src/frob/gates/_gate_cache.py
- docs/modules/serve.md
- tests/test_gate_cache.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/serve.md
  reason: 'scope closure: gate_cache frob:doc targets live here'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_gate_cache.py
  reason: T-2585 adds TestRunReplay coverage to this file
  actor: logan
  at: '2026-08-19'
evidence:
- tests/test_gate_cache.py::TestRunReplay::test_unchanged_tree_replays
- tests/test_gate_cache.py::TestRunReplay::test_tracked_edit_forces_real_run
- tests/test_gate_cache.py::TestRunReplay::test_budget_clipped_prior_run_never_replays_as_complete
- tests/test_gate_cache.py::TestRunReplay::test_ticket_scoped_prior_does_not_serve_unscoped
designated_repro_test: tests/test_gate_cache.py::TestRunReplay::test_budget_clipped_prior_run_never_replays_as_complete
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 65f21e9cf47ab0f7aab70e3c5fc70693f250c442
---
## Problem

`frob check` writes NO durable result artifact. Grepped `src/frob/check/
_python.py`: no result file is written anywhere. The verdict exists only as
stdout. So when an agent bounds the output -- `frob check > log; tail log`,
or pipes to `head` -- and the interesting part scrolls past, the ONLY
recovery is recomputation, at up to 274s.

## Why the obvious fix (a `--last` flag) is REJECTED

Repo owner raised the decisive objection: a `frob check --last` that
reprints a saved result forces the AGENT to decide whether that result is
still valid, i.e. to compare tree hashes by hand. That is a new obligation
on every caller, it will be gotten wrong, and a hand-compared stale green is
worse than no cache at all. It also contradicts the standing preference for
automatic behavior over commands -- a command requires knowing the command.

## Required shape: automatic, no flag, no caller obligation

`frob check` itself decides. On invocation it computes the tree fingerprint
(`root_content_key`, `src/frob/gates/_gate_cache.py:648` -- already exists,
already one `git ls-files -s` subprocess) and if it matches a persisted
COMPLETE prior result, it reprints that result immediately and says so,
including the fingerprint's age. Otherwise it runs for real. The agent
compares nothing and needs to know nothing new; the identical command is
just fast when nothing changed.

Persistence is the MECHANISM, not the interface. Do not surface the artifact
path as the way to use this.

## The correctness guard that matters most

A prior run that was BUDGET-CLIPPED, gate-filtered (`--ticket`, `--only`),
or otherwise partial MUST NOT be replayed as a full verdict. Record with
each stored result exactly which gates ran and whether a budget truncated
the run; serve it only to an invocation requesting the same-or-smaller gate
set, and label it as partial when it was.

This is the whole risk of the ticket. A measured prior instance: `frob check
--budget 480` ran 15 of 52 gates and reported 3 errors, which reads
identically to a clean full run. Making replay cheap makes a false green
MORE convincing, not less. A cached partial served as complete would be the
worst version of this repo's dominant bug class.

## What already exists -- do not duplicate

Caching is NOT missing. Two layers are live and enabled by default
(`src/frob/check/_python.py:867`, `use_cache=_gate_cache_enabled(no_cache)`):
- T-0602 `evaluate_cacheable_gate`: per-gate, keyed on touched-files digest
  + membership key + scalar `extra` key. 8 thread gates.
- T-1445 `_split_process_cache`: whole-tree `root_content_key`. 18 process
  gates (`_CACHEABLE_PROCESS_GATES`).

This ticket adds a WHOLE-RUN replay above those, for the case where nothing
changed at all. Reuse `root_content_key` and the existing store; do not
invent a second fingerprint.

## Positive controls, both directions

- unchanged tree: second invocation replays, is dramatically faster, and
  prints the SAME findings as the first
- any tracked file edited: does NOT replay, runs for real
- prior run budget-clipped: does NOT replay as complete -- must either
  re-run or print clearly as partial. Without this case the feature is
  indistinguishable from a stale-green generator
- prior run was `--ticket`-scoped, new invocation unscoped: does NOT replay