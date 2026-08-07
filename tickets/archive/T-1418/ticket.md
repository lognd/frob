---
id: T-1418
title: 'Classify all 306 TEST005 zeros: genuine gap or attribution artifact, before
  any further burn-down'
state: done
kind: bug
origin: human
created: '2026-08-02'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- docs/audits/**
- tests/unit/test_docs_test005_classification_t1418.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_docs_test005_classification_t1418.py
  reason: 'Land-time D-02 scope-binding check requires evidence covering a

    docs/audits/** symbol; docs/audits/** has no coverable code symbols, and

    this ticket''s kind (bug) is not in CMD_EVIDENCE_ALLOWED_KINDS so the

    docs-kind --evidence-cmd channel is unavailable. Per playbook section 5''s

    own exception ("add a small drift-lock test only if a gate actually

    demands one"), adding one narrow regression test that locks the

    classification CSV''s row count/shape so it cannot silently drift, and

    scoping it in so its evidence covers this ticket per D-02 route 2.

    '
  actor: logan
  at: '2026-08-02'
evidence:
- tests/unit/test_docs_test005_classification_t1418.py::TestClassificationCsv::test_has_exactly_306_rows
- tests/unit/test_docs_test005_classification_t1418.py::TestClassificationCsv::test_every_row_has_a_named_covering_test
- tests/unit/test_docs_test005_classification_t1418.py::TestClassificationCsv::test_classification_totals_match_the_audit_doc
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
acceptance:
- text: GIVEN the 306 symbols reporting exactly 0.0 percent branch coverage WHEN each
    is re-measured with its own test file running standalone under --cov THEN every
    one is classified as genuine gap or attribution artifact, with the covering test
    named for each artifact
  evidence:
  - tests/unit/test_docs_test005_classification_t1418.py::TestClassificationCsv::test_has_exactly_306_rows
  - tests/unit/test_docs_test005_classification_t1418.py::TestClassificationCsv::test_every_row_has_a_named_covering_test
  - tests/unit/test_docs_test005_classification_t1418.py::TestClassificationCsv::test_classification_totals_match_the_audit_doc
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- text: GIVEN the classification WHEN it is complete THEN a per-package count of genuine
    gaps versus artifacts is recorded in docs/audits/ as the input to the remaining
    burn-down plan
  evidence:
  - tests/unit/test_docs_test005_classification_t1418.py::TestClassificationCsv::test_has_exactly_306_rows
  - tests/unit/test_docs_test005_classification_t1418.py::TestClassificationCsv::test_every_row_has_a_named_covering_test
  - tests/unit/test_docs_test005_classification_t1418.py::TestClassificationCsv::test_classification_totals_match_the_audit_doc
  - tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
threat: null
component: null
---
Determines the true size of the v1.0.0 test-writing effort before any further burn-down is dispatched.

MEASURED on main 2026-08-02, from a clean coverage run (exit 0, 860 files stamped, source_sha=7454ba65, doctor healthy, no worker crashes):

    TEST005 unwaived total   1443
      at exactly 0.0 percent   306
      10-19 percent            170
      20-49 percent            107
      50-74 percent            119

The 306 at exactly 0.0 percent are the question. Three separate agents this session sampled them independently, in different packages, and each found REAL, behavioral, frob:tests-bound tests already covering the symbol:

  - T-1279 (gates): 10 of the 12 symbols its brief listed at 0.0 already had tests exercising both the clean and the finding-producing branches.
  - T-1296 (strata): _selfconform.py::check_self_conformance carries 67 real assertions and measures 95 percent standalone.
  - T-1276 (app): telemetry.py, config.py's loaders and _snapshot.py all verified covered against their existing dedicated test files.
  - T-1395 proved __main__ and serve/ trace correctly under the subprocess rc in isolation, yet report 0.0 in the full run.

So an unknown but apparently large share of the 306 are attribution artifacts -- code that IS tested, executed in a process pytest-cov does not attribute back -- not missing tests.

WHY THIS BLOCKS EVERYTHING DOWNSTREAM. Ten package-scoped burn-down tickets remain. Dispatching any of them against a falsely-zero symbol pushes an agent toward writing a duplicate test against already-tested code to move a number that was never real. That has already happened repeatedly this session and every agent that caught it had to stop and reason its way out. The count also determines the release plan: if 250 of the 306 are artifacts, the genuine remaining work is closer to 1190 findings than 1443, and the artifact class needs a fix rather than tests.

DELIVERABLE. A classification of all 306, not a sample. For each: genuinely untested, or attribution artifact with the existing covering test named. Machine-readable output (a file under docs/audits/) plus a summary count per package. Do NOT write any tests under this ticket -- classification only. Where the answer is artifact, name the test that covers it so the claim is checkable.

METHOD NOTE. A symbol reporting 0.0 in the full run but non-zero when its own test file runs standalone under --cov is definitionally an attribution artifact. That check is cheap and decisive; use it as the primary discriminator rather than reading tests by eye. Batch it -- do not run one pytest invocation per symbol.

Expect the artifact share to concentrate in code that runs in a subprocess, a daemon, or the console-script entry (src/frob/serve/**, src/frob/__main__.py, and the app runners reached only through CLI tests), since that is the shape T-1395 established. Report whether that prediction holds; if artifacts turn up somewhere structurally different, that is a new finding worth its own ticket.