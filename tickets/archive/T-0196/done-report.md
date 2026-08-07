## Done report

Verified FIRST (per the ticket's own instruction): `_real_dataflow_graph`/
`_find_block` already existed pre-ticket (landed in `5d70dad`, 2026-07-17,
before this ticket was created) but only matched Python's literal `"block"`
tree-sitter node label and `"assignment"` node label -- confirmed directly
by parsing real fixtures through `frob.lang.raw_tree` for every supported
grammar (python, rust, typescript, c, cpp): rust's function body is also
labeled `"block"` (real path already worked, by coincidence), but
typescript/tsx label it `"statement_block"`, and c/cpp label it
`"compound_statement"` -- neither matched, so those three grammars were
silently falling to the `_build_dataflow_graph` co-occurrence proxy on
every symbol, never the real path, despite `frob.lang.symbol_tree`
recovering real structure for them just fine.

Changed:
- src/frob/dup/_pipeline.py -- added `_BLOCK_LABELS`
  (`"block"`/`"statement_block"`/`"compound_statement"`),
  `_ASSIGNMENT_LABELS` (`"assignment"`/`"assignment_expression"`/
  `"let_declaration"`), and `_DECLARATOR_LABELS`
  (`"variable_declarator"`/`"init_declarator"`) module constants, each
  verified against a real parse of a minimal function in that grammar (not
  assumed from grammar docs). `_find_block` now matches any label in
  `_BLOCK_LABELS` instead of the literal string `"block"`. `_statement_ids`
  now also descends into a `_DECLARATOR_LABELS` child (typescript's
  `variable_declarator` under `lexical_declaration`/`variable_declaration`,
  c/cpp's `init_declarator` under `declaration`) when the statement itself
  or its `_ASSIGNMENT_LABELS` child doesn't carry a direct `=`, so def/use
  labeling is correct for those wrapped declaration shapes too, not just a
  flat "everything is a use" fallback. Added `_find_child_label` helper.
  `_build_dataflow_graph` (the co-occurrence proxy) is unchanged and
  remains the fallback -- now demonstrably reached only when no
  `_BLOCK_LABELS` node exists (an unlisted grammar, e.g. `strata`; a parse
  failure; or a non-function region), not for four of five supported
  grammars by default. Module docstring's "R5's def-use/control-dependence
  graph is real..." deviation note, `_real_dataflow_graph`'s own
  docstring, and the R5 constants block's docstring all updated to
  describe the per-grammar coverage instead of a Python-only claim.
- tests/test_dup_r5_multilang.py (new) -- unit tests against real
  `frob.lang.symbol_tree` output (temp files written per grammar, real
  parse, no hand-built `TreeNode`s except the one deliberate
  unrecognized-label negative case) proving: python/rust/typescript/c/cpp
  each now hit the real `_real_dataflow_graph` path (non-`None`, with both
  "def" and "use" labels present, not just a same-role flat clique), and
  an unrecognized grammar label still honestly returns `None` (proxy
  fallback), not a guess.

Measured before/after (scratch verification, not assumed): before this
change, `_real_dataflow_graph` returned `None` for minimal rust/typescript/
c/cpp fixtures despite `symbol_tree` succeeding for all four (rust's
`"block"` label happened to already match, so only typescript/c/cpp were
actually affected in practice -- confirmed by re-running the same
before/after probe against all four grammars). After: all four return a
non-`None` graph with correct def/use separation (measured directly:
rust `(7, 5)`, c `(4, 4)`, cpp `(4, 4)`, typescript `(38, 11)` as
`(len(adjacency), len(labels))`).

Disclosed limitation (not fixed, out of `_ASSIGNMENT_LABELS`'s reach as
scoped): still not a full CFG on any grammar -- no branch-edge fan-out for
`if`/`for`/`while` (an `if`'s body statements sequence against each other
and the surrounding statements as if the `if` were transparent, no
synthesized branch/merge point), no true reaching-definitions dataflow,
and augmented-assignment/tuple-unpacking/`for`-loop-target binding still
fold into "use" rather than "def" on every grammar, same pre-existing
`frob:todo T-0001` follow-up as before this ticket -- this ticket closed
"which grammars get the real path at all" (survey items 7/8's core ask),
not "how much of a real CFG is it once on the real path."

Not Filed: T-draft-75a6070b (never refiled) (mints a real T-#### id once this worktree lands
on `main`), title "R5 real-CFG per-language coverage table missing from
dup.md (T-0196 follow-up)", scope `docs/modules/dup.md`. The ticket's plan
text says "Disclose per-language coverage honestly in dup.md," but
`docs/modules/dup.md` is NOT in T-0196's declared `scope` (`tickets.md`,
`src/frob/dup/**`, `src/frob/lang/**`, `frob-core/**`, `tests/**` only) --
`frob check --ticket T-0196` confirmed this with a live SCOPE001 the one
time the doc edit was attempted directly, so it was reverted
(`git checkout -- docs/modules/dup.md`) and filed separately instead of
self-expanding scope. The exact real-vs-fallback breakdown per grammar is
disclosed in code instead, in `_BLOCK_LABELS`'/`_ASSIGNMENT_LABELS`'/
`_DECLARATOR_LABELS`'s docstrings and the module docstring's R5 deviation
note, until the follow-up ticket lands the doc table.

Evidence: recorded via `frob ticket evidence T-0196 <node-id>...` (all 6
resolved against a fresh `pytest --collect-only` pass):
- tests/test_dup_r5_multilang.py::TestRealDataflowGraphPerGrammar::test_python_block_still_matches
- tests/test_dup_r5_multilang.py::TestRealDataflowGraphPerGrammar::test_rust_block_matches_and_labels_def_use
- tests/test_dup_r5_multilang.py::TestRealDataflowGraphPerGrammar::test_typescript_statement_block_matches_and_labels_def_use
- tests/test_dup_r5_multilang.py::TestRealDataflowGraphPerGrammar::test_c_compound_statement_matches_and_labels_def_use
- tests/test_dup_r5_multilang.py::TestRealDataflowGraphPerGrammar::test_cpp_compound_statement_matches_and_labels_def_use
- tests/test_dup_r5_multilang.py::TestRealDataflowGraphHonestFallback::test_unrecognized_grammar_label_returns_none

All 6 pass: `uv run pytest tests/test_dup_r5_multilang.py -p no:cacheprovider -q`
-> "6 passed" (foreground, measured). Full existing dup rung suite
(tests/test_dup_rungs.py, test_dup_smart.py, test_dup_region.py,
test_dup_inline.py, test_dup_cross_lang.py) also re-run green (48 passed
total across both runs) -- no regression to R4/R5/R6/region-subsection
behavior from widening the label sets.

Gates: `uv run frob check --ticket T-0196` -> `gates 4 errors, 49 warnings,
202 waived`. All 4 errors are pre-existing DOC001 ("linked from nowhere")
on `docs/design/architecture-check-catalog.md`,
`docs/design/capability-evasion-taxonomy.md`,
`docs/design/design-pattern-traps-corpus.md`,
`docs/design/structural-linter-adversarial-hardening.md` -- confirmed via
`git diff main --diff-filter= --stat -- <each path>` returning empty (zero
lines changed by this worktree) that all four are untouched, pre-existing
repo debt landed on `main` by other tickets (T-0330/T-0331-adjacent work),
not introduced or touched here. `ruff-check`/`ruff-format`/`ty` all pass
clean. Deletion-filter land rule (playbook section 9):
`git diff main --diff-filter=D --stat` is empty as of the final check
(caught and fixed real staleness twice mid-ticket -- `main` advanced past
this worktree's `git merge main` while work was in progress, twice; both
times a fresh `git merge main` fast-forwarded cleanly).

**Incident, disclosed rather than silently worked around:** the second
`git merge main` (after the deletion-filter re-check found
`docs/design/design-pattern-catalog.md` newly added on `main`) required
stashing local `tickets.md` changes first (`git stash push -- tickets.md`)
because `main` had also moved `tickets.md` forward since the first merge.
`git stash pop` afterward reported a clean `Auto-merging tickets.md` with
no conflict markers, but the resulting file had SILENTLY REVERTED T-0196's
own `state`/`evidence`/Done-report edits back to the pre-ticket
`state: queued`, `evidence: []`, no Done report -- traced to `refs/stash`
being a single ref shared across ALL worktrees of this repo (confirmed:
inspecting the popped stash commit via `git show <sha>` showed it
belonged to a *different* worktree's unrelated T-0244 work, not this
session's stash), so the pop applied someone else's/an unrelated stash
state rather than this session's own. Recovered by re-running `frob
ticket start T-0196` (state -> in-progress) and `frob ticket evidence
T-0196 <same 6 ids>` (idempotent, confirmed via CLI output above), then
re-inserting this Done report text by hand from this session's own
record -- no data was invented, only restored to what this session had
already produced and verified once already. Flagging for the
coordinator: `git stash` is unsafe for any worktree-parallel session in
this repo as currently set up; a future session hitting a
`tickets.md`-conflicting `git merge main` should prefer `git merge -X
ours -- tickets.md`-style manual resolution or a temporary copy
(`cp tickets.md /tmp/...`) over `git stash`, not this pattern.

REL001 disclosure: not observed in this pass's `frob check --ticket
T-0196` output (no `REL001` line appears in the captured tool output); if
the coordinator's land-time full-repo check surfaces one, it is a
coordinator-side version-bump concern, not something this ticket's scoped
run could see.

Not run in this worktree: `make coverage` (foreground pytest+coverage.xml+
`frob check --stamp-coverage`) per explicit coordinator instruction --
coverage stamping is the coordinator's job at land, not a per-ticket
requirement here. An earlier background `make coverage` invocation in this
session did complete successfully before being superseded by that
instruction (`Coverage XML written to file coverage.xml`,
`stamp_coverage: stamped 411 file(s)`, `coverage stamp written`) but that
stamp reflects a slightly earlier tree state and should not be treated as
this ticket's own verification step.

Not closed: leaving T-0196 for the reviewer/coordinator per this
dispatch's explicit instruction not to close.
