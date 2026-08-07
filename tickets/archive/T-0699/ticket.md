---
id: T-0699
title: 'strata SYS rules: resource-contention detection over the EXISTING grammar
  (duplicate ports, overlapping owns/acl, shared pipes)'
state: done
kind: security
origin: human
created: '2026-07-22'
priority: medium
parent: T-0331
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- tests/unit/strata/
- docs/strata/host.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/strata/host.md
  reason: COV001 requires a real frob:doc anchor for the new SYS2xx public rule-id
    constants/report/entrypoint; host.md already documents the std.host grammar these
    rules read
  actor: logan
  at: '2026-07-22'
evidence:
- tests/unit/strata/test_contention.py::TestDuplicatePort::test_two_nodes_same_port_fires
- tests/unit/strata/test_contention.py::TestDuplicatePort::test_distinct_ports_clean
- tests/unit/strata/test_contention.py::TestDuplicatePort::test_one_sided_waiver_keeps_the_other_nodes_finding
- tests/unit/strata/test_contention.py::TestOverlappingPath::test_owns_subtree_overlap_fires_write_capable
- tests/unit/strata/test_contention.py::TestOverlappingPath::test_disjoint_paths_clean
- tests/unit/strata/test_contention.py::TestOverlappingPath::test_readonly_acl_overlap_fires_but_not_write_capable
- tests/unit/strata/test_contention.py::TestSharedPipe::test_same_pipe_name_fires
- tests/unit/strata/test_contention.py::TestSharedPipe::test_distinct_pipe_names_clean
- tests/unit/strata/test_contention.py::TestSharedStoreWrite::test_two_writers_fires_mode_blind
- tests/unit/strata/test_contention.py::TestSharedStoreWrite::test_single_writer_clean
- tests/unit/strata/test_contention.py::TestSharedStoreWrite::test_empty_store_ids_is_silent
designated_repro_test: null
acceptance:
- text: GIVEN two nodes listening on the same port WHEN sys checks run THEN a contention
    error names both nodes; GIVEN overlapping owns paths THEN a finding fires; GIVEN
    disjoint resources THEN silence
  evidence: []
threat: null
component: null
---
First half of the resource-contention mandate 2026-07-22 -- NO grammar change needed. New SYS rule family over the already-elaborated model: (a) two nodes declaring listens on the same port = hard conflict; (b) two nodes whose owns paths (linux) or acl paths (windows) overlap by prefix = contention finding (severity by whether either grants write-capable rights where expressible); (c) two nodes binding the same pipe NAME; (d) two nodes writing the same store. Litmus fixtures per case, both firing and clean. Coordinate rule naming with the T-0331 reliability/consistency children (T-0649 single-source-of-truth is the data-level cousin); the MODE-aware deeper version is the sibling grammar-extension ticket and must not be duplicated here -- this ticket ships what current grammar data supports, honestly labeled as mode-blind.