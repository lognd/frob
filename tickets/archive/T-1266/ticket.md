---
id: T-1266
title: extend real ctest collector to retire c/cpp frob:tests structural fallback
  (T-1193 successor)
state: done
kind: security
origin: agent
created: '2026-07-29'
priority: medium
parent: T-1193
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/testing/_collect.py
- tests/test_gates.py
- docs/design/registry/check-coverage.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: retire CHK-SUBSYS-GATES-ACCOUNTING's C/C++ clause now that the real ctest
    collector plus TEST013 disclosure are proven at gate level
  actor: logan
  at: '2026-08-01'
evidence:
- tests/test_gates.py::TestNativeTestCollectors::test_cpp_directive_resolves_via_real_ctest_node_id
- tests/test_gates.py::TestTest013NativeUnverified::test_fires_on_structural_only_edge
designated_repro_test: null
acceptance:
- text: GIVEN a CMake C/C++ project with CMAKE_EXPORT_COMPILE_COMMANDS enabled and
    an unambiguous single-source build target, and a frob:tests directive naming a
    real ctest case WHEN gates run THEN the edge resolves against a real collect_cpp_tests
    node id (not the name/path structural fallback) the same way a TS frob:tests edge
    now resolves against a real vitest node id.
  evidence:
  - tests/test_gates.py::TestNativeTestCollectors::test_cpp_directive_resolves_via_real_ctest_node_id
- text: GIVEN a C/C++ frob:tests edge that still cannot resolve against a real collected
    node id (no configured build dir, or an ambiguous multi-source match) WHEN gates
    run THEN TEST013's disclosed-unverified signal fires for that edge (per T-0552's
    existing mechanism) rather than the edge silently satisfying TEST001-004 with
    no execution evidence at all.
  evidence:
  - tests/test_gates.py::TestTest013NativeUnverified::test_fires_on_structural_only_edge
threat: null
component: null
---
Successor row from T-1193 (CHK-SUBSYS-GATES-ACCOUNTING, docs/design/registry/check-coverage.yaml).

Verified real (2026-07-29): src/frob/gates/__init__.py's _NATIVE_TEST_EXTENSIONS
still lists .c/.h/.cpp/.hpp/.cc/.hh (the C/C++ side of the audit finding
B3/E3). T-0730 (already landed, tickets-archive.md) wired the real vitest
collector into _load_tests and retired the TS structural fallback (.ts/.tsx
removed from that set), but explicitly left C/C++ on the pre-existing
name/path structural fallback (_is_native_test_symref plus snapshot
resolution) rather than the real collect_cpp_tests collector T-0587 built
-- per _NATIVE_TEST_EXTENSIONS' own comment, most C/C++ edges have no
configured build directory (CMAKE_EXPORT_COMPILE_COMMANDS) or an ambiguous
multi-source match at gate-check time, so retiring the fallback outright
today would silently drop ALL TEST001-004 credit for C/C++ frob:tests
edges rather than tighten it. Net effect: a C/C++ frob:tests edge whose
target merely LOOKS like test code by name/path still gets full
TEST001-004 execution credit even though ctest never actually ran it --
an empty void test_foo(){} still satisfies TEST001-004 for C/C++ today,
same class of false assurance the audit originally flagged, now narrowed
from ts+c+cpp down to c+cpp only.

Right-way fix direction: extend real ctest-collector coverage
(collect_cpp_tests, src/frob/testing/_collect.py) to the common single-
target/single-build-dir case so most C/C++ edges resolve against real
collected node ids the same way TS now does, and only fall back to the
disclosed-unverified structural credit (already surfaced via TEST013's
_test013_native_unverified per T-0552) for the genuinely ambiguous
multi-source/no-build-dir case -- never a silent full-credit pass for
those. Do not simply delete the fallback without a collector upgrade: per
T-0552's own Done report, that would regress real existing C/C++
TEST001-004 coverage to zero rather than to a disclosed-degraded state.