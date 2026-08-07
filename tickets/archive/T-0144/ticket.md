---
id: T-0144
title: pytest --collect-only hard-fails repo-wide when strata_core native ext is absent,
  blocking frob ticket evidence for any ticket
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/strata/test_kernel_properties.py
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_testing.py::TestCollectPythonTests::test_parses_node_ids_and_caches_on_content_hash
designated_repro_test: null
threat: null
component: null
---
Found while working T-0141: tests/unit/strata/test_kernel_properties.py does 'import strata_core' at module level with no guard/importorskip. In an environment without the native extension built (uv tool install frob with no natives, matching the T-0133/T-0134 degraded-import precedent used elsewhere in frob.lang), 'uv run pytest --collect-only -q -o addopts=' errors out entirely (Interrupted: 1 error during collection), which frob.testing.collect_python_tests treats as a hard failure. This in turn makes 'frob ticket evidence <id> <node-id>...' fail for EVERY ticket, not just ones touching strata, since it always collects the whole repo first. Fix: guard the strata_core import in that test module (pytest.importorskip or equivalent) so collection degrades gracefully like frob.lang already does, matching the natives-less precedent.