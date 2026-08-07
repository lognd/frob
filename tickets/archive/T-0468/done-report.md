## Done report

CONFIRMED: the Python resolver had the same order-insensitivity soundness
hole T-0378 fixed in Rust. `_shadowing_scope`/`_py_scope_bound_names`
collected every name bound ANYWHERE in the enclosing scope into a plain
`set[str]`, with no byte-position tracking, so a capability call textually
BEFORE a same-name rebind was wrongly treated as already shadowed and the
real dangerous call silently dropped (repro:
`import os as o\no.system('ls')\no = None` scanned to `frozenset()`,
should be `{"exec"}`; verified failing before the fix).

Fix mirrors T-0378 round 2's Rust shape: `_py_scope_bound_names` now
returns `dict[name -> shadow-onset byte position]` instead of a bare set
(new `_PY_ALWAYS_SHADOWS = -1` sentinel + `_record_py_binding` helper,
mirroring `_RUST_ALWAYS_SHADOWS`/`_record_rust_binding`); parameters and
nested `def`/`class` names always shadow (in scope for the whole body
regardless of position); assignment/`for`/`with ... as`/walrus targets now
record the BINDING NODE's own `start_byte` (via `_collect_target_names`'s
new `position` parameter) instead of joining an unordered set.
`_shadowing_scope` only treats a binding as shadowing a given call site
when `site.start_byte >= that position`, same as `_rust_shadowing_scope`.
Every `scope_cache: dict[int, frozenset[str]]` annotation in the Python
resolver section (lines ~733-922) updated to `dict[int, dict[str, int]]`
to match; the TS resolver's own (separate, out-of-scope) shadow check at
line 1214+ is untouched.

Verified against the ticket's exact repro (`import os as o;
o.system('ls'); o = None` now returns `{"exec"}`, was `frozenset()`); the
reverse order (`o = None` before the call) still correctly returns
nothing. 2 new ordering regression tests added
(test_call_before_rebinding_still_detected /
test_call_after_rebinding_still_not_detected, aliased-import form so the
raw-text lexical pass cannot mask a resolver regression); all 118
pre-existing TestCapability* tests in tests/test_vet.py still pass
(shadow/rebind/alias-table guarantees T-0328/T-0337 locked unchanged);
full tests/test_vet.py (162 tests) passes.

Evidence (2 of 2): test_call_before_rebinding_still_detected (the
soundness property), test_call_after_rebinding_still_not_detected (no
regression to unconditional permissiveness).

Filed: none (no out-of-scope defects found; TS/Rust/C-C++ resolvers are
each independently maintained and out of this ticket's scope).

Gates: `frob check --ticket T-0468` -- 0 findings attributable to
src/frob/vet/_capability.py or tests/test_vet.py; the reported 3
errors/85 warnings/1 ty diagnostic are pre-existing, unrelated to this
change (DRIFT002 on tests/test_tickets_evidence_cli.py, dup/arch findings
elsewhere in the tree, a pre-existing ty missing-argument diagnostic in
tests/unit/strata/test_threat.py). `frob test --base main` -- touched-set
selection (tests/system/test_cli_vet.py::TestHookMode::test_old_package_passes,
tests/test_vet.py) passes, exit=0. NOT closed (review-gated per dispatch
instructions).
