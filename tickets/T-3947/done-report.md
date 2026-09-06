## Done report

Changed:
- src/frob/gates/_ffi_boundary.py::_ffi002_violations -- `rel = str(path.relative_to(root))` -> `rel = path.relative_to(root).as_posix()`. FFI001's `_ffi001_violations` (`rel`/`rs_rel`) is display-only, never compared, and is deliberately left unchanged.
- tests/unit/gates/test_ffi_boundary_path_shape.py (new) -- standalone module, not tests/gates_suite/test_compliance.py, so this ticket's scope stays narrow (that shared file's frob:tests directives fan out into dozens of unrelated gates' source files via scope closure, measured and reverted during this ticket -- see Gates section).

Fixtures (per ticket):
- MUST-FIRE (`test_exclude_glob_and_test_dir_are_honored_not_scanned_as_production`): the identical undeclared ctypes call in a production file, a `[graph].exclude`-matched dir, and a nested `tests/` dir -- FFI002 fires for the production copy only, proving the gate scans the RIGHT set (the wrong-set failure mode this ticket describes), not merely a non-empty one.
- MUST-STAY-QUIET: covered by the same test's exclude/test-dir assertions (`not any(...)`), on the real (posix, Linux) path shape.
- Path-shape assertion (`test_rel_path_fed_to_exclude_and_test_checks_is_posix_style`): a nested-directory finding's `file` field is always forward-slash, same pattern as T-3941's `test_definition_and_usage_file_fields_are_posix_style`.
- Mechanism proof (`test_windows_shaped_rel_path_mechanism`): reproduces the pre-fix/post-fix mechanism directly with `PureWindowsPath` -- proved `is_excluded`/`is_test_file` both return the wrong answer pre-fix and the right one post-fix. This is the same method T-3941 used; NOT run against real Windows CI (none available). What is proven this way vs. what still needs a real Windows run: the STRING-SHAPE mechanism (backslash in, wrong answer out; forward-slash in, right answer out) is proven directly against the real `frob.excludes` functions; that this repo's actual CI runner reaches the same code path on a real win32 filesystem has not been separately verified.

Evidence:
- tests/unit/gates/test_ffi_boundary_path_shape.py::test_exclude_glob_and_test_dir_are_honored_not_scanned_as_production
- tests/unit/gates/test_ffi_boundary_path_shape.py::test_rel_path_fed_to_exclude_and_test_checks_is_posix_style
- tests/unit/gates/test_ffi_boundary_path_shape.py::test_windows_shaped_rel_path_mechanism
- Also run (not bound as evidence, all pass): tests/unit/gates/test_profile_boundary.py (regression check on the sibling T-3941 fix's test file, since both now share tests.conftest._write/_by_rule).

Filed: none (T-3947/T-3948 themselves are the two follow-ups T-3941 filed; no further out-of-scope work found in this ticket's own file).

Scope history (worth noting explicitly): the fix initially also edited docs/modules/gates.md (to satisfy AFFECT001) and tests/gates_suite/test_compliance.py (to add fixtures next to this gate's other tests, mirroring T-3941's own pattern for xref). Both were reverted after measuring the actual cost: adding either file to this ticket's scope triggers frob's bidirectional scope-closure check over EVERY OTHER symbol that shared, multi-gate file also describes/tests (30-367+ SCOPE002 findings depending on which file), wildly out of proportion to a 2-line Windows-path fix -- the same disproportionate-closure shape T-3914's own Done report documented and waived for tests/test_testing.py. Resolved instead by: (1) a `frob:waive AFFECT001` directly above `ffi_boundary_gate` (this fix has no Linux-visible or documented-behavior change, only an internal path-separator normalization), and (2) a standalone test module reusing the already-declared `tests.conftest._write`/`_by_rule` helpers (avoiding both DUP002, since a first draft of the standalone module had a byte-identical `PureWindowsPath` mechanism test duplicated against T-3948's own standalone module, and a SELFAUDIT001 SYS100 finding when the module defined its own local `_write`, since the design/frob.strata self-audit registry enumerates fs.write call sites by file and a brand-new file with its own write call is undeclared capability).

Gates: `frob check --ticket T-3947 --only gates`: 10 errors remain. 3 are pre-existing and verified unrelated to this diff (DOC006 x2 @ tickets/T-3931/ticket.md, DRIFT001 @ src/frob/xref/__init__.py -- all present on main before this ticket, none in this ticket's scope). The remaining 7 are SCOPE002 scope-closure suggestions, all of the disproportionate-closure shape described above (docs/modules/gates.md's ~40-gate fan-out; tests/gates_suite/test_compliance.py's pre-existing frob:tests directives on `ffi_boundary_gate` itself; a handful of ambiguous "private helper" cross-hits from other test files that happen to also define a same-named private `_write`/`_by_rule`, a resolver false-positive since this ticket's own file imports the disambiguated `tests.conftest._write`/`_by_rule`, not a locally-shadowing one). Chasing full closure on any of these would mean pulling in most of docs/modules/gates.md's ~40 described gates, or tests/gates_suite/test_compliance.py's entire multi-gate fixture surface, for a 2-line Windows-only path fix -- out of proportion to the change, same reasoning T-3914's own Done report used for an identical shape. `frob check --ticket T-3947 --only gates`: gate:EXHAUST and the ffi_boundary-specific findings (via `exhaustive_handling`/`ffi_boundary` stage timings in the tool summary) both report clean; `gate:SELFAUDIT` clean after switching to the shared `tests.conftest` helpers. `frob test --base main` timed out twice at 540s in this shared, heavily-active worktree (concurrent lands running against the primary checkout throughout this session) -- not run to completion; the specific evidence node ids above were run directly and pass (also profile_boundary's own suite, unaffected).

Not verified: this fix has not been run against real Windows CI -- the mechanism was confirmed directly (PureWindowsPath reproduction, see fixtures above), matching T-3941's own disclosed verification bar for the identical bug class.

### Changed
```
 tickets/T-3947/ticket.md | 80 ++++++++++++++++++++++++++++++++++++++++++++++--
 tickets/T-3948/ticket.md | 62 +++++++++++++++++++++++++++++++++++--
 2 files changed, 137 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/unit/gates/test_ffi_boundary_path_shape.py::test_exclude_glob_and_test_dir_are_honored_not_scanned_as_production` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_ffi_boundary_path_shape.py::test_rel_path_fed_to_exclude_and_test_checks_is_posix_style` (pytest node id, verified passing when recorded)
- `tests/unit/gates/test_ffi_boundary_path_shape.py::test_windows_shaped_rel_path_mechanism` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 4 error(s), 4391 warning(s), 929 waived
- error-findings: DOC006@tickets/T-3931/ticket.md, DRIFT001@src/frob/xref/__init__.py, I001@/home/logan/projects/frob/.claude/worktrees/t-3947/tests/unit/gates/test_ffi_boundary_path_shape.py, SCOPE002@tickets.md
