---
id: T-5512
title: Wire a real frob.gates._seo_gate (SEO family discovery)
state: done
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
flavour: null
due: null
rank: null
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5512
branch: t-5512
scope:
- src/frob/gates/_taint_gate.py
- tests/unit/test_seo_crawl.py
- tests/unit/test_webapp_webperf_markup.py
- tests/fixtures/webapp/webperf1xx/markup/webperf101_positive/next.config.js
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/_seo_gate.py
  reason: 're-scoped per coordinator: widen _taint_gate''s existing discovery prefix
    tuple instead of a new gate module (T-5372 already generalized it to (_websec_,
    _comply_)); one end-to-end control per family in the already-landed SEO/WEBPERF
    test files'
  actor: logan
  at: '2026-09-25'
- op: remove
  glob: src/frob/gates/__init__.py
  reason: 're-scoped per coordinator: widen _taint_gate''s existing discovery prefix
    tuple instead of a new gate module (T-5372 already generalized it to (_websec_,
    _comply_)); one end-to-end control per family in the already-landed SEO/WEBPERF
    test files'
  actor: logan
  at: '2026-09-25'
- op: add
  glob: src/frob/gates/_taint_gate.py
  reason: 're-scoped per coordinator: widen _taint_gate''s existing discovery prefix
    tuple instead of a new gate module (T-5372 already generalized it to (_websec_,
    _comply_)); one end-to-end control per family in the already-landed SEO/WEBPERF
    test files'
  actor: logan
  at: '2026-09-25'
- op: add
  glob: tests/unit/test_seo_crawl.py
  reason: 're-scoped per coordinator: widen _taint_gate''s existing discovery prefix
    tuple instead of a new gate module (T-5372 already generalized it to (_websec_,
    _comply_)); one end-to-end control per family in the already-landed SEO/WEBPERF
    test files'
  actor: logan
  at: '2026-09-25'
- op: add
  glob: tests/unit/test_webapp_webperf_markup.py
  reason: 're-scoped per coordinator: widen _taint_gate''s existing discovery prefix
    tuple instead of a new gate module (T-5372 already generalized it to (_websec_,
    _comply_)); one end-to-end control per family in the already-landed SEO/WEBPERF
    test files'
  actor: logan
  at: '2026-09-25'
- op: add
  glob: tests/fixtures/webapp/webperf1xx/markup/webperf101_positive/next.config.js
  reason: the pre-existing xfail-marked end-to-end control's fixture has no framework
    marker file, so detect_frameworks(root) returns empty and taint_gate's real discovery
    path never calls the hook even once discovery is widened; add the minimal Next.js
    marker the fixture needs to make this genuinely pass, not just remove the xfail
  actor: logan
  at: '2026-09-25'
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-25'
evidence:
- tests/unit/test_seo_crawl.py::test_taint_gate_discovers_seo_crawl_hook
- tests/unit/test_webapp_webperf_markup.py::test_webperf_markup_reachable_via_gate_discovery_end_to_end
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-5374: docs/modules/webapp-seo.md defines no leaf-hook convention, so no live gate calls src/frob/webapp/_seo_tags.py's websec_findings hook (frob.gates._taint_gate only discovers frob.webapp._websec_* modules by name prefix, and _seo_tags does not match it). Mirror frob.gates._a11y_gate's pkgutil-discovery pattern (T-5323) for a new frob.gates._seo_gate over frob.webapp._seo_* modules, and register it in gates/__init__.py (_ALL_GATES, _CANONICAL_GATE_ORDER, _build_process_jobs, _KNOWN_GATE_RULES for SEO101-112). Coordinate with sibling SEO leaves (T-5365 spam, T-5362 crawl) since they hit the same gap.