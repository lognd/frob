---
id: T-2403
title: Burn down the 133 genuine SYS003 findings post-calibration, then promote to
  error
state: queued
kind: bug
origin: agent
created: '2026-08-18'
priority: medium
parent: T-0969
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: given a fresh frob check --only sys --json, when SYS003 findings are counted,
    then the count is zero
  evidence: []
- text: given src/frob/gates/_sys.py, when SYS003's severity is read, then it is ERROR
    not WARNING
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2380 (SYS003 gate-calibration investigation) reduced the SYS003 WARN
count from 4834 to 133 (measured via `uv run frob check --only sys
--json`, full gate-summary coverage, no BUDGET001 deferral) by:

1. Declaring explicit `testsuite -> component` Flows in design/frob.strata
   for the 18 components this repo's test suite legitimately imports
   (tickets_ledger, gates, graphlang, cli, core, vet, stratamod, checker,
   verify, refactor, serve, mutate, registry_model, deploy, natives,
   fleet, security, telemetry) -- NOT a `testsuite -> *` wildcard (that
   would disable the guard for the whole direction, the T-1967 failure
   shape). Production -> testsuite and testsuite -> any undeclared
   component still fire.
2. Reclassifying `src/frob/excludes.py`, `src/frob/yaml_io.py`,
   `src/frob/tomlio.py` from node `cli` to node `core` in the same
   design file -- these were imported by 8+ unrelated components with
   zero imports of their own (the signature of a cross-cutting leaf
   utility misplaced in the CLI entrypoint layer), verified against the
   architecture model before moving (not just inferred from import
   volume).
3. Declaring 3 genuinely missing production Flows this reclassification
   did not itself resolve: refactor->core, registry_model->core,
   verify->core (frob.logging/frob.gitio dependencies that were already
   correctly modeled under `core`, just never declared from these three
   callers).

Positive-control regression coverage for the narrowing lives in
tests/unit/strata/test_sys003_calibration.py (4 tests): a declared
testsuite->component edge is silent, an UNDECLARED testsuite->component
edge still fires, production->testsuite still fires, and a genuine
undeclared production-to-production import still fires independent of
the testsuite direction entirely.

This ticket is the single-dispatch burn-down of what remains: 133
findings, each a genuine undeclared production cross-component import
(not testsuite noise, not a misplaced-utility artifact -- both classes
were eliminated by T-2380). Sample composition (measured 2026-08-18):
25 cli->verify, 9 cli->stratamod, 9 tickets_ledger->graphlang, 8
gates->cli, 8 verify->tickets_ledger, 7 tickets_ledger->gates, 7
vet->stratamod, plus ~35 more pairs each under 5. Re-measure with `uv
run frob check --only sys --json` before starting -- do not hand-count
with grep.

For EACH finding, decide case by case whether it is:
(a) a genuine missing architectural dependency that should be declared
    as a new Flow in design/frob.strata (the common case, matching how
    T-2380 resolved refactor/registry_model/verify->core above), or
(b) a real layering violation that should be fixed by moving the import
    to go through an existing sanctioned path instead of declaring a new
    edge (rare -- only reach for this if a new Flow would encode a
    genuinely backwards dependency, e.g. a lower layer importing
    something that only makes sense in a higher one).

Closure is two-part per the epic (T-0969): (1) zero SYS003 findings,
verified via the same `frob check --only sys --json` command, AND
(2) SYS003 promoted from WARN to ERROR severity in `src/frob/gates/
_sys.py::_sys003_one_model` once clean -- do not stop at zero and leave
it advisory.
