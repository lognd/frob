## Done report

Fixed all three defects in descending priority order.

**Defect 1 (priority): abort prints as pass.**
`src/frob/check/_python.py::_gates_error_result`: `GateError.ConfigMalformed`
and `GateError.GraphUnavailable` (the two sentinels
`_load_graph_queue_lock`/`_load_required_state` return when the
graph/lock/invariants/policy state every gate depends on could not be
assembled at all) now render as a hard, non-zero-exit `GATES001` ERROR,
matching the existing `QueueUnavailable`/`QUEUE001` treatment -- not the old
`exit_code=0` "gates skipped: ..." soft skip. A stage that did not run can
no longer report pass.

**Defect 2: blast radius wrong, now scoped to the one bad file.**
`src/frob/gates/invariants.py::load_invariants` no longer aborts on the
first malformed file. It now returns `LoadedInvariants` (plain value, not
`Result` -- there is no longer a whole-load failure case to represent):
every invariant that parsed, plus one `InvariantLoadError` (path + reason)
per file that didn't. Duplicate ids are likewise scoped to the SECOND file
declaring the id, not a whole-load abort. `src/frob/gates/__init__.py`'s
`_load_required_state` threads these per-file errors through
`_GateInputs.invariant_load_errors` instead of aborting; the new
`_invariant_load_error_violations` helper turns each into an ERROR-severity
**INV009** violation (naming the exact bad file) inside the `gate:invariant`
job -- every OTHER gate family (SEC/PII/COV/SCOPE/...) runs completely
unaffected.

**Defect 3: two id grammars disagreed, now one shared grammar, widened.**
Verified the `frob:invariant` code-comment directive's actual grammar before
choosing a pattern: `frob.graph.dsl`'s target parsing imposes NO format
restriction of its own, and this repo already has a real, working
descriptive-id example (`# frob:invariant INV-RENDER-SOLE-STDOUT` in
`src/frob/gates/_render_lint.py`). Widened `invariants.py::_ID_RE` from
`^INV-\d{3}$` to `^INV-[A-Z0-9]+(?:-[A-Z0-9]+)*$` -- one shared definition
that accepts both `INV-045` and a descriptive id (`INV-ADMIN-DATA-001`,
`INV-RENDER-SOLE-STDOUT`) while still rejecting lowercase/empty segments/bare
`INV-` loudly. Did not touch the directive (widening the loader to match it,
per the ticket's explicit instruction).

### Changed
- src/frob/gates/invariants.py -- `_ID_RE` widened; `InvariantError` is now
  per-file; new `InvariantLoadError`/`LoadedInvariants` models;
  `load_invariants` rewritten to per-file scoping (see above).
- src/frob/gates/__init__.py -- `_GateInputs.invariant_load_errors` field;
  `_load_required_state`/`_load_graph_queue_lock` thread per-file invariant
  errors through instead of aborting; new `_invariant_load_error_violations`
  (INV009) wired into the `gate:invariant` job.
- src/frob/check/_python.py -- `_gates_error_result`'s new
  ConfigMalformed/GraphUnavailable hard-error branch (GATES001).
- src/frob/gates/_waive.py -- registered `INV009` and `GATES001` in
  `_KNOWN_GATE_RULES` (GATERULE001).
- docs/modules/gates.md -- Invariants section rewritten for the new
  per-file-scoped contract, `LoadedInvariants`/`InvariantLoadError`
  documented, INV009 rule-table row added, shared id-grammar note added.
- docs/design/registry/check-coverage.yaml -- `CHK-GATE-GATES001`/
  `CHK-GATE-INV009` entries added via `frob registry audit
  --sync-gate-rules`, then bound with `frob:enforces` directives at the two
  enforcing sites (REG008).
- tests/gates_suite/test_invariant.py -- `TestInvariantLoad` rewritten for
  the new `LoadedInvariants` API (still exercises every existing branch,
  same test names T-0160's own evidence cites -- see the `frob:waive DUP002`
  note on why the three field-shape tests were NOT consolidated); added
  `test_descriptive_id_loads` (grammar fixture) and
  `test_one_malformed_file_does_not_block_others` (blast-radius fixture).
- tests/gates_suite/test_run.py -- new `TestInvariantLoadBlastRadius`: the
  MUST-FIRE and MUST-STAY-QUIET fixtures via real `run_gates()` calls
  against a constructed `invariants/` directory (this repo's own is empty,
  T-3928 -- a vacuous gate proves nothing, so these fixtures build real
  invariant files including a malformed one), plus the directive/loader
  grammar-agreement fixture.
- tests/unit/test_check.py -- new `TestGatesErrorResultTotalAbort`: the
  fourth fixture (a stage that did not execute never reports pass).

**Fixtures (all four required, all present and green):**
1. MUST-FIRE:
   `test_run.py::TestInvariantLoadBlastRadius::test_must_fire_malformed_invariant_file_produces_named_error`
2. MUST-STAY-QUIET:
   `test_run.py::TestInvariantLoadBlastRadius::test_must_stay_quiet_other_gates_run_normally_beside_one_malformed_file`
3. Descriptive id, directive and loader agree:
   `test_run.py::TestInvariantLoadBlastRadius::test_descriptive_id_directive_and_loader_agree`
   (plus the narrower loader-only proof,
   `test_invariant.py::TestInvariantLoad::test_descriptive_id_loads`)
4. No gate ever prints pass for a stage that did not execute:
   `test_check.py::TestGatesErrorResultTotalAbort::test_config_malformed_is_a_hard_error_not_a_pass`
   and `::test_graph_unavailable_is_a_hard_error_not_a_pass`

**Cross-reference: T-3985.**
T-3985 (the subject-count primitive) is a GENERIC mechanism that would make
"a verdict over zero subjects because a stage never ran" unrepresentable by
construction, repo-wide. This ticket's fix is a SPECIFIC, targeted fix for
this one call path (`run_gates`'s two total-abort sentinels rendered as a
hard error instead of a soft skip in `_gates_error_result`, plus the
invariants blast-radius scoping). Neither subsumes the other: T-3985, if
built, would likely make this ticket's `_gates_error_result` special-casing
unnecessary (any zero-subject verdict would be structurally impossible to
state as a pass), but T-3985 does not exist yet and this ticket did not
build it (per the ticket's own instruction not to). This ticket's INV009
blast-radius scoping is orthogonal to T-3985 either way -- that's a
LOAD-time defect T-3985's runtime-verdict primitive would not touch.

**Filed:** none. No out-of-scope structural defect found beyond the two
already-known ones the ticket itself names: T-3928 (empty invariants/ making
INV gates vacuous here) and T-3985 (the subject-count primitive).

**Gates:**
`frob check --ticket T-4019`: 220 errors remain, every one pre-existing or
disclosed noise unrelated to this diff, verified individually:
- gate:DRIFT (1): `src/frob/xref/__init__.py::xref` and (waived)
  `src/frob/tickets/_evidence.py::add_cmd_evidence` -- neither file touched
  by this diff.
- gate:TODO (1): `tests/unit/test_check.py:221` -- a pre-existing comment
  ("...COV/DOC/DRIFT/INV/DEC/TODO gates...") that lexically contains the
  word TODO as part of a real gate-family list, not a bare marker; not part
  of this diff's added lines.
- gate:SCOPE (218, SCOPE002, WARN-by-rule but `frob.toml` elevates it to
  ERROR repo-wide): `docs/modules/gates.md` documents the ENTIRE gates
  module (hundreds of symbols across dozens of unrelated files), and
  `src/frob/gates/__init__.py` is cross-documented by half a dozen OTHER
  docs (perf.md, release.md, serve.md, app.md, design/frob.strata) plus
  reverse `frob:tests` edges into dozens of unrelated test files -- any
  ticket that touches either file inherits that whole closure graph.
  Chasing full closure would mean scoping most of src/frob/gates/**,
  src/frob/check/**, and a large fraction of tests/** for a defect fix
  that touches ~7 files. This is the SAME class T-3914's own done report
  disclosed (`docs/modules/gates.md`... "scope-closure breadth... out of
  proportion to the change") and F-036/T-3841 already track generically.
  `frob:waive SCOPE002 reason="docs/modules/gates.md and
  src/frob/gates/__init__.py are each cross-documented/cross-tested far
  beyond this ticket's actual diff (gates.md describes the whole gates
  module; __init__.py is referenced by perf.md/release.md/serve.md/app.md/
  design/frob.strata and dozens of reverse frob:tests edges) -- narrowing
  would require pulling in most of src/frob/gates/**, src/frob/check/**,
  and a large slice of tests/** for a load-scoping fix that touches 7
  files; same disclosed-breadth class as T-3914"`
- ruff-format (23 files repo-wide): none of this ticket's 8 changed files
  are in that list (verified by diffing the reformat list against changed
  files).

`frob test --base main`: PASS, touched=44, python exit=0, 17 outcomes
recorded, all green (also ran with touched=41/12-outcomes on an earlier,
smaller diff -- both clean).

**Evidence:**
11 pytest node ids recorded via `frob ticket evidence T-4019` (all verified
passing when recorded): the 6 `TestInvariantLoad` cases covering the new
`LoadedInvariants` contract plus the descriptive-id and blast-radius unit
fixtures, the 3 `TestInvariantLoadBlastRadius` integration fixtures
(must-fire/must-stay-quiet/grammar-agreement), and the 2
`TestGatesErrorResultTotalAbort` fixtures (ConfigMalformed/GraphUnavailable
hard-error).

### Changed
```
 tickets/T-4019/done-report.md | 177 ++++++++++++++++++++++++++++++++++++++++++
 tickets/T-4019/ticket.md      | 103 ++++++++++++++++++++++++
 2 files changed, 280 insertions(+)
```

### Evidence
- `tests/gates_suite/test_invariant.py::TestInvariantLoad::test_malformed_bad_id` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_invariant.py::TestInvariantLoad::test_duplicate_id` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_invariant.py::TestInvariantLoad::test_missing_directory_ok` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_invariant.py::TestInvariantLoad::test_loads_valid` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_invariant.py::TestInvariantLoad::test_descriptive_id_loads` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_invariant.py::TestInvariantLoad::test_one_malformed_file_does_not_block_others` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_run.py::TestInvariantLoadBlastRadius::test_must_fire_malformed_invariant_file_produces_named_error` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_run.py::TestInvariantLoadBlastRadius::test_must_stay_quiet_other_gates_run_normally_beside_one_malformed_file` (pytest node id, verified passing when recorded)
- `tests/gates_suite/test_run.py::TestInvariantLoadBlastRadius::test_descriptive_id_directive_and_loader_agree` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestGatesErrorResultTotalAbort::test_config_malformed_is_a_hard_error_not_a_pass` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestGatesErrorResultTotalAbort::test_graph_unavailable_is_a_hard_error_not_a_pass` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 11 passed (from 11 evidence id(s))
- gates: 2 error(s), 4412 warning(s), 935 waived
- error-findings: DRIFT001@src/frob/xref/__init__.py, SCOPE002@tickets.md
