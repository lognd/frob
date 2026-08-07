## Done report

Changed:
- src/frob/vet/_capability.py: removed the bare `"compile("` needle from
  the Python `eval` pattern table (it substring-matched `re.compile(`/
  `ast.compile(` everywhere in the repo -- confirmed via direct grep that
  every non-self hit for that needle was a dotted `re.compile(` call, zero
  bare builtin `compile(` calls anywhere in src/frob). Added
  `_has_bare_compile_call` (dot-exclusion text scan, still no AST) wired
  through a new `_SPECIAL_CHECKS` table so `compile(` only counts as
  "eval" when it is NOT a dotted method access. Added `_is_self_path` /
  `_SELF_PATH` so `scan_directory_capabilities` excludes this module's own
  file from directory aggregation (its `_PATTERNS` table is guaranteed to
  contain every needle as literal data). `scan_file_capabilities` called
  directly on this file is unaffected and still exhibits the accepted
  false-positive class, now documented in the module docstring and
  docs/modules/vet.md rather than silently eaten.
- tests/test_vet.py (TestCapabilityScan): 5 new regression tests --
  `re.compile(`/`ast.compile(` alone no longer report "eval"; a genuine
  bare `compile(source, ...)` call still does; genuine `eval(...)` still
  does; scanning `_capability.py` directly still shows the documented
  self-match (locks the accepted-behavior decision either way, per
  ticket instructions); `scan_directory_capabilities` over the real
  `src/frob/vet` path no longer reports "eval"/"exec" (it still reports
  "install-hook" from `_ecosystem.py`'s genuine `"cmdclass" in text`
  check -- a SEPARATE, documented false positive this ticket's cheap
  self-exclusion does not and cannot cheaply fix; asserted explicitly,
  not silently ignored).
- docs/modules/vet.md: new "Self-match false positives (T-0151)"
  paragraph in "Honest limits" documenting the accepted false-positive
  class per the ticket's design constraint (b) -- full AST-based
  precision was explicitly out of scope.

Scope extension (written justification, per ticket instructions):
- design/frob.strata: removed `may "eval";` from the `gates` node. Fixing
  the `compile(` needle changed real observed capabilities -- `frob sys
  audit` immediately fired SYS101 (`eval declared but never observed on
  gates`) after the code fix, since `gates`'s only "eval" evidence was
  always `re.compile(` calls (_FRONTMATTER_RE, _AD_ID_RE, _TODO_RE, etc,
  all regex; confirmed zero real eval/exec/dynamic-import anywhere under
  src/frob/gates/** by direct grep). Leaving the stale `may "eval"` would
  make the ticket's own fix regress self-conformance, which the ticket
  text explicitly puts in scope ("Updating design/frob.strata's may
  declarations ... to the new honest observations is IN SCOPE"). No
  other node's `may "eval"`/`may "exec"` changed: cli (src/frob/app.py's
  `importlib.import_module(`), graphlang (src/frob/lang/_walk_strata.py's
  `importlib.import_module(`), core (src/frob/dup/_pipeline.py's
  `model.eval(`, src/frob/fuzz/_signatures.py's `importlib.import_module(`)
  all still have genuine, non-`compile(` eval-pattern hits -- re-measured
  directly via `scan_directory_capabilities`/grep, not assumed.
- docs/modules/vet.md, tests/test_vet.py, tickets.md: natural homes for
  the documented-limits paragraph, the regression tests, and this Done
  report/evidence/scope record; all three were already implicitly
  expected by the ticket's own text (the ticket names docs/modules/vet.md
  explicitly as the fallback if precision isn't cheaply achievable, and
  ticket evidence/state live in tickets.md by construction).
- tests/golden/frob_export_seccomp.json and
  tests/system/test_frob_self_model.py were NOT touched: both were
  re-run after the design/frob.strata change and neither needed
  regeneration -- `gates`'s exported syscall set is a strict subset of
  what cli/graphlang/core/vet already export for "eval", so dropping one
  node's redundant `may "eval"` did not change the union the exporter
  renders (verified: `git diff --stat` against both files is empty after
  running `uv run pytest -q tests/unit/strata/test_export_golden.py
  tests/system/test_frob_self_model.py`, both green).

Real measured numbers (2026-07-18, `uv run frob sys audit` / direct
`scan_file_capabilities`/`scan_directory_capabilities` calls, this
worktree's `src/frob/`, NOT the stale global `frob` -- see T-0150's
tooling finding, same caveat applies here):
- Before fix: `gates` node's `may "eval"` was satisfied only by
  `re.compile(` hits (12 call sites across src/frob/gates/__init__.py
  and decisions.py/invariants.py); zero genuine eval/exec-adjacent code.
- After fix: `scan_directory_capabilities(src/frob/gates)` no longer
  reports "eval"; `scan_directory_capabilities(src/frob/vet)` no longer
  reports "eval"/"exec" but still reports "install-hook" (documented,
  separate false-positive source, `_ecosystem.py`).
- `uv run frob sys audit`: exit 0, PROVED across all 8 configured views;
  self-conformance PROVED, 0 SYS gaps (confirmed both before-fix failure
  -- 1 SYS101 violation on `gates` -- and after-fix clean state).

Evidence: the 5 node ids attached via `frob ticket evidence T-0151`; all
pass (`uv run pytest -q tests/test_vet.py::TestCapabilityScan`, 12/12).

Filed: none (no out-of-scope work found beyond what was already filed
against T-0151 itself).

Gates (measured via `uv run frob ...`, this worktree's build):
- `uv run frob check --ticket T-0151`: `pass gates 96 violation(s), 67
  waived` -- zero unwaived violations attributable to any file this
  ticket touches (grepped the unwaived set line-by-line for every
  changed filename: the only hit, tests/test_vet.py:598 PERF003, is a
  pre-existing nested-loop warning in `TestEcosystemRules`, several
  hundred lines away from and unrelated to this ticket's additions,
  which start at TestCapabilityScan's new tests appended after line 389;
  every other unwaived violation is TEST002/TEST003/TEST006/PERF00x
  against files this ticket never touched).
- `uv run frob sys audit`: exit 0, PROVED across all 8 configured views
  + self-conformance (0 SYS gaps).
- `uv run ruff check` / `ruff format --check` / `uv run ty check`: clean
  on src/frob/vet/_capability.py and tests/test_vet.py.
- `uv run pytest -q tests/test_vet.py tests/unit/strata/
  tests/system/test_frob_self_model.py`: all pass (no count regression).
- `uv run frob test --base main` (touched-set): exit 0, python suite
  selected and passing.
