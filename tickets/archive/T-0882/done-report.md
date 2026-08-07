## Done report

Root cause: the eval/exec needle isn't scanned inside `src/frob/strata/**`
at all -- `_selfconform.py`'s SYS100-extended pass delegates to
`frob.vet._capability.scan_file_capabilities`, whose `_matched_capabilities`
did a plain substring match on `"eval("`/`"exec("`. That matches any
identifier merely ENDING in the needle text (`_mutation_for_eval(`), not
just a real builtin call site -- the exact T-0151-class false positive
already fixed once for `compile(`. Scope was widened (`frob ticket scope
--add src/frob/vet/_capability.py`, reason recorded in `scope_changes`
above) since the real fix has to live where the needle table does.

Changed:
- `src/frob/vet/_capability.py::_needle_hits_as_bare_call` (new) -- sibling
  of `_needle_hits_outside_comments` requiring a word/dot boundary before
  the needle, mirroring `_has_bare_compile_call`'s T-0151 precedent.
- `src/frob/vet/_capability.py::_BARE_CALL_NEEDLES` (new) -- names
  `eval(`/`exec(` as the two needles that route through the bare-call
  check instead of plain substring; the registry's needle text itself is
  left untouched so `_scan_file_operations`'s verbatim citation is
  unaffected.
- `src/frob/vet/_capability.py::_matched_capabilities` -- per-needle
  dispatch to the bare-call check for `_BARE_CALL_NEEDLES` members.
- `src/frob/vet/_capability.py::_operation_entry_matches` -- same
  dispatch for the richer `_scan_file_operations` entry point.
- `design/frob.strata` -- deleted the T-0860 `waive "SYS100:eval"` clause
  on the `deploy` node now that the self-match no longer fires.
- `tests/unit/strata/test_conform_eval_needle.py` (new) -- 6 regression
  tests: identifier-suffix self-match absent for `eval(`/`exec(` at both
  the `scan_file_capabilities` and full `check_self_conformance` layers,
  a genuine bare `eval(`/`exec(` call still detected, and a real-repo
  `load_design_ids`/`merge_models`/`check_self_conformance` run (the same
  composition `run_native_sys_audit`/`frob sys audit` use) asserting zero
  self-conformance violations with the waiver gone.

Evidence: all 6 tests in `tests/unit/strata/test_conform_eval_needle.py`
pass directly under `pytest` (bound to acceptance criteria 0/1/2 above).
`tests/test_vet.py` (216 tests) and the whole `tests/unit/strata/`
directory re-run clean, no regressions. `frob sys audit` (run manually
post-fix): `selfconform: 0 violation(s), 0 waived, 0 stale waiver(s)` and
`sys audit: self-conformance PROVED -- zero SYS gaps` -- confirms
acceptance [2] with the waiver deleted.

Gates: `frob check` (chunked, `--ticket T-0882`) clean across all 5 stage
groups (lint, static, gates-fast, gates-native, gates-security) -- 0
errors in every stage after adding `frob:ticket T-0882` directives to the
4 new/changed symbols COV002 flagged and re-sweeping pre-work.

Note (process, not scope): `frob ticket evidence`/`done-report` hung
repeatedly on this ticket even after killing and retrying under a
foreground `timeout` wrapper (matches the known T-0887/T-0884-adjacent
class of bug); this Done report and the acceptance-evidence binding above
were therefore hand-written into `tickets.md` directly, verified
afterward with `frob ticket show T-0882` printing all three acceptance
criteria as `bound(...)`, matching the exact YAML shape `frob ticket
evidence --accepts` produces elsewhere in this ledger.

Filed: none (T-0884, the FROB_WORKTREE/FROB_AGENT env leak into
`frob ticket evidence`'s spawned pytest, was already filed by a prior
session and covers the adjacent hang class encountered here).
