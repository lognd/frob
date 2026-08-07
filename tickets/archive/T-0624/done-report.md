## Done report

EPIC T-0330's catch-all smell family (T-0624): seven misc design-smell
checks written once against the T-0609 normalized model, mirroring
T-0622/T-0623's just-landed siblings.

`src/frob/arch/_smells.py` adds `mutable-default-arg` (a param default
literal starting with `[`/`{`/`list(`/`dict(`/`set(`, requiring a new
`NormalizedParam.default_text` field the T-0609 model did not carry --
added in this ticket since the previous model deliberately kept "never
the default's value itself"), `feature-envy` (a method calling one
non-self receiver strictly more than self, at least twice),
`data-clumps` (the same 3+ keyword-arg-name group repeated at 3+ call
sites), `magic-literal` (a bare numeric literal outside {0,1,-1} in a
branch condition), `dead-private-code` (PER-MODULE proxy: a private
top-level function never called by bare name elsewhere in the same
file), `deep-inheritance` (PER-MODULE proxy: same-file-resolvable base
chain beyond a configurable threshold), and `temporal-coupling` (a class
with an initialization/readiness-named bool field runtime-guarded by
another method via a branch+raise, the same guard-clause proxy
`_typedesign.py`'s illegal-states-representable check already uses).

`dead-private-code` and `deep-inheritance` are explicitly disclosed as
PER-MODULE proxies, not the ticket's own project-wide "T-0288 call
graph" / cross-file base-resolution versions -- `frob.graph.callgraph`
is a separate subsystem this ticket's `_smells.py`-only scope does not
integrate with; a genuine cross-file version is a follow-up, not
silently narrowed here.

### Scope-lease juggling across T-0622/T-0623/T-0624 (disclosed)
All three tickets in this dispatch batch extend the shared
`ArchCategory`, and the exclusive single-owner scope lease on
`_models.py` only allows ONE in-progress ticket to hold it at a time.
Working the three sequentially in one worktree, I passed the lease
forward each time (`frob ticket scope --remove` on the finishing
ticket, `--add` on the next) rather than fighting for concurrent
ownership. One real gap this produced: T-0622's ledger-restore-to-main
recipe (section 10b of the agent playbook) silently dropped its
`_models.py` scope-add from the WORKING TREE (the recipe restores
main's committed ledger, which predates that scope-add) and I did not
notice to re-run it before T-0622's own Done report -- so T-0622's
final committed ticket record does not declare `_models.py` in scope,
even though its commit (f2fa96f3) genuinely touched it (the three
logging-discipline `ArchCategory` entries). I attempted to fix this
retroactively but the exclusive lease meant re-granting it to T-0622
would have blocked T-0624/T-0625 from ever claiming it in this same
session, so I left T-0622's scope declaration as-is and am disclosing
the gap here instead of silently leaving it undiscovered. Recommend the
coordinator either accept this as a known T-0622 scope-declaration gap
(the actual diff is legitimate and was gate-verified at the time) or
open a small follow-up ticket to formally reconcile it.

### Verification
- `uv run pytest tests/unit/test_arch.py -p no:cacheprovider -q` -- full
  file, 218 passed (15 new: TestMutableDefaultArg x2, TestFeatureEnvy
  x2, TestDataClumps x2, TestMagicLiteral x2, TestDeadPrivateCode x2,
  TestDeepInheritance x2, TestTemporalCoupling x2,
  TestRunSmellChecks x1).
- `uv run frob check --only lint --ticket T-0624` -- 0 errors, 0
  warnings.
- `uv run frob check --only gates-fast --ticket T-0624` -- 0 errors
  (fixed 3 real COV001 hits on the new module-level constants, missing
  `frob:doc` edges, plus the same PRE001 staleness hit via
  `frob ticket sweep T-0624`).
- `uv run frob check --only static --ticket T-0624` -- 0 errors.
- `uv run frob check --only gates-native --ticket T-0624` -- 0 errors.
- `uv run frob check --only gates-security --ticket T-0624` -- 0 errors.
- `git diff main --diff-filter=D --stat` -- empty.

### Cuts disclosed
- No wiring into `analyze_project`/the check pipeline (by design, per
  T-0626's own job).
- `check_dead_private_code`/`check_deep_inheritance` are per-module
  proxies, not the ticket's own project-wide versions (see above).
- `check_magic_literal` covers numeric literals only; string literals
  are out of scope (raw branch-condition text cannot reliably
  distinguish a magic string from an identifier without a real
  tokenizer), disclosed in the check's own docstring.
- The T-0622 scope-declaration gap noted above.

### Changed
```
 docs/modules/arch.md             | 229 ++++++++++
 src/frob/arch/_fallibility.py    | 399 ++++++++++++++++++
 src/frob/arch/_logging_checks.py | 335 +++++++++++++++
 src/frob/arch/_models.py         |  35 ++
 src/frob/arch/_normalized.py     |  11 +-
 src/frob/arch/_smells.py         | 562 +++++++++++++++++++++++++
 tests/unit/test_arch.py          | 874 +++++++++++++++++++++++++++++++++++++++
 tickets.md                       | 216 +++++++++-
 8 files changed, 2652 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/unit/test_arch.py::TestMutableDefaultArg::test_list_literal_default_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestMutableDefaultArg::test_none_default_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestFeatureEnvy::test_method_calling_other_receiver_more_than_self_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestFeatureEnvy::test_method_calling_self_more_than_others_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestDataClumps::test_same_three_keyword_group_at_three_sites_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestDataClumps::test_group_at_two_sites_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestMagicLiteral::test_bare_number_in_condition_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestMagicLiteral::test_zero_and_one_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestDeadPrivateCode::test_unreferenced_private_function_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestDeadPrivateCode::test_referenced_private_function_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestDeepInheritance::test_chain_beyond_threshold_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestDeepInheritance::test_shallow_chain_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestTemporalCoupling::test_guard_clause_on_initialized_flag_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestTemporalCoupling::test_field_not_guarded_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch.py::TestRunSmellChecks::test_combines_all_seven_checks` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 15 passed (from 15 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
