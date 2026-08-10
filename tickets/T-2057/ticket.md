---
id: T-2057
title: Wire strata/graph/vet examined-sites into WAIVE004 (blocked pending a sound
  site-identity mapping)
state: queued
kind: feature
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_coverage_sites.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Successor to T-2011 (Wire perf/strata/graph/vet examined-sites reporters
into a real WAIVE004 consumer). T-2011 investigated all four families by
reading the actual rule-to-violation-site code path and only wired perf
(PERF001-008/010-014, excluding PERF009) -- see T-2011's own Done report
for the full investigation.

strata, graph, and vet are LEFT DELIBERATELY UNWIRED because no rule in
each family's own violation set has a `Violation.file` that corresponds
to what that family's examined-sites reporter
(`frob.gates._coverage_sites._strata_examined_sites`/
`_graph_examined_sites`/`_vet_examined_sites`) actually tracks:

- strata: SYS001/SYS003 report a CODE site (the directive/import), SYS002
  constructs a synthetic `design/<kind>/<id>` string, SELFAUDIT001 always
  reports the constant `design_dir` -- none is a real `.strata` file path
  from the examined set. SYS004 IS a real `.strata` path, but only fires
  on a load FAILURE, which by construction can never be a member of the
  successfully-parsed examined set.
- graph: `build_graph`'s `GraphSnapshot` backs dozens of unrelated gate
  families with heterogeneous violation-site shapes; there is no single
  owning rule family the way `arch_gate`/`perf_gate` own theirs.
- vet: `_vet_examined_sites`' own docstring wrongly claims OPAQUE001 as
  its consumer (T-2056 tracks correcting that inaccuracy
  separately) -- `opaque_gate` does not call `scan_file_capabilities` at
  all. The real callers of `scan_file_capabilities`
  (`frob.strata._selfconform` for SELFAUDIT001, `frob.vet._capability_
  scan.py` for third-party dependency package scans) either share
  SELFAUDIT001's `design_dir`-constant site problem or operate on a
  completely different file-identity space (an external dependency's
  source tree, not this repo's own `root`).

This ticket exists so the open `follow_up="T-2011"` WIRE001 waivers on
the strata/graph/vet reporters in `src/frob/gates/_coverage_sites.py`
have a live tracker to re-point to now that T-2011 is closing, and so a
future session doesn't have to re-derive this investigation's negative
findings from scratch. Not actionable as "wire it" -- the honest next
step, if one ever exists, is either (a) a real per-file rule emerges in
one of these families whose site matches its reporter's candidate set,
or (b) a reporter is rebuilt to track the actual site space its family's
real rule already uses (e.g. a vet reporter over
`_opaque_indirection_findings`' own candidate set, matching what
OPAQUE001 truly consumes, instead of `scan_file_capabilities`'s).
