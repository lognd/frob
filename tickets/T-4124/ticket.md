---
id: T-4124
title: 'audit: other fnmatch-against-path-glob call sites share T-4102/T-4013''s normcase
  platform-dependence bug'
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- src/frob/gates/_doclink_docanchor.py
- src/frob/gates/_fix_engine_text.py
- src/frob/gates/_refs.py
- src/frob/strata/_code_binding.py
- src/frob/strata/_effects.py
- src/frob/tickets/_doable.py
- src/frob/tickets/_land_git_ops.py
- src/frob/tickets/_land_merge_zones.py
- src/frob/tickets/_models.py
- src/frob/tickets/_new_renumber.py
- src/frob/tickets/_scope.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/strata/_selfconform_kinds.py
  reason: collides with T-4110's active lease on this file; auditing this site separately/later
    to avoid blocking on that ticket
  actor: logan
  at: '2026-09-06'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-4102 (frob.excludes.is_excluded -> pathspec gitwildmatch, mirroring T-4013's frob.policy fix). T-4102's WHAT-TO-DO item 1 asked to check whether any OTHER module still calls fnmatch against a path glob, since a third copy is the same normcase-platform-dependence bug waiting (fnmatch.fnmatch/fnmatchcase/filter run operands through os.path.normcase, which folds case and flips / to \\ on Windows, so the same (path, glob) pair can answer differently per platform).

Grep for fnmatch. calls against a path/glob pair (not against an arbitrary string like tickets/_scope.py's narrow-vs-broad scope-glob containment, which may or may not be path-shaped -- worth checking too) found matches in all the files in this ticket's scope:
  - src/frob/gates/__init__.py:543,1443
  - src/frob/gates/_doclink_docanchor.py:127 (has an existing frob:waive WALK001 that assumes fnmatch semantics)
  - src/frob/gates/_fix_engine_text.py:362
  - src/frob/gates/_refs.py:384 (uses fnmatch.fnmatchcase -- no normcase step, may already be platform-safe; audit to confirm)
  - src/frob/strata/_code_binding.py:132
  - src/frob/strata/_effects.py:245-272,370,964 (already does a manual os.path.normcase(glob) workaround per its own comment -- check whether this is now doing the SAME normcase-then-fnmatch dance is_excluded used to, on purpose or as leftover)
  - src/frob/strata/_selfconform_kinds.py:144,381
  - src/frob/tickets/_doable.py:521-524,570,1221 (fnmatch.filter, perf-motivated per its own comments -- T-0453)
  - src/frob/tickets/_land_git_ops.py:1081
  - src/frob/tickets/_land_merge_zones.py:99
  - src/frob/tickets/_models.py:242,499,670 (ticket scope-glob containment; narrow-in-broad checks -- confirm whether these compare real filesystem paths or narrow/broad SCOPE strings, since the platform-dependence bug only matters for real paths)
  - src/frob/tickets/_new_renumber.py:1025 (fnmatch.filter)
  - src/frob/tickets/_scope.py:498,527,545

Each site needs the same audit T-4102 did for frob.excludes: does it compare a real repo-relative path (POSIX-shaped, produced via .as_posix()) against a user-authored glob, and if so does normcase's Windows/case-insensitive folding change the answer versus Linux CI (T-3947/T-3948's real failure mode). NOT all of these are necessarily bugs -- e.g. fnmatchcase never normcases; ticket scope-glob-vs-glob containment (_models.py, _scope.py) may not be a real-filesystem-path comparison at all. This ticket is to do that per-site audit and fix (pathspec gitwildmatch, matching T-4013/T-4102's precedent) or waive each site found to be a genuine platform-dependent path match; the perf-motivated fnmatch.filter sites (_doable.py, _new_renumber.py) may need is_excluded-style caching to keep pathspec fast at that call volume (T-0453 measured 624k calls).