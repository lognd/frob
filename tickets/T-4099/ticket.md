---
id: T-4099
title: 'F-226 follow-up: apply pathspec gitwildmatch fix to remaining 6 fnmatch call
  sites (excludes, gates, refs, close_cmd, query)'
state: queued
kind: security
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
- src/frob/excludes.py
- src/frob/gates/__init__.py
- src/frob/gates/_refs.py
- src/frob/gates/_doclink_docanchor.py
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/app/ticket_runner/_query.py
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
T-4013 fixed src/frob/policy/__init__.py's user-authored glob matching (fnmatch -> pathspec gitwildmatch): fnmatch has no zero-or-more-directories ** (app/**/*.py silently misses files directly under app/) and is platform-dependent via os.path.normcase (same pattern matches differently on Windows vs Linux). T-4013's Done report classified all 8 repo fnmatch call sites named in its ticket body; the following 6 files/7 call sites are ALSO user-authored-glob call sites carrying the identical trap and were left unfixed (out of T-4013's declared scope, filed here per NO-DUPLICATION/scope discipline):

1. src/frob/excludes.py:83 is_excluded() -- [graph].exclude globs from frob.toml, user-authored. AFFECTED.
2. src/frob/gates/__init__.py:543 _glob_prefix_match() -- [[system]].paths glob, user-authored. AFFECTED.
3. src/frob/gates/__init__.py:1443 _scope_glob_specificity() -- ticket scope globs (via _scope_globs), user-authored; connects directly to T-3978 (a scope glob matching zero tracked files is accepted silently) -- an under-matching ** is one way to produce a zero-match scope. AFFECTED.
4. src/frob/gates/_refs.py:384 _allowlist_covers() -- [[refs.entrypoint]] allowlist globs, user-authored (uses fnmatchcase, so also platform-independent already via case-sensitivity, but still lacks ** semantics). AFFECTED.
5. src/frob/gates/_doclink_docanchor.py:127 -- docs include/exclude globs, user-authored; already carries a waiver comment (WALK001, unrelated rule) that itself documents the exact fnmatch ** gap this ticket would fix. AFFECTED.
6. src/frob/app/ticket_runner/_close_cmd.py:402 _matching_gate_claim_files() -- ticket close evidence criterion glob, user-authored. AFFECTED.
7. src/frob/app/ticket_runner/_query.py:1255 -- ticket scope globs (same _scope_globs expansion as #3), user-authored. AFFECTED.

NOT classified as affected (do not touch under this ticket -- see T-4013's Done report for the full reasoning): src/frob/gates/_fix_engine_text.py:362 mirrors ruff's own per-file-ignores glob dialect specifically (matching what ruff itself would do), not a general policy glob -- switching it to gitwildmatch could DIVERGE from ruff's actual matching behavior rather than fix a bug, so it needs its own investigation into ruff's dialect, not this fix.

Widening caution (same as T-4013): switching a glob-matching call site's semantics WIDENS what existing patterns match. Measure the before/after finding-count delta for each site before landing and report it -- do not suppress new findings to keep a change small.