---
id: T-0137
title: frob test --base main mixes touched non-test source symbols into pytest argv
state: done
kind: bug
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/**
- tests/**
- docs/modules/testing.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_testing.py::TestSelect::test_reversed_directive_never_selects_the_source_symbol
- tests/test_testing.py::TestSelect::test_direct_hit
- tests/test_testing.py::TestSelect::test_class_level_target
- tests/test_testing.py::TestSelect::test_file_and_package_target
- tests/test_testing.py::TestSelect::test_one_hop_ripple
- tests/test_testing.py::TestSelect::test_touched_test_file_self_selects
- tests/test_testing.py::TestSelect::test_unbound_fallback_package
- tests/test_testing.py::TestSelect::test_unbound_fallback_suite
- tests/test_testing.py::TestSelect::test_unbound_fallback_warn
designated_repro_test: null
threat: null
component: null
---
frob test --base main's touched-set selection includes touched non-test SOURCE symbol node-ids (e.g. src/frob/strata/_sysdoc.py::merge_models) directly in the pytest argv alongside real test file paths. Under pytest-xdist this collects 0 items and exits 5 for the whole run, even though the real tests pass in isolation -- a false [FAIL]. Root cause is believed to be in the unbound-fallback path of selection/rendering: touched source symbols without a bound test are passed raw into the pytest invocation instead of being filtered out or mapped to covering tests. See src/frob/testing/_select.py (selection + ripple) and _runners.py ({filters} rendering). Fix: filter to test-file node ids at the render seam, or map source symbols to bound tests. Reproduced independently across multiple sessions (T-0110, T-0085 dispatch notes).