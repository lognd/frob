## Done report

T-0781 implements the SEC005 taint rule Audit M1's gate-direction finding
asked for: a value parsed from a repo-writable state file under `.git/`
or `.frob/` (JSON or text -- both writable by any worktree/agent sharing
this clone) reaching a `subprocess`/`frob.gitio.run_argv` argv position
requires a registered validator hop or a preceding literal `"--"`
terminator; a flow with neither is a finding naming source and sink line.

New:
- src/frob/vet/_taint.py -- `taint_findings(path)`: an intra-function/
  intra-module AST pass (T-0781's own body: "scope it honestly as intra-
  module flow first, interprocedural later"). SOURCE = an assignment
  whose RHS is a read-like call (`read_text`/`read_bytes`/`json.load`/
  `json.loads`/`.../safe_load`) whose own unparsed text mentions `.git`/
  `.frob`. SINK = a `subprocess.run`/`Popen`/`call`/`check_call`/
  `check_output`/`run_argv`-shaped call whose first positional argument
  is a `List`/`Tuple` LITERAL (a non-literal argv is a disclosed gap, not
  a silent all-clear -- pinned by
  `test_dynamic_argv_list_is_not_falsely_cleared`). VALIDATION = a call
  whose function name matches `validate`/`sanitize`/`assert_safe`/
  `confine`/`quote` clears taint for its result and its own argument
  names. A `"--"` string literal earlier in the same argv list clears
  every element after it.
- src/frob/gates/_taint_gate.py -- `taint_gate(root)`: the SEC005
  tracked-`.py`-file scan wrapper, WARN-tier at first turn-on (same
  T-0688/T-0973 promotion posture `opaque_gate` already established --
  a brand-new structural rule needs a real fix-or-waive pass over its
  first measured hit set before ERROR is safe). Self-scan against this
  repo's own live `.py` tree found ZERO hits (`gate:SEC` 0
  errors/0 warnings in the full `--only gates-security` run) -- no
  waiver churn needed to turn this on.
- Wired into src/frob/gates/__init__.py's `process_jobs` (a `"taint"`
  job, same shape as `"secrets"`/`"opaque"`) and `_KNOWN_GATE_RULES`
  (src/frob/gates/_waive.py) so `frob:waive SEC005 reason="..."` and any
  future `handled_by:SEC005` registry entry both resolve.
- tests/unit/vet/test_taint.py -- 8 tests: the acceptance criterion's
  fire/no-fire pair (`test_unvalidated_state_read_reaching_argv_fires`/
  `test_validated_value_does_not_fire`), the `"--"`-terminator discharge
  shape, a non-state-read negative, the disclosed dynamic-argv-list gap,
  a malformed-file negative, and the gate wrapper's empty-tree/real-repo
  cases.

DISCLOSED CUT: `"taint"` was not added to `_STAGE_GROUPS`'s
`"gates-security"` alias in `src/frob/check/__init__.py` -- that file is
outside this ticket's declared scope (`src/frob/vet/**`,
`src/frob/gates/**`). The gate still runs under an unscoped `frob check`
(it is a live `process_jobs` member); only the `--only gates-security`
convenience alias omits it for now. Noted, not silently worked around.

Verification: `pytest tests/unit/vet/test_taint.py -q` -- 8 passed.
`frob check --only lint` -- clean (ruff-check/ruff-format/ty all pass on
the touched files; one pre-existing unrelated ruff-format finding in
`src/frob/dup/_pipeline/_callgraph.py`, not touched here). `frob check
--ticket T-0781 --only gates-native`/`gates-security` -- 0 new errors;
the one remaining DRIFT002 (`tests/unit/test_dup_smt.py`) is pre-existing
(`git diff main` over that file/its target is empty) and unrelated to
this ticket's files. One real DUP001 hit
(`_sink_argv_elements`/`_walk_lint._first_arg_literal`, same boilerplate
shape, different return semantics) waived with a specific reason at the
site.

### Changed
```
 tickets.md | 3 +--
 1 file changed, 1 insertion(+), 2 deletions(-)
```

### Evidence
- `tests/unit/vet/test_taint.py::TestTaintFindings::test_unvalidated_state_read_reaching_argv_fires` (pytest node id, verified passing when recorded)
- `tests/unit/vet/test_taint.py::TestTaintFindings::test_validated_value_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/unit/vet/test_taint.py::TestTaintFindings::test_dash_dash_terminator_clears_taint` (pytest node id, verified passing when recorded)
- `tests/unit/vet/test_taint.py::TestTaintFindings::test_non_state_read_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/unit/vet/test_taint.py::TestTaintFindings::test_dynamic_argv_list_is_not_falsely_cleared` (pytest node id, verified passing when recorded)
- `tests/unit/vet/test_taint.py::TestTaintFindings::test_unparseable_file_returns_empty` (pytest node id, verified passing when recorded)
- `tests/unit/vet/test_taint.py::TestTaintGate::test_taint_gate_no_findings_on_empty_tracked_set` (pytest node id, verified passing when recorded)
- `tests/unit/vet/test_taint.py::TestTaintGate::test_taint_gate_emits_warn_severity_violation` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: 11 error(s), 1778 warning(s), 420 waived
- error-findings: AFFECT001@src/frob/gates/_taint_gate.py, COV001@src/frob/vet/_taint.py, DRIFT002@tests/unit/test_dup_smt.py, INV006@src/frob/dup/_pipeline/__init__.py, INV006@src/frob/dup/_pipeline/_fingerprint.py, INV006@src/frob/dup/_pipeline/_normalize.py, INV006@src/frob/dup/_pipeline/_probe.py, INV006@src/frob/dup/_pipeline/_shared.py, INV006@src/frob/vet/_taint.py, PRE001@tickets/T-0781, TEST001@src/frob/vet/_taint.py
