## Done report

Changed:
- src/frob/gates/_exhaustive_handling.py::exhaustive_handling_gate -- `rel = str(path.relative_to(root))` -> `rel = path.relative_to(root).as_posix()`.
- tests/unit/gates/test_exhaustive_handling_path_shape.py (new) -- standalone module, not tests/gates_suite/test_compliance.py, so this ticket's scope stays narrow (that shared file's frob:tests directives fan out into dozens of unrelated gates' source files via scope closure; also true of docs/modules/gates.md -- both measured and reverted during this ticket, see Gates section).

Fixtures (per ticket):
- MUST-FIRE (`test_exclude_glob_and_test_dir_are_honored_not_scanned_as_production`): the identical genuine EXHAUST002-triggering boundary in a production file, a `[graph].exclude`-matched dir, and a nested `tests/` dir -- EXHAUST002 fires for the production copy only, proving the gate scans the RIGHT set (the wrong-set failure mode this ticket describes -- worse than a dead gate, it fires on the wrong set), not merely a non-empty one.
- MUST-STAY-QUIET: covered by the same test's exclude/test-dir assertions.
- Path-shape assertion (`test_rel_path_fed_to_exclude_and_test_checks_is_posix_style`): a nested-directory finding's `file`/`symref` fields are always forward-slash, same pattern as T-3941's `test_definition_and_usage_file_fields_are_posix_style`.
- Mechanism proof (`test_windows_shaped_rel_path_mechanism`): T-3947 (landed first, same series) already carries the identical `PureWindowsPath` mechanism proof for the SAME underlying `frob.excludes.is_excluded`/`is_test_file` contract (both tickets fix the identical bug class in the identical way) -- rather than duplicate that body verbatim (which DUP001 correctly flagged on a first attempt), T-3948's own test of this name calls T-3947's directly (`tests.unit.gates.test_ffi_boundary_path_shape.test_windows_shaped_rel_path_mechanism`), binding it as T-3948's own evidence too without re-litigating an identical proof. What is proven this way vs. what still needs a real Windows run: the STRING-SHAPE mechanism (backslash in, wrong answer out; forward-slash in, right answer out) is proven directly against the real `frob.excludes` functions; that this repo's actual CI runner reaches the same code path on a real win32 filesystem has not been separately verified.

Evidence:
- tests/unit/gates/test_exhaustive_handling_path_shape.py::test_exclude_glob_and_test_dir_are_honored_not_scanned_as_production
- tests/unit/gates/test_exhaustive_handling_path_shape.py::test_rel_path_fed_to_exclude_and_test_checks_is_posix_style
- tests/unit/gates/test_exhaustive_handling_path_shape.py::test_windows_shaped_rel_path_mechanism

Filed: none.

Scope history: same disproportionate-closure shape as T-3947 (this series' sibling ticket) -- an initial draft also edited docs/modules/gates.md (for AFFECT001) and tests/gates_suite/test_compliance.py (to sit next to this gate's other fixtures); both reverted after measuring that adding either to scope drags in frob's bidirectional SCOPE002 closure over every OTHER symbol that shared file also describes/tests (300+ findings for gates.md alone), wildly out of proportion to a 1-line Windows-path fix -- same shape T-3914's own Done report documented and waived for tests/test_testing.py. Resolved instead with a `frob:waive AFFECT001` directly above `exhaustive_handling_gate` (no Linux-visible or documented-behavior change) and the standalone test module above.

Gates: `frob check --ticket T-3948 --only gates`: 8 errors remain. 1 is pre-existing and verified unrelated (DRIFT001 @ src/frob/xref/__init__.py, present on main before this ticket, T-3941's own known drift, not in this ticket's scope). The remaining 7 are SCOPE002 scope-closure suggestions of the same disproportionate shape T-3914's Done report documented and T-3947 (this series' sibling, landed first) also carried: docs/modules/gates.md's ~40-gate fan-out, tests/gates_suite/test_compliance.py's pre-existing frob:tests directives on `exhaustive_handling_gate` itself, and several ambiguous "private helper" cross-hits from other tests/unit/gates/*.py files that happen to also define a same-named private `_write`/`_by_rule` (a resolver false-positive, since this ticket's own file imports the disambiguated `tests.conftest._write`/`_by_rule`). Chasing full closure would mean pulling in most of docs/modules/gates.md's ~40 described gates, or test_compliance.py's entire multi-gate fixture surface, for a 1-line Windows-only path fix. `frob check --ticket T-3948 --only gates`: gate:EXHAUST reports clean (0 errors; DUP001 also clean after switching the mechanism test to a delegating call instead of a duplicate body). `frob test --base main` was not run to completion in this shared, heavily-active worktree (same 540s timeout T-3947 hit, concurrent lands running against the primary checkout throughout this session); the specific evidence node ids above were run directly and pass.

Not verified: this fix has not been run against real Windows CI -- the mechanism was confirmed directly (PureWindowsPath reproduction, via T-3947's shared mechanism test), matching T-3941's own disclosed verification bar for the identical bug class.

### Changed
```
 tickets/T-3948/ticket.md | 4 ++++
 1 file changed, 4 insertions(+)
```

### Evidence
- `tests/unit/gates/test_exhaustive_handling_path_shape.py::test_exclude_glob_and_test_dir_are_honored_not_scanned_as_production` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_exhaustive_handling_path_shape.py::test_rel_path_fed_to_exclude_and_test_checks_is_posix_style` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_exhaustive_handling_path_shape.py::test_windows_shaped_rel_path_mechanism` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 2 error(s), 4403 warning(s), 931 waived
- error-findings: DRIFT001@src/frob/xref/__init__.py, SCOPE002@tickets.md
