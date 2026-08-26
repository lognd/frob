---
id: T-2998
title: Extend T-2978 live progress to cpp/rust/ts check stages and other multi-minute
  commands
state: queued
kind: ux
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/**
- src/frob/app/check_runner.py
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
T-2978 landed live per-task progress for `frob check`'s PYTHON stage only
(ruff/ty/cycle/dup/arch/bind/exports/gates), reusing the existing T-0419
`Progress` primitive (TTY-only, --json/non-TTY unaffected). Remaining scope
disclosed but not done in that ticket:

1. Wire the same `on_task_done` callback into `run_check_cpp`/
   `run_check_rust`/`run_check_ts` (src/frob/check/_cpp.py or wherever
   those live) -- `_dispatch_check_cpp`/`_dispatch_check_rust`/
   `_dispatch_check_ts` in src/frob/app/check_runner.py already accept a
   `progress` kwarg (T-2978) but do not yet forward it anywhere; a
   polyglot or non-Python repo still only sees the outer per-language
   progress line, not per-task detail within a language's own run.

2. Live progress for the OTHER multi-minute commands the ticket's body
   named with measured timings: `frob verify now`, `frob sys audit`,
   `frob dup`, the branch-classification scan (~5m48s/1092 branches), and
   `frob ticket doable` (92-99s). None of these route through
   `frob.check`'s task dispatcher, so T-2978's `_collect_results`/
   `_run_tasks_concurrently` hook does not reach them -- each needs its
   own hook point into whatever sequential/parallel loop it runs,
   reusing the same `Progress`/`should_color` TTY contract.

Reuse `frob.render.Progress` (`frob.render._renderer.Progress`) for both --
do not invent a second progress mechanism.
