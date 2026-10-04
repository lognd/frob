+++
id = "01M1WJMD43QA4H55AS684P9467"
title = "evidence classification: a test whose subject is constructed in the test file rather than imported from the package is weaker evidence"
type = "task"
category = "triage"
priority = "high"
parent = "01M1WJMD2FWKPS1J7MPF18KDVY"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-09-07T00:00:00Z"
aliases = ["T-4227"]
labels = ["milestone:1.1.0", "v1-cluster:B4"]
scope = ["src/frob/gates"]
+++

Consumer F-373/P3 (T-4175): a system test builds a throwaway app with one synthetic route per error type and asserts against that -- it never touches the real routers, so an error body constructed anywhere other than the intended mapper is outside its reach by construction. The test is green and its subject is not the system. This is the dogfooding-blindness class expressed as a test-design defect, and it is detectable in principle: label a test whose subject (app/route table/registry instance) is constructed inline in the test file, rather than imported from the package under test, as a distinct and weaker evidence kind. High-value, generic. Fixture-testable: YES, frob's own evidence-binding code with a synthetic example (a test that builds its own throwaway object instead of importing the real one).
