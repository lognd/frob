---
id: T-2056
title: _vet_examined_sites' docstring wrongly claims OPAQUE001 uses scan_file_capabilities
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_coverage_sites.py
evidence_scope:
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-2011 (wiring perf/strata/graph/vet examined-sites
into WAIVE004): `_vet_examined_sites`' own docstring
(src/frob/gates/_coverage_sites.py) claims it is "the OPAQUE001/CVE-
fingerprint gates' own per-file capability scanner" (scan_file_
capabilities). This is factually wrong -- `opaque_gate`
(src/frob/gates/_opaque.py:110) does not call `scan_file_capabilities` at
all; it calls `_opaque_indirection_findings`, a scanner its own module
docstring says is DELIBERATELY DISJOINT from the scan_file_capabilities
universe (two separate universes per
docs/design/capability-evasion-taxonomy.md: statically-resolvable name
bindings vs. runtime-opaque constructs).

`scan_file_capabilities` is actually consumed by:
- `frob.strata._selfconform` (folded into SELFAUDIT001) -- but every
  SELFAUDIT001 Violation.file is the constant `design_dir` string
  (src/frob/gates/_sys_selfaudit.py:64), never a per-file site, so even
  this usage's site identity does not match what `_vet_examined_sites`
  tracks.
- `frob.vet._capability_scan.py`'s `_aggregate_capabilities` -- but this
  scans a THIRD-PARTY dependency's extracted source tree (`source_dir`,
  a downloaded package being vetted), never this repo's own `root` --
  `_vet_examined_sites(root)` walks this repo's own tracked files, an
  entirely different file-identity space.

No live rule's violation site corresponds to what `_vet_examined_sites`
tracks today. This does not block anything currently (T-2011 investigated
and left the "vet" family deliberately unwired from WAIVE004 for exactly
this reason), but the docstring's own claim is misleading to a future
reader who might otherwise trust it and wire a consumer on the strength
of the docstring alone -- exactly the "family name/docstring claim
implies coverage, but the code doesn't back it" mistake T-2011's own
investigation was trying to avoid.

Suggested fix: correct `_vet_examined_sites`' docstring to either (a)
honestly describe what it actually measures without claiming an OPAQUE001
tie, or (b) if a real per-repo vet consumer is wanted, build one from
whatever OPAQUE001's `_opaque_indirection_findings` candidate set actually
is (`supported_extensions()`-filtered `_shared_tracked_files`), which is
NOT what this reporter currently computes.

frob:no-behavior-change reason="took suggested fix (a): the docstring on _vet_examined_sites is corrected to drop the false OPAQUE001/CVE-fingerprint claim and add an explicit note naming the real consumers of scan_file_capabilities, with no change to the function's logic or return value. The designated evidence (the CLI-dispatch integration test) correctly PASSES at both parent and fix, since nothing observable changed."