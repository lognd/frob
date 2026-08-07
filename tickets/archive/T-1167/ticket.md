---
id: T-1167
title: 'exports: 15 public symbols across frob/serve/vet never wired into __init__.py
  or demoted private (T-0871 policy residue)'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/__init__.py
- src/frob/serve/__init__.py
- src/frob/vet/__init__.py
- src/frob/doctor.py
- src/frob/gitio.py
- src/frob/serve/_events.py
- src/frob/serve/_leases.py
- src/frob/serve/_socketd.py
- src/frob/serve/_watch.py
- src/frob/vet/_cache.py
- src/frob/vet/_supplychain.py
- src/frob/vet/_taint.py
- design/frob.strata
- tests/unit/test_exports.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: SELFAUDIT001/SYS104 interface= sync for newly-exported symbols
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/unit/test_exports.py
  reason: 'evidence-covers-scope: this test file is the evidence covering the __init__.py
    wiring changes'
  actor: logan
  at: '2026-07-28'
evidence:
- tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols
designated_repro_test: null
threat: null
component: null
---
Found while triaging T-1006 (widespread pre-existing test failures).
tests/unit/test_exports.py::TestFrobExportsPolicyResidue::test_all_nine_packages_report_zero_missing_symbols
fails: 15 public symbols across 3 packages, added by recent landing
waves, were never wired into their package __init__.py (or, if not
meant to be public, never demoted to a leading-underscore private name):

  src/frob:
    frob.doctor.scan_malformed_ticket_edges
    frob.doctor.scan_stale_ticket_leases
    frob.doctor.MalformedTicketEdge
    frob.gitio.excerpt
  src/frob/serve:
    serve._events.subscribe_and_wait
    serve._events.CoverageWatcher
    serve._leases.ResourceLeaseManager
    serve._socketd.daemon_version
    serve._watch.watch_tick
    serve._watch.WatchThread
  src/frob/vet:
    vet._cache.ttl_cache_get
    vet._cache.ttl_cache_set
    vet._supplychain.supply_chain_tree_violations
    vet._taint.taint_findings
    vet._taint.TaintFinding

Per T-0871's own policy (this test's docstring): each one needs a
deliberate per-symbol call -- either a real export (__init__.py import +
__all__ entry) if it is genuinely part of the package's public surface,
or a demotion to private (leading underscore, referrers fixed) if it
was only ever meant as internal plumbing. Not safe to batch-resolve
inside T-1006's own test-triage scope: it touches
src/frob/__init__.py, src/frob/serve/__init__.py, and
src/frob/vet/__init__.py (and possibly renames call sites), none of
which are in T-1006's declared scope, and each symbol needs its own
public-vs-private judgment call.