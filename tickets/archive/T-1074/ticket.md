---
id: T-1074
title: 'arch: triage 800-2000 line file residue (T-0395 remainder tier 3)'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/
- tests/test_testing.py
- docs/modules/testing.md
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_testing.py
  reason: 'T-1074''s real split of frob.testing._collect into _collect_rust/_collect_ts/_collect_cpp
    moved shutil.which() call sites out of _collect.py; tests/test_testing.py monkeypatches
    collect_mod.shutil by module attribute and must be repointed at the new modules
    to keep passing, per the T-1171 split precedent (repoint tests that monkeypatch
    a moved function via the package attribute).

    '
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/modules/testing.md
  reason: 'T-1074''s real split of frob.testing._collect into _collect_rust/_collect_ts/_collect_cpp
    moved shutil.which() call sites out of _collect.py; tests/test_testing.py monkeypatches
    collect_mod.shutil by module attribute and must be repointed at the new modules
    to keep passing, per the T-1171 split precedent (repoint tests that monkeypatch
    a moved function via the package attribute).

    '
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/test_gates.py
  reason: 'tests/test_gates.py::TestCppSourceAccurateCollection._mock_ctest monkeypatches
    collect_mod.shutil by module attribute; must be repointed at frob.testing._collect_cpp
    after the T-1074 split moved the cpp collector out of _collect.py.

    '
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_testing.py::TestCollectRustTests::test_collect_rust_tests_parses_and_caches
- tests/test_testing.py::TestCollectTsTests::test_collect_ts_tests_parses_and_caches
- tests/test_testing.py::TestCollectCppTests::test_collect_cpp_tests_parses_and_caches
designated_repro_test: null
threat: null
component: null
---
Filed from T-0395 (failed as too large for one pass). Remaining in-scope
large-file residue under 2000 lines (frob-core/src/lib.rs 2277 --
excluded, native crate, separate toolchain/ownership from the python
gates split above; list the rest as of 2026-07-28):
src/frob/tickets/_models.py (1658), src/frob/arch/_patterns.py (1486),
src/frob/app/check_runner.py (1468), src/frob/gates/_docblocks.py (1460),
src/frob/arch/_python.py (1267), src/frob/testing/_collect.py (1267),
src/frob/gates/_protocol_summary.py (1244), src/frob/tickets/_leases.py
(1191), src/frob/app/config.py (1118), src/frob/gates/_secrets.py (1108),
src/frob/graph/dsl.py (1033), src/frob/gates/_docptr.py (1000),
src/frob/gates/_registry_exhaustiveness.py (993), src/frob/check/__init__.py
(958), src/frob/check/_python.py (936), src/frob/graph/__init__.py (869),
strata-core/src/lib.rs (869, native crate -- confirm with the strata
sibling ticket owner before touching), src/frob/app/sys_runner.py (851),
src/frob/perf/_rules.py (845), src/frob/arch/_rust.py (838),
src/frob/graph/callgraph.py (830), src/frob/perf/_effect_summaries.py
(823), src/frob/gates/_refs.py (818). Triage into real splits vs.
files that genuinely do not decompose cleanly (record the specific
reason per file, per this ticket's acceptance framing) -- do not attempt
all ~20 in one diff; group by subsystem and land incrementally, full
suite verification per group.