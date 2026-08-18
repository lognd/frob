## Done report

Reproduction (both strings, per standing rule): reading `_match_waiver`
suggested the mechanism, but the AB anecdote's own rule (DUP001) does
NOT set `Violation.symref` at all in this codebase (verified: `DUP001`/
`DUP002` construct `Violation(...)` with no `symref=` kwarg), so the
symbol-exact branch never engages for it -- DUP falls through to the
file-scoped branch, which matches on file identity regardless of
qualname spelling. The real, confirmed live mismatch is C++ ARCH001:

- `frob.arch._cpp._check_long_functions` (via the shared
  `frob.lang._common._cpp_class_methods`) builds a method's symref with
  C++'s own native scope operator: `violation.symref ==
  "<path>::Foo::bar"`.
- `frob.lang._walk_c` (the DSL/graph symbol table that binds a symbol-
  bound `frob:waive` comment to its nearest enclosing symbol) always
  dot-joins qualname segments: `waiver.src == "<path>::Foo.bar"`.

Both strings printed side by side from a direct, isolated repro (see
evidence test) -- confirmed FORMATTING, not BINDING: both sides
genuinely refer to the same method, spelled two different ways by two
independently-written qualname builders.

Sweep for other currently-inert symbol-bound waivers: instrumented
`_match_waiver`'s symbol-exact branch to WARN on every near-miss (same-
file, same-rule, but non-matching symref) and ran a full, unbudgeted
`frob check --only gates -v` against this repo's entire real tree.
Result: **0** near-misses fired across the whole run (53 real gate
errors that run, none involving a waiver near-miss). Scanned: every
gate family's violations that reach `_apply_waivers`/`_match_waiver`
during a complete `--only gates` pass (every gate, not a subset) --
i.e. the full symref-carrying-violation population this repo's own code
currently produces. The C++ ARCH001 mismatch above is real but has not
yet manifested as a live inert waiver in this repo's own tree (no C++
method in this repo currently carries a symbol-bound ARCH001 waiver);
it is nonetheless the confirmed, reproducible root cause and is fixed
generically (any rule, any language, any two "::"-vs-"." spellings of
the same symbol) rather than special-cased to C++.

Fix (in scope, `src/frob/gates/_waive.py` only):
- `_match_waiver`'s symbol-exact branch now compares `_canonical_
  symref`-normalized strings (`::` collapsed to `.` on both sides before
  `==`) instead of raw `==`. `::` is never a legal identifier substring
  in any grammar frob parses, so this cannot make two genuinely
  different symbols collide -- acceptance [2]'s must-still-keep control
  is unaffected (different symbols still normalize to different
  strings).
- A violation that still finds no symbol-exact match after
  normalization, but DOES have a same-file same-rule waiver present, now
  logs a WARNING naming both raw strings instead of silently returning
  None (acceptance [1], fail-loudly per T-2391).
- The symbol-exact matching logic was split into a new helper,
  `_match_waiver_by_symref`, to keep both functions under ARCH001's own
  60-line ceiling.
- The TRUE producer-side fix -- teaching `_cpp_class_methods` frob's own
  canonical dot-joined qualname for the `symref=` it feeds, while
  keeping the `::`-spelled name only in human-facing `message=` text --
  lives in `src/frob/lang/_common.py`/`src/frob/arch/_cpp*.py`, outside
  this ticket's declared scope. Filed separately as T-2470
  (renumbers on land) per the playbook's do-not-expand-scope-silently
  rule; T-2438's consumer-side normalization stands as defense in depth
  regardless of whether/when that producer fix lands, and also covers
  any OTHER producer with the same disease not yet found.

Positive controls (both directions), verified directly against
`_match_waiver`:
- must-now-waive: `symref="x.cpp::Foo::bar"` vs `waiver.src=
  "x.cpp::Foo.bar"` (the real C++ repro shape) now matches and returns
  the waiver.
- must-still-keep: `symref="x.cpp::Foo::qux"` vs the same
  `waiver.src="x.cpp::Foo.bar"` still returns `None` -- a waiver bound
  to a DIFFERENT symbol in the same file does not suppress an unrelated
  finding.
- diagnostic: the must-still-keep case above also asserts a WARNING log
  record naming both raw strings (`x.cpp::Foo::qux` and
  `x.cpp::Foo.bar`).

Changed:
- `src/frob/gates/_waive.py::_canonical_symref` (new)
- `src/frob/gates/_waive.py::_match_waiver_by_symref` (new, split out of
  `_match_waiver`)
- `src/frob/gates/_waive.py::_match_waiver` (symbol-exact branch now
  delegates to `_match_waiver_by_symref`)

Evidence:
- `tests/test_gates.py::TestTestGate::test_match_waiver_symref_formatting_difference_still_waives`
  (designated repro: `frob ticket evidence --check-repro` confirmed
  FAILED_AT_PARENT against the test-only commit before the fix commit
  was applied)
- `tests/test_gates.py::TestTestGate::test_match_waiver_logs_diagnostic_on_genuine_symref_mismatch`
- `tests/test_gates.py::TestTestGate::test_match_waiver_different_symbol_same_file_still_not_waived`

Filed: T-2470 (producer-side C++ symref canonicalization,
renumbers on land) -- filed under "found while working T-2438" per the
playbook; not fixed here since it is outside `src/frob/gates/_waive.py`.

Gates: `frob check --ticket T-2438` clean on `src/frob/gates/_waive.py`
and `tests/test_gates.py` (0 new errors attributable to this diff; the
two remaining `tests/test_gates.py` diagnostics, DOC007/DRIFT002 at line
16468, are pre-existing T-2441 findings unrelated to this ticket's own
edits, confirmed by line/content, not touched by this diff).

### Changed
```
 src/frob/gates/_waive.py           |  98 +++++++++++++++++++++++++++++--
 tests/test_gates.py                | 116 +++++++++++++++++++++++++++++++++++++
 tickets/T-2438/ticket.md           |  21 +++++--
 tickets/T-2470/ticket.md |  75 ++++++++++++++++++++++++
 4 files changed, 300 insertions(+), 10 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestTestGate::test_match_waiver_symref_formatting_difference_still_waives` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_match_waiver_logs_diagnostic_on_genuine_symref_mismatch` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestTestGate::test_match_waiver_different_symbol_same_file_still_not_waived` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_port_selfcheck.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_port_selfcheck.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC007@tests/test_gates.py, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOCENUM001@docs/modules/gates.md, DRIFT002@tests/test_gates.py, E501@/home/logan/projects/frob/.claude/worktrees/waive-symref-series/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/waive-symref-series/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/waive-symref-series/src/frob/gates/_dup_graph_schema.py, E501@/home/logan/projects/frob/.claude/worktrees/waive-symref-series/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/waive-symref-series/src/frob/vet/_capability.py, GATERULE001@src/frob/gates/_gates_schema.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2438, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md, missing-argument@tests/unit/test_ticket_runner_land_release.py
