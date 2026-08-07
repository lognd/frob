## Done report

Changed: NormalizedCall gained `declared_raises: frozenset[str] | None`
(src/frob/arch/_normalized.py) -- the `frob:raises` declaration's parsed
value, `None` when absent, an empty `frozenset()` a distinct valid
declaration ("raises nothing"). `frob.arch._python` parses a same-line
`# frob:raises A, B` comment on a call site into that field
(`_frob_raises_declaration`, threaded via `source_lines` through
`_py_build_module`/`_py_build_class`/`_py_build_function`/
`_py_collect_body_events`; `PythonAdapter.adapt` now decodes `source`
instead of discarding it). `frob.arch._mayraise._own_base_raises` checks
`call.declared_raises` FIRST (substitutes unconditionally, including the
empty set), then a new `_STDLIB_QUALIFIED_RAISERS` table (keyed on full
dotted callee text: json.loads/json.load -> JSONDecodeError,
sqlite3.connect/sqlite3.execute -> sqlite3.Error, struct.pack/
struct.unpack -> struct.error), then falls through to the existing
`_BUILTIN_RAISERS`/same-module-lookup/UNKNOWN chain -- so any opaque
ctypes/cffi/C-extension call (not same-module, not in either curated
table) already resolves to Unknown via that existing fail-closed path;
no separate ctypes-detection code was needed for the first half of the
acceptance criterion, only the declaration substitution for the second
half. `_EXCEPTION_PARENT` gained parent links for the three new curated
exception names. docs/modules/arch.md's may-raise-resolver and
normalized-code-model sections updated to describe the extension
(scope extended to include this file, `frob ticket scope --add`,
reason recorded above -- required by AFFECT001 since both changed
symbols are `frob:doc`-anchored there).

Evidence: the 5 tests listed above, all passing
(`pytest -q tests/unit/test_arch.py` -- 244 passed). `frob test --base
main` selected touched-set python tests and passed (exit=0, 4 outcomes
recorded).

Filed: none -- no out-of-scope work discovered.

Gates: `frob check --ticket T-0689 --only prework --only scope --only
affect_drift --only sys` -- prework/scope/affect_drift clean; gate:SYS's
one error is the pre-existing worktree-native-extension-unavailable
artifact (docs/guides/agent-playbook.md section 1), unrelated to this
change. Full `frob check --ticket T-0689` gate-summary still FAILs on
gate:COV (16) / gate:DRIFT (41) -- confirmed zero hits in this ticket's
touched files (src/frob/arch/_mayraise.py, _python.py, _normalized.py,
docs/modules/arch.md); pre-existing repo-wide debt, not introduced here.
ruff-check/ruff-format/ty all clean on the touched files specifically
(whole-repo `ty`/gate:COV/gate:DRIFT failures are pre-existing and
untouched by this diff).
