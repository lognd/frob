## Done report

Verified both of T-1339's own acceptance criteria are ALREADY satisfied
by prior work under this same epic, not new implementation this ticket
needed to build:

- **Acceptance [0]** ("given a line carrying one checker's suppression
  and an unsuppressed diagnostic from another configured checker, when
  frob check runs, then SUPPRESS001 reports it"): implemented in
  `suppress001_gate` (`src/frob/gates/_suppress.py`, T-1340, phase 1),
  evidence-driven exactly per this ticket's own DESIGN section -- no
  mypy<->ty rule-code mapping table, the reporting checker's own
  diagnostic supplies the code. Fresh evidence: `TestSuppress001Gate::
  test_mypy_suppressed_ty_unsuppressed_fires` (the fixture case) and
  T-1342's own `TestSuppress001RepoWideLock::test_repo_is_currently_clean`
  (the real-repo case: main reads 0 unpaired suppressions today).

- **Acceptance [1]** ("given SUPPRESS001 findings, when frob check --fix
  runs, then the paired suppression is written with the reporting
  checker's own rule code, in canonical order, idempotently"):
  implemented in `fix_suppress001_paired_suppression`
  (`src/frob/gates/_fix_engine_text.py`, T-1341, phase 2), wired into
  `_fix_engine.py`'s Tier-A auto-fix registry (`TIER_A_HANDLERS`) -- so
  it already runs AUTOMATICALLY on every `frob ticket land`'s pre-land
  pass, matching the user's original directive verbatim ("all this tool
  compliance stuff should be automatically handled rather than manually
  done"), not something a human has to remember to invoke. Fresh
  evidence: `TestFixSuppress001PairedSuppression::
  test_mypy_suppressed_ty_unsuppressed_gets_paired_suppression`
  (writes the pair, canonical mypy/ruff/ty slot order per
  `_CANONICAL_DIALECT_ORDER`) and `::test_idempotent_second_fix_pass_is_a_no_op`
  (the "idempotently" clause).

The DESIGN AMENDMENT's own portability requirement -- suppressions must
satisfy ANY consumer's checker, not only the one this repo gates on --
is what `suppression_dialects()`'s ty/mypy split already encodes: ty is
the gating checker, mypy runs as a pure ORACLE (dev dependency, never a
gate) purely to produce ground-truth diagnostics for dialects this repo
itself never enforces. Confirmed directly: `shutil.which("mypy")`-gated
availability, `mypy` never appears in `_ALL_GATES`
(src/frob/gates/__init__.py) or any `_build_jobs` job list -- it cannot
fail a build, only feed SUPPRESS001's correlation.

Scope correction: T-1339's originally declared scope (`docs/modules/
gates.md`, `src/frob/gates/_waive.py`, `src/frob/gates/_fix_engine.py`)
predates the T-1340/T-1341 phase work that implemented both acceptance
criteria in `_suppress.py`/`_fix_engine_text.py` -- corrected via `frob
ticket scope --add` before closing, not a silent gap.

No code changes in this ticket: it is the closing verification pass for
an epic whose real implementation work already landed under its own
phase tickets (T-1340, T-1341, T-1342). No root-cause fix needed under
DEAD001/WIRE001/OPAQUE001/REF002.

### Changed
```
 tickets/T-1339/ticket.md | 51 +++++++++++++++++++++++++++++++++++++++++++++---
 1 file changed, 48 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_gates_suppress.py::TestSuppress001Gate::test_mypy_suppressed_ty_unsuppressed_fires` (pytest node id, verified passing when recorded)
- `tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression::test_mypy_suppressed_ty_unsuppressed_gets_paired_suppression` (pytest node id, verified passing when recorded)
- `tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression::test_idempotent_second_fix_pass_is_a_no_op` (pytest node id, verified passing when recorded)
- `tests/test_gates_suppress.py::TestSuppress001RepoWideLock::test_repo_is_currently_clean` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 3 error(s), 832 warning(s), 725 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/__init__.py, PRE001@tickets/T-1339, SEC110@src/frob/app/ticket_runner/__init__.py
