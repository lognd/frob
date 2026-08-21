---
id: T-2234
title: Map the tickets/app/serve/verify/testing/strata/gates/... mega-cluster (180+
  files) into sub-SCCs before any mechanical fix leaf can be scoped
state: done
kind: docs
origin: human
created: '2026-08-16'
priority: medium
parent: T-2202
tier: story
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/investigations/T-2202-mega-cluster.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- cmd:bash -c "wc -l docs/investigations/T-2202-mega-cluster.md && grep -n 'does not
  decompose' docs/investigations/T-2202-mega-cluster.md && grep -n 'Answer:' docs/investigations/T-2202-mega-cluster.md"
  exit=0 sha256=3ce4bc59a52b
designated_repro_test: null
acceptance:
- text: 'Given current main, when ''uv run frob check --only cycle'' runs, then the
    single ERROR-severity cycle spanning src/frob/tickets, src/frob/app, src/frob/serve,
    src/frob/verify, src/frob/testing, src/frob/strata, src/frob/gates, src/frob/perf,
    src/frob/refactor, src/frob/policy, src/frob/natives, src/frob/registry, src/frob/release,
    src/frob/check, src/frob/graph, and src/frob/__main__.py/doctor.py/__init__.py
    (approx. 180 files, approx. 15 packages) is too large to scope as a single leaf
    without re-creating T-2202''s original mega-glob problem. This ticket''s own deliverable
    is docs/investigations/T-2202-mega-cluster.md: a written breakdown of the strongly-connected
    sub-groups inside this one reported SCC (the frob-cycle tool reports one merged
    SCC when several tighter sub-cycles are chained through a small number of hub
    files), naming the specific hub file(s) whose removal/seam would split it, so
    that follow-on leaf tickets (each narrow-scoped like T-2231/T-2232/T-2233) can
    be filed against the sub-groups. Acceptance for THIS ticket is the doc existing
    with that breakdown, not a code fix -- do not touch src/ under this ticket.'
  evidence:
  - cmd:bash -c "wc -l docs/investigations/T-2202-mega-cluster.md && grep -n 'does
    not decompose' docs/investigations/T-2202-mega-cluster.md && grep -n 'Answer:'
    docs/investigations/T-2202-mega-cluster.md" exit=0 sha256=3ce4bc59a52b
- text: 'OPEN QUESTION for the design doc to answer: this cluster did not exist in
    T-2202''s original filing (which described a tickets/-only, 4-file cluster: _accept.py,
    _setters.py, _land_finalize.py, _land_verify.py). It has grown to ~180 files across
    ~15 packages since, tracking with T-2211/T-2219 (landed after T-2202 was filed)
    fixing resolve_local_import''s handling of ''from X import submodule'' and transitive
    re-export chains. Confirm in the doc whether this reflects newly-accurate detection
    of real, pre-existing debt (the T-2202 framing) or whether the growth rate itself
    is a signal worth its own finding -- do not assume without checking a sample of
    the newly-included edges.'
  evidence:
  - cmd:bash -c "wc -l docs/investigations/T-2202-mega-cluster.md && grep -n 'does
    not decompose' docs/investigations/T-2202-mega-cluster.md && grep -n 'Answer:'
    docs/investigations/T-2202-mega-cluster.md" exit=0 sha256=3ce4bc59a52b
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Spawned while decomposing T-2202 (epic) into leaf tickets, 2026-08-16. Direct measurement of 'uv run frob check --only cycle' on today's main shows this cluster has grown from T-2202's originally recorded 4-file tickets/-only cluster to a single reported SCC spanning src/frob/tickets, app, serve, verify, testing, strata, gates, perf, refactor, policy, natives, registry, release, check, graph, plus __main__.py/doctor.py/__init__.py -- effectively most of src/frob outside dup/, lang/, vet/, gates' docblocks pair, and arch/deploy. A leaf scoped to this cluster's actual files would be exactly the mega-glob T-2202 itself was blocked for; it cannot be dispatched as a mechanical fix leaf until it is broken into sub-SCCs. NOT a code ticket -- see its own acceptance.