---
id: T-0311
title: TEST005 reports wrong file path when make coverage uses multiple --cov roots
state: done
kind: bug
origin: auditor
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_coverage.py
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestCoverageLoad::test_multi_root_resolves_each_class_to_its_real_root
designated_repro_test: null
acceptance:
- text: Given a coverage.xml with two declared source roots and a class filename that
    exists as a real repo path under only one of them, when load_coverage resolves
    it, then the class is labeled under the root it actually exists under, not the
    other declared root
  evidence: []
threat: null
component: null
---
FROBLEMS (aprog-private): with 'pytest --cov=scripts --cov=tests' (two roots), coverage.xml records filename='actgen/core.py' (rooted under scripts) but TEST005 reports it as 'tests/actgen/core.py' -- the coverage-XML-to-repo-path resolver picks the wrong root (last-declared/alphabetically-last?) for files whose package-relative path doesn't disambiguate. The 0%-coverage finding is correct; only the displayed path is wrong, and it misleads an agent opening the file. Fix: resolve each coverage filename against the actual root it exists under (stat each candidate root+relpath), not a single guessed root. Test: multi-root coverage.xml resolves each file to the root it truly lives under.