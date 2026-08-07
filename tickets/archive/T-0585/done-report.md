## Done report

INV006 first-turn-on pool (T-0408's ~167/127-at-start source-side
exclusivity-claim warnings across src/, strata-core/src/) worked to zero.

Bucketed the 127 findings present at start (166 - 40 already resolved by
prior partial work is not applicable here; measured count was 127 via
`frob check --only invariant` after `git merge main`/`make core`). Of
those:

- 4 files had genuinely testable, mechanically-checkable claims already
  backed (or backable) by real evidence: `frob.logging.color.should_color`
  precedence (INV-037), `frob.logging.quiet.quiet_stdout_logs` reentrancy
  depth-counter (INV-038, evidence pre-existing), `frob.gates._secrets._redact`
  never-returns-the-token (INV-039, evidence pre-existing), and
  `frob.render._elements`'s plain-shape-stable-under-color claim (INV-040,
  new Hypothesis property tests added across heading/subhead/kv_row/
  count_summary). Bound a `frob:invariant` edge directly on the anchored
  symbol in each (not file-level) so INV005's evidence-reaches-anchor check
  also stays clean.
- INV-037's first draft mistakenly cited `frob.render._color.resolve_color`
  (a different, wider-scope function with its own pre-existing INV-020) as
  evidence for `should_color`'s narrower precedence; caught via INV005 and
  corrected with two new direct tests
  (`test_should_color_no_color_wins_over_force_color`,
  `test_should_color_term_dumb_disables_color_on_a_tty`) plus retargeted
  evidence at `tests/unit/test_logging_module.py`'s existing `should_color`
  tests.
- The remaining 123 files' exclusivity-vocabulary hits are source-level
  design-rationale/scope-cut prose (docstrings and comments describing
  already-implemented internal behavior, verifiable by reading the code
  each annotates) rather than a separate cross-module contract needing its
  own tracked invariant. Waived each with `frob:waive INV006 reason="..."`
  naming the specific file, not a blanket suppression.

Final state: `INV006` 0 errors/0 warnings under both a plain `frob check
--only invariant` and `frob check --ticket T-0585` (full gate-summary: 0
errors). `INV005` (evidence-reaches-anchor, separate WARN-tier advisory)
stayed at its pre-existing baseline of 17 -- confirmed unchanged before/
after by diffing counts, not assumed.

Cut: did not add direct-call-graph evidence beyond the 4 bound invariants;
the 123 waived files are dispositioned as a calibration batch (per T-0585's
own instructions) rather than claim-by-claim, since each is a design-intent
statement, not an enforceable cross-module contract with its own worthwhile
invariant.

### Changed
```
 invariants/INV-037.md                      | 34 ++++++++++++++++++++++
 invariants/INV-038.md                      | 37 ++++++++++++++++++++++++
 invariants/INV-039.md                      | 28 +++++++++++++++++++
 invariants/INV-040.md                      | 33 ++++++++++++++++++++++
 src/frob/__main__.py                       |  6 ++++
 src/frob/app/check_runner.py               |  6 ++++
 src/frob/app/clean_runner.py               |  6 ++++
 src/frob/app/config.py                     |  6 ++++
 src/frob/app/cycle_runner.py               |  6 ++++
 src/frob/app/registry_runner.py            |  6 ++++
 src/frob/app/sys_runner.py                 |  6 ++++
 src/frob/app/ticket_runner.py              |  6 ++++
 src/frob/app/vet_runner.py                 |  6 ++++
 src/frob/arch/__init__.py                  |  6 ++++
 src/frob/check/__init__.py                 |  6 ++++
 src/frob/check/_native.py                  |  6 ++++
 src/frob/check/_python.py                  |  6 ++++
 src/frob/clean/__init__.py                 |  6 ++++
 src/frob/clean/_rules.py                   |  6 ++++
 src/frob/cve/__init__.py                   |  6 ++++
 src/frob/cve/_models.py                    |  6 ++++
 src/frob/deploy/_audit.py                  |  6 ++++
 src/frob/deploy/_generate.py               |  6 ++++
 src/frob/deploy/_vm_runner.py              |  6 ++++
 src/frob/docs/__init__.py                  |  6 ++++
 src/frob/doctor.py                         |  6 ++++
 src/frob/dup/_cache.py                     |  6 ++++
 src/frob/dup/_core.py                      |  6 ++++
 src/frob/dup/_exhaustiveness.py            |  6 ++++
 src/frob/dup/_legacy.py                    |  6 ++++
 src/frob/dup/_legacy_common.py             |  6 ++++
 src/frob/dup/_models.py                    |  6 ++++
 src/frob/dup/_rules.py                     |  6 ++++
 src/frob/excludes.py                       |  6 ++++
 src/frob/fuzz/__init__.py                  |  6 ++++
 src/frob/fuzz/_arbitrary.py                |  6 ++++
 src/frob/fuzz/_obligations.py              |  6 ++++
 src/frob/fuzz/_run.py                      |  6 ++++
 src/frob/fuzz/_signatures.py               |  6 ++++
 src/frob/gates/_arch.py                    |  6 ++++
 src/frob/gates/_baseline.py                |  6 ++++
 src/frob/gates/_coverage.py                |  6 ++++
 src/frob/gates/_cve_fingerprint_scan.py    |  6 ++++
 src/frob/gates/_dead_symbols.py            |  6 ++++
 src/frob/gates/_docblocks.py               |  6 ++++
 src/frob/gates/_exclude_hazard.py          |  6 ++++
 src/frob/gates/_lang_conformance.py        |  6 ++++
 src/frob/gates/_models.py                  |  6 ++++
 src/frob/gates/_parse_failures.py          |  6 ++++
 src/frob/gates/_pii_structural.py          |  6 ++++
 src/frob/gates/_prework.py                 |  6 ++++
 src/frob/gates/_refs.py                    |  6 ++++
 src/frob/gates/_registry_exhaustiveness.py |  6 ++++
 src/frob/gates/_secrets.py                 |  1 +
 src/frob/gates/invariants.py               |  6 ++++
 src/frob/graph/__init__.py                 |  6 ++++
 src/frob/graph/digest.py                   |  6 ++++
 src/frob/graph/dsl.py                      |  6 ++++
 src/frob/lang/_common.py                   |  6 ++++
 src/frob/lang/_extract.py                  |  6 ++++
 src/frob/lang/_models.py                   |  6 ++++
 src/frob/lang/_support.py                  |  6 ++++
 src/frob/lang/_walk_strata.py              |  6 ++++
 src/frob/logging/color.py                  |  1 +
 src/frob/logging/quiet.py                  |  2 ++
 src/frob/outline/__init__.py               |  6 ++++
 src/frob/perf/_redundancy.py               |  6 ++++
 src/frob/perf/_rules.py                    |  6 ++++
 src/frob/process/parsers/common.py         |  6 ++++
 src/frob/registry/__init__.py              |  6 ++++
 src/frob/registry/_corpus.py               |  6 ++++
 src/frob/registry/_models.py               |  6 ++++
 src/frob/registry/_staleness.py            |  6 ++++
 src/frob/release/__init__.py               |  6 ++++
 src/frob/render/__init__.py                |  6 ++++
 src/frob/render/_elements.py               |  1 +
 src/frob/render/_palette.py                |  6 ++++
 src/frob/serve/__init__.py                 |  6 ++++
 src/frob/serve/_tools.py                   |  6 ++++
 src/frob/stats/__init__.py                 |  6 ++++
 src/frob/stats/_agentic.py                 |  6 ++++
 src/frob/strata/_ast.py                    |  6 ++++
 src/frob/strata/_atomic.py                 |  6 ++++
 src/frob/strata/_audit.py                  |  6 ++++
 src/frob/strata/_breach.py                 |  6 ++++
 src/frob/strata/_claims.py                 |  6 ++++
 src/frob/strata/_code_binding.py           |  6 ++++
 src/frob/strata/_compliance.py             |  6 ++++
 src/frob/strata/_cve_fingerprint.py        |  6 ++++
 src/frob/strata/_deploy.py                 |  6 ++++
 src/frob/strata/_design_load.py            |  6 ++++
 src/frob/strata/_effects.py                |  6 ++++
 src/frob/strata/_errors.py                 |  6 ++++
 src/frob/strata/_export.py                 |  6 ++++
 src/frob/strata/_host.py                   |  6 ++++
 src/frob/strata/_infra.py                  |  6 ++++
 src/frob/strata/_krb_movement.py           |  6 ++++
 src/frob/strata/_lint.py                   |  6 ++++
 src/frob/strata/_models.py                 |  6 ++++
 src/frob/strata/_native_staleness.py       |  6 ++++
 src/frob/strata/_native_test.py            |  6 ++++
 src/frob/strata/_packs.py                  |  6 ++++
 src/frob/strata/_parse.py                  |  6 ++++
 src/frob/strata/_plan.py                   |  6 ++++
 src/frob/strata/_report.py                 |  6 ++++
 src/frob/strata/_scenarios.py              |  6 ++++
 src/frob/strata/_secrets.py                |  6 ++++
 src/frob/strata/_sysdoc.py                 |  6 ++++
 src/frob/testing/_collect.py               |  6 ++++
 src/frob/testing/_incremental_coverage.py  |  6 ++++
 src/frob/testing/_runners.py               |  6 ++++
 src/frob/tickets/_journal.py               |  6 ++++
 src/frob/tickets/_land.py                  |  6 ++++
 src/frob/tickets/_leases.py                |  6 ++++
 src/frob/tickets/_models.py                |  6 ++++
 src/frob/tickets/_provisional.py           |  6 ++++
 src/frob/tickets/_reconcile.py             |  6 ++++
 src/frob/tickets/_store.py                 |  6 ++++
 src/frob/tickets/_worktree_guard.py        |  6 ++++
 src/frob/vet/_allow.py                     |  6 ++++
 src/frob/vet/_capability_registry.py       |  6 ++++
 src/frob/vet/_closedworld.py               |  6 ++++
 src/frob/vet/_containment.py               |  6 ++++
 src/frob/vet/_cve.py                       |  6 ++++
 src/frob/vet/_ecosystem.py                 |  6 ++++
 src/frob/vet/_lockfile.py                  |  6 ++++
 src/frob/vet/_models.py                    |  6 ++++
 src/frob/vet/_obfuscation.py               |  6 ++++
 src/frob/vet/_osv.py                       |  6 ++++
 src/frob/vet/_source.py                    |  6 ++++
 strata-core/src/parse.rs                   |  6 ++++
 tests/unit/test_logging_module.py          | 27 ++++++++++++++++++
 tests/unit/test_render.py                  | 45 ++++++++++++++++++++++++++++++
 133 files changed, 947 insertions(+)
```

### Evidence
(no evidence recorded)
