## Done report

Changed: reconciled the `frob:raises` name collision between T-0688 and
T-0689 by keeping `frob:raises` for the ABOVE-THE-DEF, function-wide
declared-propagation directive `EXHAUST002` consumes
(`src/frob/gates/_exhaustive_handling.py`, untouched by this ticket) and
renaming T-0689's SAME-LINE, call-site directive
(`NormalizedCall.declared_raises`) to `frob:callee-raises` everywhere it
is spelled, parsed, or documented:

- `src/frob/arch/_python.py` -- `_FROB_RAISES_RE` regex literal,
  `_frob_raises_declaration` docstring/comments, and every other
  `frob:raises` mention describing this same-line form now read
  `frob:callee-raises`.
- `src/frob/arch/_normalized.py` -- `NormalizedCall.declared_raises`
  field docstring updated to the new spelling.
- `src/frob/arch/_mayraise.py` -- module docstring and
  `_own_base_raises`/priority-order comments describing the call-site
  substitution updated to the new spelling.
- `tests/unit/test_arch.py` -- the two tests exercising the call-site
  form (`TestPythonAdapter::test_adapt_parses_frob_raises_declaration_on_call_line`,
  `TestMayRaiseResolver::test_declared_raises_substitutes_for_opaque_boundary_call`)
  now write `# frob:callee-raises ...` in their fixture source and their
  own comments/docstrings describe the rename; test METHOD NAMES were
  deliberately left unchanged (they are bound as evidence on the already
  CLOSED ticket T-0689 -- renaming the qualname would break that
  ticket's historical evidence for no benefit).
- `docs/modules/arch.md` -- the "Opaque boundaries and `frob:raises`
  declarations" section renamed/updated to `frob:callee-raises` with a
  new "Naming note (T-0931)" paragraph explaining the split and how
  T-0690's planned FFI-boundary declarations will extend the ABOVE-THE-DEF
  form, not this one; the `NormalizedCall` table row in the
  normalized-code-model section updated to match.
- `docs/modules/gates.md` -- added a "Naming note (T-0931)" paragraph
  directly under EXHAUST002's declared-propagation-directive description
  clarifying `frob:raises` is now the SOLE owner of that verb text and
  cross-referencing the renamed sibling.

Convention chosen and why: T-0690 (open, reads compatible) explicitly
plans its FFI-boundary declarations to mirror `frob:deprecated`'s
above-the-def placement -- i.e. the SAME shape as T-0688's function-wide
directive, not T-0689's call-site one. Keeping `frob:raises` on the
function-wide form and renaming only the call-site form (rather than
inventing a brand-new name for both, or unifying on position-based
disambiguation) minimizes churn: EXHAUST002 is the only current CONSUMER
of the function-wide form and needed zero code changes; T-0690's future
work needed zero convention changes; only T-0689's freshly-landed,
narrower call-site feature needed a rename. Position-based
disambiguation alone (same verb, infer meaning from placement) was
rejected as the ticket itself calls for -- it is exactly the ambiguity
being reconciled: a human or tool reading `# frob:raises X` mid-file
cannot tell which grammar applies without also knowing this repo's own
convention-of-conventions, whereas two distinct verb texts are
self-describing at the point of use.

Scope: extended via `frob ticket scope --add` to include
`docs/modules/arch.md`, `docs/modules/gates.md`, `tests/unit/test_arch.py`,
`tests/test_gates.py` (reason recorded on the ticket) -- the ticket's
declared `scope` (`src/frob/arch/**`, `src/frob/gates/**`) did not cover
the docs/tests half of "update ... all existing directive occurrences in
the repo ... the DSL documentation ... and tests on both sides" the
ticket explicitly asks for.

Filed: T-0944 (bug) -- a genuine, reproducible self-deadlock in
`frob check` discovered while trying to verify this ticket: the `frob
check --only <anything>` process opens `.frob/derived.lock` twice in the
SAME process and blocks forever trying to acquire an exclusive lock on
one fd while it still holds a shared lock on the other (confirmed via
`/proc/<pid>/fd` + `/proc/locks` showing the identical pid holding both a
READ flock and a pending WRITE flock on the same inode). Reproduced
against two different `--only` gate selections (`scope`, `prework`) in
this worktree -- not gate-specific. `src/frob/process/_lock.py` is
outside T-0931's scope, so not fixed here; filed instead, with the
`/proc` evidence and a suggested fix direction in the ticket body.

Evidence: this bug made `frob check --ticket T-0931 --only ...`
completely unusable in this worktree for verification, so evidence here
is pytest + ruff + ty directly, plus a manual deletion-filter check:

- `pytest -q tests/unit/test_arch.py` -- 249 passed (whole file, includes
  both renamed call-site tests).
- `pytest -q tests/test_gates.py -k "ExhaustiveHandling or ErrorsAsValues"`
  -- 9 passed (confirms the untouched, function-wide `frob:raises` /
  EXHAUST002 path still works unchanged).
- `pytest --collect-only tests/unit/test_arch.py -n0 | grep -i raises` --
  confirms all bound evidence node ids below actually collect.
- `ruff check` / `ruff format --check` clean on every touched `.py` file
  (`src/frob/arch/_python.py`, `src/frob/arch/_normalized.py`,
  `src/frob/arch/_mayraise.py`, `tests/unit/test_arch.py`).
- `ty check` clean on the three touched `src/frob/arch/*.py` files.
- `git diff main --diff-filter=D --stat` -- empty (no unintended
  deletions carried forward from a stale merge base).
- One PRE-EXISTING, UNRELATED failure observed and NOT caused by this
  change: `tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known`
  fails citing `PARSE002` (from `src/frob/gates/_parse_failures.py`,
  landed by T-0905, a file this ticket never touches) -- confirmed
  unrelated by file/symbol, not investigated further as out of scope.

Gates: `frob check` COULD NOT BE RUN against this ticket -- every
`--only` invocation self-deadlocks per the filed bug above (T-draft-
851603e2). Substituted the pytest/ruff/ty verification above and the
manual deletion-filter check per playbook section 9. This is a
disclosed, honest gap, not a silent skip: the standard gate-verification
step for this ticket is currently blocked by an environmental bug
outside its scope.
