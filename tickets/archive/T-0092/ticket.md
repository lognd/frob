---
id: T-0092
title: 'rust test integration: [[test.runner]] for cargo + COV003 evidence resolution'
state: done
kind: feature
origin: agent
created: '2026-07-17'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- frob.toml
- src/frob/testing/**
- src/frob/gates/**
- tests/**
- docs/modules/testing.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestCoverageGate::test_cov003_passes_for_rust_evidence_id
designated_repro_test: null
threat: null
component: null
---
Two symptoms, one gap, both hit on 2026-07-17: (1) frob test --base main errors NoRunner when rust files are touched because frob.toml has no [[test.runner]] language=rust entry (cargo needs PYO3_PYTHON + LD_LIBRARY_PATH env to link); (2) COV003 rejects cargo test ids as ticket evidence because only python tests are collected (T-0062 closed with rust ids and broke repo check until swapped for pytest ids). Wire a cargo runner + rust test collection so native-kernel work can cite its real tests.
## Done report

Cargo [[test.runner]] for strata-core with {filters} converted to bare
module paths (_to_rust_filter); _cargo_env probes PYO3_PYTHON/python3.x
plus sysconfig LIBDIR and returns Err(CargoEnvUnavailable) BEFORE
spawning, so an unbuildable environment fails loudly on both the runner
and collection paths (no vacuous pass -- reviewer-verified with tests).
collect_rust_tests walks crates, parses cargo test --list, maps module
paths back to path::qualname symrefs, cached on rust content hash;
gates._load_tests merges python+rust collections with independent
degrade. .rs removed from the structural-evidence fallback: rust now
has execution evidence, superseding T-0090 for rust only (ts/c/cpp
unchanged). Real end-to-end proof: cargo test run + 93 collected ids
incl. the exact id existing directives cite. frob-core runner coverage
filed as T-0128. Reviewer APPROVED; verified at merge on main: 119
tests across testing+gates suites.