---
id: T-4175
title: 'consumer round-4 backend audit: nine findings written as why the gates missed
  them, including a second independent report of waiver premises expiring unchecked'
state: queued
kind: bug
origin: auditor
created: '2026-09-07'
priority: critical
parent: null
tier: epic
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given the findings in this epic, when it is decomposed, then each has its
    own leaf or recorded evidence on an existing open ticket, with the choice stated
    per finding
  evidence: []
- text: given a waiver whose stated premise has ceased to hold, when the gates run,
    then it no longer suppresses its finding
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
A CONSUMER'S FOURTH-ROUND BACKEND AUDIT, verbatim, and the most useful of the set
so far: every entry is written as "why the gates missed it" rather than as a
defect report. It is a critique of our detection model, from someone who found
the defects by hand first.

DECOMPOSE ONE LEAF PER FINDING, with real scope and an explicit note per leaf
saying whether the rule can be fixture-tested in frob's own tree.

THE ONE TO WORK FIRST IS NOT NEW -- IT IS A SECOND INDEPENDENT REPORT OF A
MECHANISM ALREADY FILED, and that changes its priority:

    a WIRE001 waiver "carries precisely the directive that tells the wiring
    gate to stop asking -- the waiver was honest when written and nothing
    re-examines it when the wiring later lands elsewhere"

T-4157 (their round-4 engine audit) records the same shape from a different
angle: a waiver whose stated reason was "the file is absent on this branch" kept
suppressing a real finding after a merge made that false. Two audits, two
subsystems, one mechanism -- A WAIVER'S PREMISE CAN EXPIRE AND NOTHING
RE-EVALUATES IT. Attach this evidence to whichever leaf T-4157 produces for it
rather than filing a third copy.

FOUR OTHER THEMES WORTH NAMING BEFORE THE LEAVES ARE CUT:

  TESTS THAT PROVE SOMETHING ABOUT A SYNTHETIC SUBJECT. One of their system tests
  builds a THROWAWAY application with one synthetic route per error type and
  asserts against that, "never touching the real routers, so an error body
  constructed anywhere other than the mapper is outside its reach by
  construction". The test is green and its subject is not the system. That is the
  dogfooding blindness we keep finding in ourselves, expressed as a test-design
  defect -- and it is detectable in principle: a test whose subject is
  constructed in the test file rather than imported from the package is a
  different kind of evidence and could be labelled as such.

  A CLAIM ABOUT THE REGISTRY MISTAKEN FOR A CLAIM ABOUT THE SURFACE. Their
  coverage assertion proves every registered error has a mapping -- "a claim about
  the registry, not about the response surface. Nothing enumerates the error
  responses the framework itself can produce." We have the identical shape: a
  gate registered in one list and absent from another is exactly this, and it cost
  this repo two CI rounds today.

  THE ONE BROKEN THING IS THE ONE THING NO TEST USES. Their module's entry-point
  guard is not a symbol, so symbol coverage reports it covered while the CLI
  entry point is broken. Coverage measured over the wrong denominator reads as
  complete.

  A TEST THAT ENCODES THE DEFECT AS THE REQUIREMENT. One of their unit tests
  asserts the rate limit fires even for a legitimate caller -- so the bug IS the
  spec, and no gate can distinguish that from a correct requirement. Probably not
  fixable by a rule, but worth stating as a known limit rather than discovering it
  again next round.

DOGFOODING NOTE: routes, containers, runbooks, rate limits, log records. frob has
none of these. Our green is evidence of nothing for most of these leaves; say so
per leaf.

QUEUE NOTE FOR WHOEVER DECOMPOSES THIS: there are now several undecomposed audit
epics open at once. Before cutting new leaves, check the others for the same
finding -- at least one mechanism here is already known to be duplicated across
two of them.

VERBATIM REPORT FOLLOWS.

## F-373 (2026-09-07) backend round 4 audit: why the gates and strata missed each finding (verbatim from docs/security/audit-2026-09-07-backend-round4.md)
Why the gates missed it. The route's own unit tests (test_ingest_rejects_bad_token, test_ingest_writes_alert_and_202) construct the header themselves, and tests/unit/test_ops_backup.py asserts on the *payload*, not the headers -- so both halves pass in isolation and no gate compares producer against consumer. frob has no cross-artifact rule of the shape "a shell script that POSTs to an 

Why the gates missed it. frob's SYS/COV/REF gates reason over Python symbols and doc anchors, not over Dockerfile COPY operands or the existence of an importlib target resolved from a string literal -- and the OPAQUE001 waiver on _dispatch_deferred explicitly legitimises the dynamic import ("the target module genuinely does not exist yet"), which converts a missing module into documented, waived 

Why the gates missed it. SIT-012 (backend/tests/system/test_error_contract.py:26-53) builds a *throwaway* FastAPI() with one synthetic route per ErrorSet member and asserts on those -- it never touches the real routers, so an error body constructed anywhere other than to_http_exception is outside its reach by construction. test_openapi_export_error_codes_match_mapping 

Why the gates missed it. _assert_total_coverage() proves every registered ErrorSet member has an HTTP mapping -- a claim about the *registry*, not about the *response surface*. Nothing enumerates the error responses FastAPI itself can produce. The rule that would catch it: a system test that fires one deliberately malformed request at each POST route in the real app's route table and asserts the envelope 

Why the gates missed it. tests/unit/test_ops_backup.py exercises backup.sh under DRY_RUN=1; no test executes, parses, or even lints the runbook's fenced commands, and frob's doc gates check anchors and drift, not whether a documented shell command would run. The rule that would catch it: mark runbook code fences with a frob:doc-adjacent directive naming the container they run in, and 

Why the gates missed it. UT-1308 asserts the 429 fires even with a correct token, so the test encodes the defect as the requirement. No gate reasons about whether a rate-limit threshold is compatible with the legitimate call rate of the route's only real caller; that is a capacity question, and neither strata's rate clauses (which describe outbound flows) nor frob check model inbound call budgets. 

Why the gates missed it. Every existing test for this module imports it in-process under pytest, where the repo root is already on sys.path -- so the one thing that is broken (the CLI entry point) is the one thing no test uses. frob's TEST/COV gates measure whether symbols are covered, and build_app, schema, render, and main are all covered; the module's __main__ guard is not a symbol they 

Why the gates missed it. purge_unverified carries a frob:waive WIRE001, which is precisely the directive that tells the wiring gate to stop asking -- the waiver was honest when written and nothing re-examines it when the wiring later lands elsewhere. A waiver staleness check ("this WIRE001 waiver says 'not yet wired'; a caller of a sibling symbol in the same module now exists") would have caught it. 

Why the gates missed it. test_redaction_filter_masks_secrets passes secrets in the message, which is the surface the filter handles; frob's PII gate is structural (it knows which nodes carry which PII classes) and does not model the message/extra split inside a log record. 

