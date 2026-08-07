---
id: T-0582
title: 'perf audit re-measurement: verify vet/secrets/selfconform after T-0410 parse_file
  memo fix; profile refs stage (now 2nd dominator)'
state: done
kind: bug
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/
- docs/audits/perf.md
- tests/test_lang.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/audits/perf.md
  reason: ticket body explicitly requires a dated re-measurement section in docs/audits/perf.md
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_lang.py
  reason: 'covers_scope route 2: the T-0414 parse-cache anti-regression test is this
    measurement ticket''s evidence proving the H4 resolution mechanism; the deliverable
    itself is the audit-doc re-measurement'
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_lang.py::TestParseCache::test_cross_entry_point_reuse_is_one_parse_per_file
designated_repro_test: null
threat: null
component: null
---
T-0410 landed one concrete fix: memoize parse_file's extract() walk (coverage_gate 155.8s->15.9s isolated, ~40s->~4s in real frob check) plus M6 (.hypothesis/.serena skip-dirs). Two things from docs/audits/perf.md need re-measurement, not assumption: (1) H4's other cited multipliers (vet.scan_file_capabilities uses raw_tree not parse_file, so bypasses the new memo -- but _parse's own content-hash cache may already make repeats cheap; verify with a profile) and H5 (selfconform's double capability-scan, likely still unfixed). (2) refs_gate is now the 2nd-largest stage (measured ~8-11s across several frob check runs) and was never profiled by the original audit; isolate and profile it the way this ticket isolated coverage_gate. Update docs/audits/perf.md with a dated re-measurement section (mark H1/H2 RESOLVED via T-0423) rather than a fresh audit.