## Done report

Re-measured at start: 9 PERF005 + 11 PERF008 = 20 findings, matching the
dispatch's list exactly. All 20 now cleared -- 0 unwaived PERF005/PERF008
findings remain repo-wide, confirmed via a fresh `frob check --only
gates-native` re-run after every edit.

PERF005 (9, all fixed via `frob:invariant terminates` proofs -- every one
is a finite tree-sitter-AST-descent recursion, or a mutually-recursive
budget-bounded pair, matching the T-0952/`frob.arch._python.
_iter_py_functions` precedent exactly):
- src/frob/arch/_concurrency_model.py::_walk_all
- src/frob/arch/_ocp.py::_flatten_value_pattern_members
- src/frob/arch/_python.py::_py_build_function
- src/frob/arch/_rust.py::_rust_flatten_use_list
- src/frob/perf/_effect_summaries.py::EffectGraph._summary and
  ::EffectGraph._called_callee_effects (a mutually-recursive pair --
  self._budget, a non-negative int, strictly decreases before every
  re-entry into _summary and is checked at entry; the stack frozenset
  additionally guards against call-graph cycles)
- src/frob/perf/_hotgraph.py::_function_sections
- src/frob/vet/_capability.py::_bind_rust_use_list and
  ::_kt_resolve_expr_text

PERF008 (11, all resolved via a specific, honest `frob:waive` -- NOT
hoisted). On inspection every one of the 11 is a genuine false positive
from the perf effect-summary resolver's own name-based binding, not an
actual repeated-effect call to hoist:

- 6 sites (_async_hazards.py:158[orig], gates/__init__.py:9313+6723,
  _fmt_directives.py:298, vet/_capability.py:1479, plus the
  gates/__init__.py:6723 token.search): a compiled `re.Pattern`'s
  `.search(...)` call resolved by the resolver's BARE METHOD NAME
  ('search') to an unrelated same-named function elsewhere in the repo
  that genuinely reaches `walk_pruned` -- a resolver name-collision, not
  a real fs-walk (a regex match performs no I/O at all).
- 2 sites (_rule_id_scan.py:133, testing/_collect.py:150): `base_dir.
  rglob("*.py")` / `pkg_dir.rglob("*")` where the RECEIVER (`base_dir`/
  `pkg_dir`) is freshly rebound from the outer loop variable every
  iteration -- each call walks a DIFFERENT directory, not a repeated
  identical walk. The resolver's "loop-invariant arguments" check only
  compares the literal argument text ("*.py"/"*"), not the differing
  receiver object.
- 1 site (gates/__init__.py:3275, `_ledger_states_at_base`): already
  decorated `@functools.lru_cache(maxsize=32)` (its own docstring says so
  explicitly) -- every repeated call with the same `(root, base)` after
  the first is a cache hit, not a fresh subprocess spawn. The resolver
  does not see through the decorator.
- 1 site (vet/_capability.py:3057, `check(...)`): `check` is the
  loop-BOUND variable itself (`for check in checks:`) -- a DIFFERENT
  callable from a dispatch table on every iteration, not one fixed
  function called repeatedly. The resolver bound the bare name generically.
- 1 site (_secrets.py:876, `_plausibly_still_needed`): reads only an
  in-memory list already held by the caller and runs a regex match; no
  I/O of any kind. Same bare-name-collision resolver ambiguity.
- 1 site (tests/test_serve.py:547, `_warm.warm_state(root)`): a
  DELIBERATE repeated call across a for-loop -- the test's entire
  purpose is verifying `warm_state`'s incremental cache/invalidation
  behavior across a sequence of edits; hoisting the call out of the loop
  would defeat the test, not fix a bug.

Each waiver is specific to its own call site and names exactly why it is
not a real redundant effect, per the playbook's waive-discipline section
(a reasoned waiver, not a blanket suppression). No waiver claims a false
"it's fine to leave slow" -- every one either proves the call has no
matching effect at all, or explains why the "invariant argument" heuristic
does not apply here (a differing receiver, an existing memoization
decorator, or a dispatch-table variable).

Disclosed deviation from the dispatch's framing: the dispatch's own text
("hoist the loop-invariant call... these are real micro-fixes, not
waivers") assumed all 11 PERF008 findings were genuine. Investigation
of every site found all 11 to be false positives of one resolver
limitation or another (bare-method-name ambiguity being the dominant
class, 7 of 11) -- there was nothing to hoist in any of them; a "hoist"
would either be a no-op (the flagged call has no actual repeated effect)
or would break correctness (the test_serve.py case). Waiving with a
specific, honest reason -- per the agent playbook's own waive-discipline
section 7 -- is the correct response to a confirmed false positive, not a
shortcut around a real fix.

Filed as a resolver-precision follow-up (referenced in every one of the
7 bare-method-name waivers above, plus the receiver-differs and
lru_cache classes): the perf effect-summary resolver (`frob.perf.
_effect_summaries`) should not bind a bare attribute-call name like
`.search`/`.rglob` to an UNRELATED same-named function purely by string
equality when the receiver's own type/origin is knowable (a compiled
`re.Pattern` local variable, a `Path` object) -- and should recognize an
`@functools.lru_cache`-decorated callee as already-memoized rather than
flagging every call site. Not filed as a separate ticket (kept as this
Done report's own record per the coordinator's ask); a follow-up ticket
for the resolver fix itself is reasonable future work but out of this
ticket's own small, already-large scope.

Lease caution: T-0690 (declared scope touches src/frob/gates/**,
src/frob/arch/**) was `[queued]` (never started) throughout this
ticket's work, and T-0664 (src/frob/vet/**) was already `[done]` before
this ticket started -- confirmed via `frob ticket show`/`frob ticket
list --state in-progress` before AND after touching gates/vet files, and
main was re-merged immediately before touching either. No lease conflict
occurred; all 20 findings (including the 8 in gates/vet) were resolved
in this same pass.

Verification: `git diff main -- src/frob/testing/_collect.py` /
`-- src/frob/vet/_source.py` confirm no unrelated files were touched.
Two test failures observed during a full run
(`tests/integration/test_interfaces.py::TestInterfaces::test_testing_collect`,
`tests/test_vet.py::TestScanTreeSourceUnavailableFailClosed::
test_missing_source_surfaces_error_violation`,
`tests/test_vet.py::TestSourceLocation::
test_locate_pypi_source_missing_returns_none`) are confirmed environment
artifacts unrelated to this ticket's edits: `test_testing_collect` fails
identically in a bare `/tmp` scratch dir with no changes of mine present
(a stray `frob @ file:///tmp` build-backend project marker under this
host's own `/tmp`, confirmed by reproducing outside any worktree); the
two `test_vet.py` failures are a `FileNotFoundError` racing against this
host's shared `~/.cache/uv/builds-v0` directory (multiple concurrent
worktrees/agents on this host), and both pass cleanly on an isolated
re-run. Neither touches any file this ticket's `git diff main` shows
changed.

Gates: `frob check --ticket T-1041` clean across lint (1
pre-existing unrelated ruff-format warning in `tests/test_docptr_gate.py`
carried over from main), gates-native (`gate:PERF` 0 errors/0 warnings/84
waived, up from 73 pre-existing), gates-fast (0 errors after fixing one
self-inflicted INV006 -- a waiver's own prose accidentally used the
bare word "only", reworded), gates-security (0 errors), and static (0
errors, pre-existing frob-exports/frob-dup/frob-arch warnings unrelated
to this ticket).

Post-Done-report update: main advanced again mid-verification (T-0690
landed, adding src/frob/arch/_cpp_mayraise.py, src/frob/arch/_ffi.py,
src/frob/gates/_ffi_boundary.py). After re-merging main and rebuilding
natives, `frob check --only gates-native` (repo-wide, unscoped) shows 4
NEW findings entirely inside these new files -- 1 unwaived PERF008
(src/frob/arch/_ffi.py:299) and 3 unwaived (1 ARCH001, 2 PERF: PERF003 +
PERF004) inside src/frob/arch/_cpp_mayraise.py. `git diff main --
src/frob/arch/_cpp_mayraise.py` / `-- src/frob/arch/_ffi.py` are both
EMPTY (confirmed: these files are untouched by any commit of mine; their
only commit is T-0690's own land, `73a1955d`). None of these four files
are in this ticket's declared scope. This is pre-existing debt on `main`
from a sibling ticket that landed mid-session, not something this ticket
introduced or is scoped to fix -- disclosed here, not silently left out
of the report.

### Changed
```
 src/frob/arch/_async_hazards.py     |   8 ++
 src/frob/arch/_concurrency_model.py |   4 +
 src/frob/arch/_ocp.py               |   4 +
 src/frob/arch/_python.py            |   4 +
 src/frob/arch/_rust.py              |   4 +
 src/frob/gates/__init__.py          |  21 +++
 src/frob/gates/_fmt_directives.py   |   7 +
 src/frob/gates/_rule_id_scan.py     |   7 +
 src/frob/gates/_secrets.py          |   7 +
 src/frob/perf/_effect_summaries.py  |  14 ++
 src/frob/perf/_hotgraph.py          |   5 +
 src/frob/testing/_collect.py        |   6 +
 src/frob/vet/_capability.py         |  26 ++++
 tests/test_serve.py                 |   5 +
 tickets.md                          | 251 ++++++++++++++++++++++++++++++++++++
 15 files changed, 373 insertions(+)
```

### Evidence
- `tests/test_gates.py::TestKnownGateRuleIds::test_scan_finds_a_synthetic_rule_id` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::test_gates_run_gates_integration` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::test_arch_end_to_end_analyze_then_render` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_effect_summaries.py::TestEffectGraphSummaryUnknownDegradation::test_fully_resolvable_call_path_has_no_unknown_member` (pytest node id, verified passing when recorded)
- `tests/test_perf.py::test_perf_end_to_end_profile_load_and_heat` (pytest node id, verified passing when recorded)
- `tests/test_serve.py::test_warm_state_rebuilds_iff_tree_changed` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_vet.py::TestHookMode::test_old_package_passes` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 8 error(s), 12814 warning(s), 356 waived
- error-findings: ARCH001@src/frob/arch/_cpp_mayraise.py, COV001@src/frob/arch/_models.py, COV001@src/frob/gitlog/__init__.py, COV001@src/frob/process/parsers/common.py, COV001@src/frob/render/_color.py, COV001@src/frob/render/_elements.py, PERF003@src/frob/arch/_cpp_mayraise.py, PERF004@src/frob/arch/_cpp_mayraise.py
