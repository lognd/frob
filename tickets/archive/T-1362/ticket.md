---
id: T-1362
title: Fix ty no-matching-overload regression in test_makefile_coverage.py (T-1335
  follow-up)
state: done
kind: bug
origin: human
created: '2026-07-31'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/test_makefile_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_makefile_coverage.py::TestCoverageXmlIgnoreErrors::test_combine_then_xml_survives_a_stale_fixture_path
designated_repro_test: null
threat: null
component: null
---
T-1335's own new regression test (tests/unit/test_makefile_coverage.py)
introduced 2 new `ty` no-matching-overload errors: it builds a plain
dict of subprocess.run kwargs and unpacks it with **run_kwargs across two
call sites, which ty's overload resolution cannot match against
subprocess.run's typeshed overloads (an untyped dict loses the literal
`text=True`/`check=True` types the overloads key on). Found immediately
after T-1335 landed, while verifying T-1351's --ticket lint stage
(`frob check --ticket T-1351 --only lint`) showed 3 ty diagnostics where
the prior full run showed only 1 (src/frob/gates/_debt_deprecated.py,
pre-existing, unrelated).

Fix: pass the subprocess.run kwargs directly at each call site instead of
via a dict-unpack, so ty can resolve the real overload from literal
keyword arguments.