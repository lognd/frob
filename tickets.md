# Tickets

Central ledger managed by `frob ticket` -- one section per ticket.

<!-- ticket:T-0156 -->
```yaml
id: T-0156
title: 'release readiness: version, changelog, packaging, and the release gate'
state: in-progress
kind: feature
origin: human
created: '2026-07-18'
blocked_by:
- T-0148
- T-0153
- T-0154
- T-0155
- T-0157
- T-0158
- T-0159
- T-0162
parent: null
scope:
- pyproject.toml
- CHANGELOG.md
- README.md
- docs/**
- strata-core/Cargo.toml
- frob-core/Cargo.toml
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Get frob into a releasable state once the gates-zero sweep and the three feature tickets land. Deliverables: (1) version bump decision (current 0.1.0 line -- pick the next version honestly against the scale of what shipped) stamped via frob release stamp, with frob release check green as the gate; (2) CHANGELOG.md generated from the ticket archive + git history since the last release, grouped by area (strata, threat/CVE, vet, check/gates, tickets, editors), human-readable, every T-#### referenced; (3) README refresh: current subcommand table, strata overview with the self-model/self-conformance story, editors support, CVE mirror workflow, install paths (uv tool install, bare pip, dev) each verified by actually running them; (4) docs/index.md completeness pass -- every docs/ page linked, every public module documented; (5) packaging: uv build the wheel, decide and document the native-crate strategy (strata-core/frob_core: bundled, separate wheels, or optional with the T-0133-135 degrade contract -- verify the degrade contract works from the actual built wheel in a bare venv, and verify the T-0142/T-0152 dependency completeness holds there too); (6) final release gate: frob check exit 0 with gates at zero, frob sys audit fully PROVED, full pytest suite green, drift-locks all live. Do not tag or publish -- leave the repo in a provably releasable state and report what the release command sequence would be.

<!-- ticket:T-0160 -->
```yaml
id: T-0160
title: burn down TEST005 module-line-coverage backlog (~78 modules below 85% floor)
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/**
- tests/**
- frob.toml
evidence: []
attachments: []
acceptance: []
threat: null
```
TEST005 module-line-coverage floor (frob.toml [testing].module_line_cov=85) reports ~78 src/frob/** modules below threshold, from 0.0% (never-exercised runners like app/ack_runner.py, app/arch_runner.py, and most other app/*_runner.py CLI entry points) up to modules a few points shy of the floor (e.g. tickets/_store.py at 84.8%, strata/_claims.py at 84.7%). This backlog was invisible during T-0148's original scope (a fresh worktree has no .frob/coverage-stamp, and TEST005 silently produces no findings without one) -- it surfaced only after T-0148 regenerated the stamp to clear its own TEST006 finding ("no coverage stamp found"). It is pre-existing, repo-wide coverage debt, not something T-0148's edits introduced, and burning it down to the 85% floor across ~78 modules (many CLI app/*_runner.py entry points at literal 0%, needing new system/integration tests, not just unit tests) is a dedicated, multi-session effort far outside a gates-sweep ticket. Full per-module list captured via: uv run frob check --only test (TEST005 lines), 2026-07-18.

Acceptance: every src/frob/** module at or above module_line_cov=85 (or system_line_cov=80 in aggregate where a narrower per-module floor is not achievable), OR a specific, reasoned frob.toml override for modules that cannot reasonably reach the floor (e.g. thin CLI entry-point shims exercised only via subprocess system tests). Start with the 0.0%-covered app/*_runner.py entry points -- each is a CLI command's runner with no direct unit/integration test at all, the single highest-leverage slice of this backlog.

Scope correction (2026-07-18, same T-0148 sweep): `src/frob/gates/_coverage.py::_parse_classes` had a path-prefix bug -- Cobertura `filename` attrs are relative to the `--cov=src/frob` root (e.g. `app/ack_runner.py`), but every other path in `frob.graph` is repo-relative (`src/frob/app/ack_runner.py`); the two never matched, so BOTH `module_line` (this ticket's original ~78-module estimate) AND `symbol_branch` (per-symbol TEST005 branch-coverage, `unit_branch_cov=90`) silently mapped zero symbols this whole time. T-0148 fixed the prefix join. Re-running with the fix (and after excluding `src/frob/scaffold/data/**` template files, a separate genuine rule misfire fixed in the same sweep) shows the true backlog is far larger than originally scoped here: 197 unwaived TEST005 findings (up from ~78), most now per-symbol branch-coverage misses across `src/frob/**`, not just the module-line floor. This ticket's acceptance criteria and estimate above are superseded by that number -- treat "~78 modules" as the historical (and wrong, pre-fix) figure; the real acceptance criterion is 0 unwaived TEST005 findings from a fresh `uv run frob check --only test` after `make coverage`, both per-module and per-symbol. This is now unambiguously a dedicated, multi-session effort, not a gates-sweep add-on. (Renumbered from T-0157 to T-0160 on 2026-07-18: the original local allocation collided with main's real T-0157 (secrets-scan gate) landing concurrently; every `frob:waive TEST005` directive this ticket's sweep added under `src/frob/**` was updated in lockstep.)

<!-- ticket:T-0161 -->
```yaml
id: T-0161
title: 'PERF001-004 lexical heuristic: false-positive classes need real fixes, not
  permanent waivers'
state: done
kind: bug
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/perf/**,tests/**,docs/**
evidence:
- tests/test_perf.py::test_perf003_fires_on_nested_join_with_intervening_statement
- tests/test_perf.py::test_perf003_does_not_fire_on_sibling_comprehensions
- tests/test_perf.py::test_perf003_does_not_fire_on_sibling_statement_loops
- tests/test_perf.py::test_perf004_does_not_fire_when_sorted_is_the_loop_iterable
attachments: []
acceptance: []
threat: null
```
found while working T-0148: the gates sweep waived 93 PERF001-004 sites (14 PERF001, 8 PERF002, 52 PERF003, 19 PERF004) as false positives of src/frob/perf/_rules.py's documented 'lexical, one-token-stream-deep linear-scan' heuristic. Every waived site fell into one of a small number of misfire classes, each fixable without a full AST/control-flow rewrite: (1) PERF003 'nested loop join' fires on ANY function body containing 2+ 'for' headers plus an '==' comparison ANYWHERE in the body, even when the two loops are separate siblings (a setup loop then an unrelated assertion loop) rather than actually nested -- needs real nesting-depth tracking, not a flat token count over the whole function. (2) PERF004 'sorted()/.sort() in a loop' fires on any sorted()/.sort() call that is lexically inside an enclosing for/while, even when it executes exactly once per function call (e.g. sorting a small already-collected result list right before returning) -- needs to distinguish 're-sorted every outer iteration' from 'lexically nested but reached once'. (3) PERF001 'membership test in a loop' (confirmed in strata-core/src/lib.rs) fires on 'x in <name>' with zero awareness of the collection's actual type -- a HashSet/HashMap membership test is O(1) and not a smell at all, but the heuristic cannot tell a HashSet from a Vec since it never sees types. (4) PERF002 similarly flags any .index()/.count() call lexically inside a loop regardless of whether it runs once per call. Deliverables: either (a) add lightweight scope/nesting tracking to the existing token-stream scanner (track brace/indent depth per 'for' header, require the '==' to be textually inside the INNER loop's body, not just anywhere after the outer loop opens; require sorted()/.sort()/.index()/.count() calls to be inside the loop body they are nested under AND for that enclosing loop to actually repeat the call across iterations rather than short-circuiting via return/break), or (b) for languages with type info available (Rust via the existing AST, TypeScript via its checker) consult the declared/inferred type of the container before firing PERF001/PERF002. Re-run the current 93 waived sites (grep 'frob:waive PERF00' across the repo for the exact list, dated 2026-07-18, T-0148) against the improved rules and either remove now-unnecessary waivers or downgrade them to genuinely-irreducible cases. Acceptance: fewer than half of the current 93 waivers remain necessary, and no new false-positive class is introduced (verified against this repo's own PERF-clean modules).

## Done report

Changed:
- src/frob/perf/_rules.py::_bracket_depths (new)
- src/frob/perf/_rules.py::_loop_gate
- src/frob/perf/_rules.py::_perf001_python
- src/frob/perf/_rules.py::_perf002_python
- src/frob/perf/_rules.py::_perf003
- src/frob/perf/_rules.py::_perf004_python
- src/frob/perf/_rules.py::_header_colon_index (new)
- src/frob/perf/_rules.py::_method_call_in_loop
- src/frob/perf/_rules.py::_perf001_best_effort
- src/frob/perf/_rules.py::_perf002_best_effort
- src/frob/perf/_rules.py::_python_violations
- src/frob/perf/_rules.py::_best_effort_violations
- src/frob/perf/_rules.py::_symbol_violations

Fix, mechanically: `_rules.py` scanned a flat leaf-token stream and treated
"any `for`/`while` token anywhere earlier in the function" as loop context.
`_bracket_depths` now tags each token with its `(`/`[`/`{` nesting depth so
comprehension/generator-expression `for` (depth >= 1: `{x for x in y}`,
`any(x == y for x in y)`, `sorted(x for x in y)`) is no longer
indistinguishable from a real statement-level loop header (depth 0).
`_loop_gate`, `_perf003`'s loop scan, and `_perf004_python`'s `for`-header
lookup all consult depth now. `_perf003` additionally requires the second
depth-0 loop to be the literal next token after the first loop's header
colon (real nesting, not two sibling loops) and requires the `==` to occur
at or after the INNER loop's own colon, not merely anywhere in the
enclosing function. `_perf004_python` excludes `sorted(...)` used as the
`for` statement's own iterable (`for x in sorted(data):`), which runs once
per call to the enclosing function, not once per outer iteration.

Not fixed (documented, not force-waived): a membership/sort call that
executes exactly once AFTER an earlier, unrelated loop in the same
function (e.g. `for x in items: ...` then, later, `x in built_list`) is
lexically indistinguishable from "inside that loop" without real
indentation/block-end data, which `RawSymbol.body_tokens` (a
position-free leaf-token stream, no INDENT/DEDENT) does not carry. Two
of the 31 waivers still standing are exactly this class
(`tests/system/test_cli_scale.py:116` PERF001,
`src/frob/strata/_claims.py:249`-style PERF004 "runs once after this
loop"). Fixing this for real needs either real block-nesting data on
`RawSymbol` or a control-flow pass -- out of this ticket's "lightweight
scope/nesting tracking on the token scanner" scope; noted for a future
ticket if it recurs at volume.

Waived count (perf gate, `uv run frob check --only perf`, `waived: `
lines counted, measured before and after with the SAME command against
the SAME tree -- before-count was re-measured on this branch, not taken
from the ticket's original 93/T-0148 figure, since the tree has grown
waivers since T-0148 landed):
- Before this fix: 188 waived, 1 unwaived kept.
- After this fix (pre-merge): 30 waived, 1 unwaived kept (same site,
  unrelated to this ticket).
- After merging origin/main (one more PERF004 site landed on main in the
  interim, itself already correctly waived under the new heuristic): 31
  waived, 1 unwaived kept.
- Reduction: 188 -> 31, an 83.5% drop, well past the "fewer than half"
  acceptance bar. Zero NEW unwaived violations appeared anywhere in the
  repo (`comm -13` of the before/after `waived:` line sets is empty) --
  no new false-positive class introduced, and the two canonical
  PERF-clean/PERF-fires fixtures in tests/test_perf.py (sibling loop,
  real nested join) still pass unchanged.
- 100 `frob:waive PERF00\d` comment lines removed across 64 files
  (src/frob, strata-core, frob-core, tests) -- each removal verified by
  re-running `frob check --only perf` after deletion and confirming the
  kept/waived totals were unchanged (30 waived + 1 kept, matching the
  pre-deletion state) i.e. no comment removal surfaced a violation that
  actually still needed it. Waivers whose rule+file pair still had a
  genuinely-firing violation elsewhere in the same file (fallback
  matching via `_match_waiver`'s file-level scope) were left in place
  even where their specific originally-attached symbol no longer fires,
  to avoid breaking that fallback for the still-firing site --
  5 files: tests/test_capability_registry.py (PERF003, a real 3-level
  nested loop elsewhere in the file), tests/unit/strata/test_kernel_properties.py
  (PERF003), src/frob/strata/_selfconform.py, src/frob/strata/_threat.py,
  src/frob/testing/_collect.py (all PERF004, genuine single-sort-once
  sites elsewhere in file already correctly waived pre-fix).

Per-class fixture proof (new tests in tests/test_perf.py, all
`frob:tests src/frob/perf/_rules.py::perf_rules`):
- test_perf003_does_not_fire_on_sibling_comprehensions: set comprehension
  + any()-generator + unrelated `==` -- PERF003 does not fire (was the
  single largest false-positive class: ~majority of the 52 PERF003
  waivers named "sibling comprehension(s)/generator(s)... not a nested
  join").
- test_perf003_does_not_fire_on_sibling_statement_loops: two sibling
  (not nested) statement-level for loops plus an unrelated `==` --
  PERF003 does not fire.
- test_perf004_does_not_fire_when_sorted_is_the_loop_iterable:
  `for path in sorted(paths):` -- PERF004 does not fire.
- test_perf004_does_not_fire_on_sorted_generator_no_preceding_loop:
  `sorted(m.id for m in matched)` with no preceding statement loop --
  PERF004 does not fire (generator's own `for` no longer satisfies the
  loop gate for its enclosing sorted() call).
- Existing genuine-detection fixtures unchanged and still pass:
  test_perf001_fires_on_list_membership_in_loop,
  test_perf002_fires_on_index_call_in_loop,
  test_perf003_fires_on_nested_loop_equality_join,
  test_perf004_fires_on_sort_in_loop (plus their does-not-fire
  counterparts).

T-0230 (findings anchor to the def line instead of the statement): not
touched. It did not fall out of this rework naturally -- `RawSymbol`
still reports only `span[0]` (the enclosing symbol's start), and none of
the depth/nesting logic added here changes what line gets reported.
Left for its own ticket as instructed.

Filed: none (no out-of-scope work found; the one hard limitation found
-- no INDENT/DEDENT in `body_tokens`, blocking "runs once after an
earlier loop" detection -- is a known, pre-existing cut documented in
this file's own module docstring, not a new gap worth a ticket unless it
recurs at volume).

Evidence:
- `uv run pytest tests/test_perf.py -q` -- 22 passed (was 18 before this
  ticket's 4 new tests).
- `uv run frob test --base main` -- touched-set selected
  `tests/test_perf.py` (+ `test_perf_end_to_end_profile_load_and_heat`),
  `[PASS] python exit=0 4.62s`.
- `uv run frob check --only perf` -- `pass gates 1 violation(s), 31
  waived`, unchanged unwaived count from the pre-fix baseline.
- `uv run frob check` (full) -- `gates 3 violation(s), 31 waived`; the 3
  errors (`ty` unresolved-import for strata_core/frob_core in a
  subprocess-spawned collection, one pre-existing COV003 on T-0168's
  evidence id) are all pre-existing and reproduced identically on
  `origin/main` before this change (verified by `git stash` + rerun).
  `ruff-check`/`ruff-format` clean on the touched files after `ruff
  format`.
- `git diff origin/main --diff-filter=D --stat` -- empty (deletion-filter
  land rule clean; this worktree was originally merged against a stale
  local `main` ref missing 21 files/1 commit that had landed upstream in
  the interim -- re-fetched `origin/main` and re-merged before finishing,
  per the playbook's warm-up step).

Gates: `frob check --ticket T-0161` not run standalone (ticket is
`queued`, not started via `frob ticket start`, per this dispatch's
existing worktree state) -- `frob check` full-repo run above is the
gate evidence instead; no PERF-related error, no WAIVE001/WAIVE002
introduced by the 100 waiver-comment deletions (`frob check` full output
carries zero WAIVE001/WAIVE002 lines).

## Round 2 (reviewer REJECT addressed)

Reviewer verdict on the round-1 Done report above: REJECT, one CRITICAL
undisclosed false-negative regression -- `_perf003`'s "inner loop must be
the literal next token after the outer header's colon" adjacency check
silently missed real nested joins whenever any statement (accumulator
init, guard) sat between the two headers, e.g.
`for x in a: y0 = 0; for y in b: if x == y: ...`. Everything else in
round 1 was verified as reproducing/genuine (31/1 numbers, all 4 FP
regression tests, sorted-in-body/comprehension-inner-body adversarial
cases, waiver housekeeping).

Fix: relaxed the adjacency requirement to a forward scan for the next
statement-level (depth 0) loop keyword, allowing intervening statements
(`_next_statement_loop`). Relaxing adjacency alone reopens exactly the
false positive it was added to prevent -- two SIBLING (non-nested) loops
are lexically identical to "outer loop, one statement, inner loop" in a
position-free token stream with no INDENT/DEDENT. Replaced the adjacency
check with a correlation check: the OUTER loop's own bound variable (the
identifier right after `for`) must be an operand of the `==` found in the
candidate inner loop's body, not merely present anywhere nearby. Operand
identification (`_operand_names`) unwinds one bracket pair for a subscript
expression (`a[i - 1] == b[j - 1]`, the shape a real DP/edit-distance join
usually takes) but deliberately does NOT widen to attribute access
(`x.attr == ...`) -- while iterating on this fix, a first attempt used a
flat 6-token window on each side of `==` instead of the bracket-aware
operand walk, and that window incorrectly re-fired on 4 genuine sibling-
loop sites that reuse the same loop variable name and each end in
`<var>.attr == something`: `src/frob/app/sys_runner.py::_repo_root_for`
(`ancestor` reused across two sibling `for ancestor in ...:` loops),
`src/frob/gates/__init__.py::_match_waiver` (`waiver` reused across two
sibling `for waiver in candidates:` loops), plus one site each in
`src/frob/strata/_elaborate.py` and `src/frob/vet/_containment.py`. All
four were caught by re-running `frob check --only perf` after each
iteration and inspecting every newly-unwaived finding by hand before
accepting the change -- none needed a new waiver because none should
fire; narrowing the operand check to subscript-only made all four stop
firing again without reopening the adjacency regression.

New regression test: `test_perf003_fires_on_nested_join_with_intervening_statement`
in `tests/test_perf.py`, the reviewer's exact repro shape -- asserts
PERF003 fires. `tests/test_perf.py` is now 23 tests (was 22 in round 1),
all pass.

Restored one waiver round 1 had incorrectly removed as a side effect of
the adjacency bug: `src/frob/strata/_models.py::Lattice.leq`'s
`while frontier: ... for lower, higher in self.order: if lower == current`
is a genuine algorithm-inherent BFS nested loop (the original waiver's own
words, `"algorithm-inherent BFS over lattice pairs"`) that round 1's
too-strict adjacency check made stop firing entirely (a silent detection
loss, not a fix) -- it fires again correctly now and is waived again with
the same, still-accurate reason.

Updated waived/unwaived counts (`uv run frob check --only perf`, same
tree, round 2 vs round 1 vs the original pre-fix baseline):
- Original baseline (before any T-0161 work): 188 waived, 1 unwaived kept.
- Round 1 (adjacency-based, REJECTED): 31 waived, 1 unwaived kept.
- Round 2 (correlation-based, current): 27 waived, 1 unwaived kept (same
  pre-existing site, `src/frob/tickets/_land.py:67`, unrelated to this
  ticket in both rounds).
- Net reduction from the honest original baseline: 188 -> 27, an 85.6%
  drop -- still well past the "fewer than half" acceptance bar. The drop
  from round 1's 31 to round 2's 27 is NOT lost detection: those 6 sites
  (`src/frob/vet/_cve.py:335`, `src/frob/vet/_nvd.py:112`,
  `tests/test_capability_registry.py:277,303`,
  `tests/unit/cve/test_parser.py:201`) stopped firing because the
  correlation check correctly recognizes they were never real equality
  joins between the outer and inner loop elements (a filter on the inner
  element's own attribute, or membership checks, not a pairwise `==`
  involving the outer loop variable) -- round 1's adjacency-based version
  had already made these questionable (see the round-1 note that
  `tests/test_capability_registry.py:277/303`'s reason text didn't
  actually match the code at that location); round 2 resolves that
  mismatch by no longer firing there at all, one more precision gain in
  the same direction as round 1's `_bracket_depths` fix. One waiver
  restored (`_models.py`, above) as a correctness fix, not a new
  reduction.

Re-verification after the round-2 fix:
- `uv run pytest tests/test_perf.py -q` -- 23 passed.
- `uv run frob check --only perf` -- `pass gates 1 violation(s), 27
  waived`.
- `uv run frob check` (full) -- `gates 3 violation(s), 27 waived`; same
  single pre-existing unrelated error (`tickets/T-0168:0 COV003`) as
  round 1, reproduced identically before this ticket's work.
- `uv run frob test --base main` -- touched-set selected `tests/test_perf.py`
  (+ `test_perf_end_to_end_profile_load_and_heat`), `[PASS] python exit=0
  1.67s`.
- `git diff origin/main --diff-filter=D --stat` -- empty.
- `ruff format`/`ruff check` clean on all touched files.

Not touched further: T-0230 (line anchoring) still out of scope, per
round 1's note. No new tickets filed -- all 4 sibling-loop false positives
surfaced while iterating were caught and fixed within this same change,
not left as debt.

<!-- ticket:T-0166 -->
```yaml
id: T-0166
title: store grammar rejects code/may despite surface.md implying support
state: done
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- strata-core/src/parse.rs
- docs/strata/surface.md
- src/frob/strata/**
- tests/**
- design/frob.strata
- tickets.md
evidence:
- tests/unit/strata/test_store_code_may.py::TestStoreCodeMayGrammar::test_store_code_glob_elaborates_to_code_attr
- tests/unit/strata/test_store_code_may.py::TestStoreCodeMayGrammar::test_store_may_capability_lands_on_node_may
- tests/unit/strata/test_store_code_may.py::TestStoreMayFeedsThreat003::test_store_with_exec_may_fires_undischarged_cwe_94
attachments: []
acceptance: []
threat: null
```
Confirmed twice (T-0150 review read parse_store directly: no code/may branch, falls through to unknown-store-property; typani pilot reconfirmed): stores cannot carry code/may declarations though docs/strata/surface.md implies they can. T-0150 worked around it by folding tickets_ledger's code into the core node. Fix properly: implement code/may on store_prop in strata-core (mirroring parse_node), elaborate into the kernel, un-fold frob's own tickets_ledger workaround in design/frob.strata, and correct surface.md either way so doc and grammar agree.

## Done report

Resolution: implemented `code`/`may` on `store` (surface.md's `store_prop := node_prop | ...`
line was the correct spec; the grammar was the bug, not the doc). `code`/`may` on `store`
now mirror `node`'s handling exactly, and the T-0150 `tickets_ledger`/`core` workaround was
un-folded.

Changed:
- strata-core/src/parse.rs::parse_store -- new `code`/`may` branches (same STRING+/STRING
  shape T-0132 gave `node`), plus `code`/`may` fields in the stores JSON output.
- src/frob/strata/_ast.py::StoreDecl -- new `code: tuple[str, ...] = ()` / `may: tuple[str, ...] = ()`
  fields.
- src/frob/strata/_infra.py::_elaborate_store -- `code` globs desugar to `code=<glob>` attrs
  (same convention `_elaborate_node` uses, `_code_binding.py::_node_code_globs` reads it back
  generically off any `Node`); `may` lands directly on the elaborated `Node.may` field.
- docs/strata/surface.md -- new "`code`/`may` on `store` (T-0166)" callout paragraph
  (#node-grammar-implemented) documenting the fix and the exact semantics.
- design/frob.strata -- un-folded the T-0150 workaround: `src/frob/tickets/**` moved off
  `core`'s `code`/`may` onto `tickets_ledger`'s own `code "src/frob/tickets/**"` +
  `may "env"`/`"exec"`/`"fs"` (measured honestly via
  `frob.vet._capability.scan_directory_capabilities('src/frob/tickets')` -> `{env, exec,
  fs-write}`, zero eval/net/ffi). This drags in one new THREAT003 CWE-78 obligation on
  `tickets_ledger`, discharged with `assume "weakness:CWE-78:tickets_ledger" noflow registry
  -> tickets_ledger owner logan review "2026-10-15"` (graph-provable via the pre-existing
  `c_no_registry_ledger` assert, but an `assert`-form discharge still requires a boundary-KIND
  mitigation-chokepoint proof that doesn't exist here -- `assume` is the honest tool, same
  precedent `checker`'s discharge comment already documents).
- tests/unit/strata/test_store_code_may.py (new) -- grammar + elaboration tests for store
  code/may, plus two tests proving a store's `may "exec"` auto-instantiates the same
  undischarged THREAT003 CWE-78 obligation a node's would (answering the ticket's "does a
  store's may feed THREAT003 obligations?" question: yes, identically -- `_threat.py` reads
  `Node.may` generically with no node/store distinction).
- tests/system/test_frob_self_model.py -- claim count 12 -> 13 (new
  `weakness:CWE-78:tickets_ledger` assume), docstrings updated.
- tests/golden/frob_export_seccomp.json -- regenerated via
  `export_seccomp(elaborate(parse_module(design/frob.strata)))`; `tickets_ledger`'s seccomp
  profile now allows clone/execve/execveat/fork/vfork (its new `may "exec"`).
- strata-core rust unit tests: `parses_store_code_globs_and_may_capabilities`,
  `parses_store_without_code_or_may_defaults_empty`,
  `error_store_code_requires_at_least_one_glob`, `error_store_may_requires_string_not_ident`.

Semantics decided and documented: a store's `code` participates in tier-2 import conformance
(`check_import_conformance`) exactly like a code-modeled node's would (both read `code=` attrs
off any elaborated `Node`, no store/node distinction). A store's `may` capability
auto-instantiates THREAT003 weakness obligations exactly like a node's would, for the same
reason (`_threat.py` reads `Node.may` generically).

Filed: T-draft-956203f7 "store grammar still missing on-deploy/observe/errors_total/
panics_contained_by from node_prop" -- surface.md's `store_prop := node_prop | ...` grammar
line literally claims the FULL node_prop set is legal on store; this ticket closed only the
code/may gap it explicitly named. `on deploy`/`observe`/`errors_total`/`panics_contained_by`
remain unimplemented on `parse_store`, a real (smaller) remaining gap between that grammar
line and the actual parser, left for a follow-up ticket rather than folded into this one.

Evidence:
- `uv run pytest tests/unit/strata/test_store_code_may.py --collect-only`: 5 tests collected
  -- `TestStoreCodeMayGrammar::test_store_code_glob_elaborates_to_code_attr`,
  `TestStoreCodeMayGrammar::test_store_may_capability_lands_on_node_may`,
  `TestStoreCodeMayGrammar::test_store_without_code_or_may_defaults_empty`,
  `TestStoreMayFeedsThreat003::test_store_with_exec_may_fires_undischarged_cwe_94`,
  `TestStoreMayFeedsThreat003::test_store_without_may_fires_no_obligation`.
- `uv run pytest -q -n auto`: full suite green (exit 0), no failures, after the golden-file
  regeneration and test_frob_self_model.py claim-count update.
- `cargo test --release` (strata-core, `VIRTUAL_ENV`/`LD_LIBRARY_PATH` pointed at the
  worktree venv/uv python lib): 106 passed, 0 failed, including the 4 new store code/may tests
  and `parses_store_carries_pii_tags`/`parses_store_managed_marker` (unaffected precedent
  tests still green).
- `uv run frob check --only sys`: 0 violations (was `1 violation(s)` THREAT003 mid-fix, before
  the `tickets_ledger` discharge claim was added).
- `uv run frob check`: 1 error total, `[gates] tickets/T-0168:0 COV003` -- pre-existing, out of
  scope (already documented at tickets.md's own T-0221..T-0234 filing note as "out of scope:
  COV003 on T-0168 (stale evidence id, unrelated ticket)"); no new violations introduced by
  this change, before or after merging main forward.
- `uv run frob test --base main`: `[PASS] python exit=0 8.17s`, ran the touched-set including
  `tests/unit/strata/test_store_code_may.py`, `tests/system/test_frob_self_model.py`, and
  `tests/unit/strata/test_managed.py::TestManagedGrammar::test_store_managed_marker_elaborates_to_attr`.
- `git diff main --diff-filter=D --stat`: empty, after a second `git merge main` (main had
  moved to b2a91fa mid-session, adding docs/guides/extending/** and other unrelated files --
  fast-forwarded cleanly, no conflicts, `make core` rebuilt, full suite re-verified green).

Gates: `frob check --ticket T-0166` clean except the pre-existing `tickets/T-0168:0 COV003`
(unrelated ticket, out of scope, already documented as such at this ledger's T-0221..T-0234
filing note). Note: the mid-session `git merge main` fast-forward dropped the recorded
pre-work sweep (PRE001 fired on the first post-merge `--ticket` run since `.frob/prework/` is
local, uncommitted state); re-ran `uv run frob ticket sweep T-0166` to re-record it (dup=165,
xref=6), after which `--ticket T-0166` shows 0 violations beyond the pre-existing T-0168 one.

<!-- ticket:T-0170 -->
```yaml
id: T-0170
title: kotlin capability-scanner column for android nodes
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/vet/_capability.py
- tests/**
- docs/modules/vet.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
logand.app has an android node; no Kotlin pattern table exists, so its capabilities cannot be verified. Add kotlin as a language column per the T-0158 matrix discipline: pattern tables for the reserved kinds where Kotlin idioms exist (net: OkHttp/HttpURLConnection/Retrofit; exec: Runtime.exec/ProcessBuilder; client_storage: SharedPreferences/Room; fs; eval: unusual -- excuse honestly), per-cell fire fixtures, .kt/.kts extension mapping. Sequence after T-0158 lands the matrix.

<!-- ticket:T-0171 -->
```yaml
id: T-0171
title: THREAT002 fires in quality views lacking the sink taxonomy security views have
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/strata/**
- tests/**
- docs/strata/threat.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
logand.app pilot: THREAT002 (capability kind matches no sink taxonomy entry) fires against quality-family audit views because views do not share the capability-to-CWE mapping the security views carry -- the same signal that hit frob's own T-0150 work (DEFAULT_BENIGN_CAPABILITIES was the frob-repo patch, but external repos hit the raw gap). Decide the principled fix: the sink taxonomy and benign-capability excuse table should be single-sourced across view families, not re-declared per view; a capability genuinely irrelevant to a quality view must not demand a per-repo excuse. Regression-test against a fixture reproducing the pilot's shape.

<!-- ticket:T-0173 -->
```yaml
id: T-0173
title: sys audit output repeats identical WARNING blocks across all views
state: queued
kind: ux
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/app/sys_runner.py
- src/frob/strata/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
logand.app pilot: the same WARNING blocks print once per configured view (8x duplication), burying the per-view differences that matter. Deduplicate: print shared findings once with a views-affected annotation, keep per-view sections for view-specific results only. Snapshot-test the output shape.

<!-- ticket:T-0174 -->
```yaml
id: T-0174
title: waiver mechanism for sys-audit findings (SYS/THREAT rules) analogous to frob:waive
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/strata/**
- design/**
- docs/strata/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
logand.app pilot: check-gate violations have frob:waive with written reasons, but sys-audit findings (SYS100-102, THREAT002/003) have no waiver channel -- external repos must either fix immediately or live with permanent red, which pushes toward gaming the model instead of honest debt. Design the analog: an in-design waive/accept declaration (surface syntax on the node/claim, e.g. an accept clause with a mandatory reason string and optional ticket ref -- reuse the assume claim machinery where it already fits rather than a parallel channel), surfaced in audit output as WAIVED with the reason, counted separately, drift-locked so reasonless or stale waivers fail. Must satisfy the same discipline as frob:waive: narrowly scoped, reason mandatory, loud in output.

<!-- ticket:T-0177 -->
```yaml
id: T-0177
title: 'frob serve daemon: incremental gate evaluation over the warm obligation graph'
state: queued
kind: feature
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/serve/**
- src/frob/gates/**
- src/frob/graph/**
- src/frob/app/**
- pyproject.toml
- Makefile
- tests/**
- docs/modules/serve.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
frob serve is already a FastMCP stdio server with 5 read-only tools (doable tickets, stale docs, graph query, doc-for, check-scope) and is now wired into the coordinator's MCP config. Grow it into the structural fix for test-wait latency: the obligation graph knows exactly which obligations a diff can invalidate (frob test --base already proves the touched-set concept for tests) -- exploit it for gates. Deliverables: (1) warm state: the daemon holds the parsed graph snapshot, collected test ids, and the stamped violation baseline, refreshing incrementally on file-change (mtime/content-hash walk, reuse the .frob sqlite cache) instead of cold-parsing per invocation; (2) frob_check_delta MCP tool: given a base ref or dirty set, evaluate ONLY the obligations whose inputs changed and return the violation delta against the stamped baseline, in seconds; (3) frob_run_touched_tests tool wrapping the existing touched-set selection; (4) correctness guarantee: incremental results must provably match a cold frob check -- add a verification mode that runs both and diffs, plus property tests for the invalidation logic (an obligation NOT re-evaluated must have had no changed inputs -- vacuous-pass doctrine applies to the cache); (5) packaging: mcp becomes a proper [serve] extra in pyproject (mirroring [smt]) with _require_mcp's remedy message updated; Makefile install-tool already passes --with mcp -- reconcile with the extra; (6) docs/modules/serve.md updated with the daemon lifecycle and the staleness/correctness contract. Sequence AFTER the T-0148 sweep lands (gates code moves under it).

<!-- ticket:T-0178 -->
```yaml
id: T-0178
title: 'agentic time profiling: non-gated breakdown of where development time goes'
state: queued
kind: feature
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/app/**
- src/frob/tickets/**
- src/frob/stats/**
- scripts/**
- docs/modules/stats.md
- docs/guides/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Diagnostics ONLY -- explicitly NOT a gate family: no rule ids, nothing fails on these numbers, report-only (user directive: for designing tooling around, never for gating). Deliverables: (1) frob CLI entry timing hook -- every frob invocation appends {iso_ts, subcommand, args_head, duration_ms, exit, tree_hash} to .frob/telemetry.jsonl (local-only, already gitignored via .frob/, opt-out env var FROB_NO_TELEMETRY); reuse the per-gate timing frob check already computes by logging it structured instead of display-only. (2) ISO timestamps on ticket state transitions (created/started/done currently date-only) so per-ticket cycle time is computable. (3) EXTERNAL TOOL COVERAGE: ship a Claude Code PostToolUse hook script (scripts/frob-telemetry-hook + docs/guides page with the settings.json snippet) that appends every harness tool invocation -- Bash command head, duration, exit -- to the same telemetry stream; hooks fire for subagents too, so implementer/reviewer runs are covered without per-tool shims; document an optional PATH-shim mode for profiling outside the harness. (4) frob stats --agentic report over the merged stream: per-ticket cycle time and review-round count (parse Done-report addenda), command-time breakdown by category (frob-check / test-suite / native-build / vcs / other), top wall-clock sinks, and RETREAD DETECTION -- identical command+tree_hash re-runs counted as cache-hit candidates, which directly quantifies the T-0177 daemon payoff before it is built. (5) coordinator flow: document attaching the harness usage block (tokens, tool_uses, duration per dispatch role) at ticket close via the existing frob ticket attach, so cost history survives sessions. Privacy: telemetry never committed, never networked, redact anything matching the T-0157 secrets patterns before writing the command head. Tests: hook script emits valid JSONL under fake invocations; stats aggregation over a fixture stream; redaction case.

Addendum (user, 2026-07-18) -- TOKENS as a first-class dimension beside
time: (a) per-tool-call token cost -- the PostToolUse hook also records
an output-size token estimate (len/4 heuristic is fine; note the method)
for every tool result, since tool OUTPUT is what silently consumes agent
context: the report must rank tools by cumulative output tokens (e.g.
'frob check dumps cost N tokens/run x M runs') to identify which tools
need quieter output modes or pagination; (b) per-development-stage
attribution -- bucket both time and tokens by lifecycle stage, using the
telemetry markers already present in the stream (frob ticket start ->
first edit -> first test run -> evidence recording -> done report) and
by dispatch role (implement / review / rework round N / land), so the
report answers 'what does a REJECT round cost in tokens and minutes'
with measured numbers; (c) the coordinator-attached harness usage block
(subagent_tokens, tool_uses, duration per dispatch) is the ground truth
to reconcile the per-call estimates against -- report both and the
discrepancy.

Addendum 2 (user, 2026-07-18) -- PER-TEST TIMING ANNOTATIONS: track
per-test wall-clock as a Gaussian running estimate (Welford mean/sd/n,
persisted in .frob telemetry keyed by pytest node id, fed by the
existing test-run machinery). Write the estimate as a comment annotation
on the test itself (e.g. `# frob:perf mean=12.4s sd=1.1 n=9` above the
test def), updated ONLY when the new mean shifts beyond 2 sigma from
the annotated value -- statistical update to avoid diff churn, never
per-run rewrites. Consumption: frob test / frob check gain a fast mode
that SKIPS tests whose annotated mean exceeds a configured threshold,
and skipping is LOUD (summary names every skipped-slow test and its
annotated cost); the full check always runs everything -- fast mode is
an explicit opt-in, never the default for release/CI gates (vacuous-pass
doctrine: a skipped test must be visible, and the full gate is the
authority).

<!-- ticket:T-0179 -->
```yaml
id: T-0179
title: 'TTY-aware pretty output: colors and formatting across all frob commands'
state: queued
kind: ux
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/logging/**
- src/frob/app/**
- src/frob/check/**
- tests/**
- docs/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Bake consistent pretty formatting and color into frob's terminal output for TTYs, skipped cleanly when non-TTY. Build on the existing src/frob/logging/color.py should_color machinery -- single source of truth, honoring isatty, NO_COLOR, FORCE_COLOR, and a [tool.frob] override. Apply across the surfaces users actually read: frob check tool/gates summary (pass/fail coloring, aligned columns, per-gate timing dimmed), frob sys audit (PROVED green, GAP red, view sections), frob ticket list/doable (state-colored ids), frob vet reports (severity coloring), frob stats. HARD CONSTRAINT: non-TTY output must remain byte-stable plain text -- agents, CI, and this repo's own snapshot tests parse it; add tests locking both modes (force-color golden and plain golden) so pretty mode can never leak ANSI into piped output. No new heavyweight dependency without written justification (prefer hand-rolled ANSI via the existing color module over adding rich).

<!-- ticket:T-0180 -->
```yaml
id: T-0180
title: 'closed-world unknown-import accounting: vetted-library cache engine (T-0158
  addendum 2 remainder)'
state: queued
kind: security
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/vet/**,tests/**,docs/modules/vet.md
evidence: []
attachments: []
acceptance: []
threat: null
```
T-0158 shipped the single-source dangerous-operations registry, the (kind x language) coverage matrix with 0 unexcused cells, and the sys-audit matrix-verdict proof line. NOT shipped (too large for one pass, explicitly deferred per T-0158's own escape valve): addendum 2 deliverable (2), full CLOSED WORLD accounting -- resolving every third-party import in a vetted dependency's source to (a) a registry entry, (b) a VETTED library (same scanner engine run over the installed third-party source, cached per package+version, e.g. reusing the frob.vet._cache.py sqlite pattern), or (c) a LOUD 'unknown, unvetted, uninspected' failure -- with the audit accounting line (N registry ops, M vetted libraries, K explicit no-capability entries, 0 unknown) T-0158's addendum 2 describes. T-0158's sys-audit line covers the (kind x language) MATRIX proof only, not this import-resolution closed-world proof. Needs: an import-graph walk per vetted package (python ast.parse imports at minimum), a resolution function classifying each imported name against DANGEROUS_OPERATIONS/registry libraries vs NO_CAPABILITY_MODULES vs unresolved, and a persistent per-package+version cache keyed like _cache.py's verdict cache.

<!-- ticket:T-0187 -->
```yaml
id: T-0187
title: 'frob dup bleeding-edge: algorithm survey, reverse-templating abstraction,
  exhaustiveness meta-test'
state: in-progress
kind: feature
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/dup/**
- frob-core/**
- tests/**
- docs/modules/**
- docs/index.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
User mandate 2026-07-18: frob dup does the basics (R1-R6 rungs: winnow, WL-hash, candidate_pairs, tree_edit in frob-core; statement-Levenshtein; co-occurrence CFG/DFG proxy) but must be bleeding-edge. Phase 1 RESEARCH (exhaustive-researcher): map the clone-detection state of the art against our implementation -- APTED exact tree edit distance, SourcererCC bag-of-tokens overlap, Oreo metrics-based type-3/4, NiCad normalization+abstraction, DECKARD characteristic vectors, learning-based (ASTNN, FA-AST GNN, CCLearner) with honest feasibility calls for a no-model-dependency tool, cross-language clone detection, and ANTI-UNIFICATION / reverse templating: report each clone group with its abstracted template plus per-instance bindings (the shared skeleton with holes), so the fix suggestion is the extracted function signature, not just 'these are similar'. Phase 2 DESIGN+TICKETS: planner converts the survey into an implementation ticket tree (rust-kernel work vs python orchestration split explicit). Phase 3 META-TEST: exhaustiveness drift-lock in the T-0158/T-0182 mold -- a registry of detectors/rungs/clone-types, parametrized litmus fixtures proving every (clone type 1-4 x supported language x rung) cell either fires on a minimal fixture pair or carries a written exclusion; adding a detector or claiming a clone type without a firing fixture fails the suite. Acceptance: survey doc committed, ticket tree filed, meta-test green over the CURRENT detector set before any new detector lands.

<!-- ticket:T-0188 -->
```yaml
id: T-0188
title: 'catalog: add CWE-295 (improper cert validation) WeaknessEntry to unblock TLS
  verify=False fingerprint'
state: queued
kind: security
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/strata/**
- tests/**
- docs/strata/threat.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: spoofing
```
T-0153 review follow-up: the TLS verify=False fingerprint class was correctly cut because no CWE-295 WeaknessEntry exists in CWE_CATALOG/CWE_TOP_25_CATALOG/QUALITY_CATALOG and the CVEFP001 drift-lock (rightly) refuses fingerprints citing absent CWEs. Add the catalog row (with honest views placement), then the fingerprint entry (requests/httpx/aiohttp verify=False, node tls rejectUnauthorized false, rust danger_accept_invalid_certs), litmus positive/negative source tests per T-0153's pattern. Also reconcile CWE-916 (mentioned in _cve_fingerprint.py docstring but in neither catalog nor cut-class list) -- add it or fix the docstring.

<!-- ticket:T-0189 -->
```yaml
id: T-0189
title: 'catalog: add CWE-611 (XXE) WeaknessEntry to unblock XML external-entity fingerprint'
state: queued
kind: security
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/strata/**
- tests/**
- docs/strata/threat.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: info-disclosure
```
T-0153 review follow-up: XXE fingerprint class cut because no CWE-611 WeaknessEntry exists and CVEFP001 refuses fingerprints citing absent CWEs. Add the catalog row, then the fingerprint entry (python lxml etree.parse with resolve_entities, xml.sax without feature_external_ges disabled, java-style patterns out of scope -- only supported languages), litmus positive/negative tests per T-0153's pattern.

<!-- ticket:T-0190 -->
```yaml
id: T-0190
title: secrets-gate fixtures trip GitHub push protection -- main is unpushable
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- tests/test_secrets_gate.py
- src/frob/gates/_secrets.py
- docs/modules/gates.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
GH013 push protection rejects main: the Stripe fixture at tests/test_secrets_gate.py:49 (landed in 48aeed1, T-0157) is realistic enough for GitHub secret scanning despite T-0157's clearly-fake requirement. Every push of main is blocked until resolved. Fix has two parts: (1) make every fixture structurally un-flaggable by GitHub (pattern-invalid tail: wrong length/charset/checksum for the provider) while still firing frob's own gate -- if frob's format constraint is currently so strict that only GitHub-flaggable strings can fire it, LOOSEN the fixture-facing constraint or add a test-only needle path, disclosed; (2) meta-test: fixtures must not match GitHub's published secret-scanning patterns (encode the Stripe/AWS/GitHub-token formats we know) so a future fixture cannot re-trip push protection. REMEDIATION for the already-flagged blob (coordinator step, not this ticket): after all in-flight branches merge, rewrite the unpushed range to replace the flagged fixture in 48aeed1 itself (remote tip predates it, so no force-push needed), or the user may use the GitHub unblock URL instead. This ticket only makes the CURRENT tree safe and drift-locked.

<!-- ticket:T-0191 -->
```yaml
id: T-0191
title: wire DUP001/DUP002 smart-dup rules into frob check gates -- pipeline currently
  inert
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: T-0187
scope:
- tickets.md
- src/frob/gates/**
- src/frob/dup/**
- frob.toml
- tests/**
- docs/modules/dup.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Survey finding (dup-sota-survey.md sec 0/3.1): DUP001/DUP002 are pure rule functions never invoked from frob.gates.__init__; frob check still runs only the legacy Type-1/2 scanner, so the whole R1-R5 smart pipeline never gates a build. Wire the clones gate to the smart pipeline behind the existing opt-in leaf, fixture tests proving a planted R3/R4 clone fails check when enabled and passes when waived. Highest priority of the T-0187 tree: everything else is inert until this lands.

<!-- ticket:T-0192 -->
```yaml
id: T-0192
title: frob dup --probe CLI flag reaching probe_equivalence (R6) -- closes T-0041
  debt
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: T-0187
scope:
- tickets.md
- src/frob/dup/**
- src/frob/app/**
- src/frob/__main__.py
- tests/**
- docs/modules/dup.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
R6 probe_equivalence is fully implemented and unreachable (no --probe string anywhere under the CLI, confirmed by survey). Wire the flag, document the workload contract, CLI-level test.

<!-- ticket:T-0193 -->
```yaml
id: T-0193
title: 'R1.5 exact-region kernel: generalized suffix automaton over normalized token
  stream'
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: T-0187
scope:
- tickets.md
- frob-core/**
- src/frob/dup/**
- tests/**
- docs/modules/dup.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Survey item 16 ADOPT: R1/R2 hash whole symbol bodies only, so partial copy-paste regions inside otherwise-different functions are invisible today. New frob-core kernel; region output feeds the existing CloneRegion model; cargo tests + python-side fixtures.

<!-- ticket:T-0194 -->
```yaml
id: T-0194
title: 'anti_unify kernel: Plotkin lgg over (labels,parents) node arrays'
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: T-0187
scope:
- tickets.md
- frob-core/**
- src/frob/dup/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Survey sec 4: lockstep top-down walk emitting shared nodes and $hole_N at divergence, returning template arrays + binding index pairs; reuses the node-array representation apted_similarity already consumes. Cargo tests incl. hole-ceiling sanity (>50 pct holes = Err back to plain pair).

<!-- ticket:T-0195 -->
```yaml
id: T-0195
title: 'reverse-templating report: CloneTemplate/CloneBinding models, extraction-signature
  synthesis in DUP001 messages'
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by:
- T-0194
parent: T-0187
scope:
- tickets.md
- src/frob/dup/**
- tests/**
- docs/modules/dup.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Survey sec 4: frozen pydantic CloneTemplate/CloneBinding, CloneReport.groups[].template optional, signature synthesis one param per distinct hole (reuse identifier when both instances agree), DUP001 violation message gains the suggested extraction. The violation hands you the fix, not a percentage.

<!-- ticket:T-0196 -->
```yaml
id: T-0196
title: 'R5 fidelity: real control-flow edges from frob.lang where available, proxy
  demoted to true fallback'
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: T-0187
scope:
- tickets.md
- src/frob/dup/**
- src/frob/lang/**
- frob-core/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Survey items 7/8 ADAPT: verify frob.lang actual CFG-edge coverage FIRST (the survey flags this VERIFY), then follow R4 established two-tier pattern (real primary, proxy fallback for unparseable symbols). Disclose per-language coverage honestly in dup.md.

<!-- ticket:T-0197 -->
```yaml
id: T-0197
title: 'candidate prefilters: DECKARD characteristic vectors + Oreo metric ratios
  + NiCad size ratio'
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: T-0187
scope:
- tickets.md
- frob-core/**
- src/frob/dup/**
- tests/**
- docs/modules/dup.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Survey items 2/4/6 (non-ML halves): three additive candidate-pruning stages before APTED/WL verification; prefilters only prune pairs, never add false positives -- test that enabling them never changes the verified-clone set on fixtures, only the pair count examined.

<!-- ticket:T-0198 -->
```yaml
id: T-0198
title: 'cross-language clone litmus: same logic in two grammars through the real pipeline'
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: T-0187
scope:
- tickets.md
- tests/**
- src/frob/dup/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Survey item 13: the cross-language claim rests on shared node vocabulary between frob.lang grammars but no fixture proves it. One fixture pair (python+ts same algorithm) through the REAL pipeline; if vocabulary does not align, that is the finding -- document and file rather than force.

<!-- ticket:T-0199 -->
```yaml
id: T-0199
title: 'dup exhaustiveness meta-test: (clone-type 1-4 x language x rung) matrix registry
  + litmus fixtures'
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: T-0187
scope:
- tickets.md
- src/frob/dup/**
- tests/**
- docs/modules/dup.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Survey sec 5, user mandate: registry of detectors/rungs/claimed clone types; parametrized fixture pairs per claimed cell (fire + negative); unclaimed cells need written exclusions; a detector or clone-type claim added without a fixture fails the suite -- T-0158 capability-matrix mold. Meta-test must be green over the CURRENT detector set before any new detector lands (acceptance from T-0187).

<!-- ticket:T-0200 -->
```yaml
id: T-0200
title: add real kill-switch/feature-flag mechanism for exec/net capabilities (checker/core/stratamod/vet)
state: queued
kind: feature
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/process/**
- src/frob/check/**
- src/frob/strata/**
- design/frob.strata
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
T-0155's LINT004 rule (design lint family) fires honestly on design/frob.strata's checker/core/stratamod/vet nodes: each holds a risky (exec/net) may capability with no real, checked-in kill switch (env var / feature flag) an operator can flip live to disable it. T-0155 deliberately did not fabricate a flag=<id> attr naming a mechanism that does not exist (declare real facts or waive with reasons, T-0150/T-0151 precedent) -- this ticket is the follow-on product work to build the actual mechanism and then discharge LINT004 for real on design/frob.strata.

<!-- ticket:T-0204 -->
```yaml
id: T-0204
title: 'standing warnings triage: exports (12+ per pkg), dup 64 groups, arch 197 warns,
  perf 174'
state: queued
kind: bug
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/**
- tests/**
- frob.toml
- docs/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
User directive 2026-07-18: the pass-line counters hide real debt -- frob-exports reports 12-253 public symbols missing from __init__.py per package (decide policy: export or demote to private, per package, no blanket waiver), frob-dup 64 duplicate groups (triage: real extraction candidates vs false pairs; feeds T-0187 tree), frob-arch 197 warnings + 123 suggestions (long-function/god-class residue post-calibration -- fix or waive with reasons), perf gate 174 violations (166 waived -- re-audit every waiver still holds after T-0161's heuristic fixes land; the 8 unwaived need real fixes). Deliverable: each family driven to a state where the summary line is HONEST -- zero unwaived findings or a written per-finding reason; no threshold-loosening without a disclosed decision. Split into child tickets per family if any single family exceeds a session of work -- this ticket is the umbrella and the accounting.

<!-- ticket:T-0206 -->
```yaml
id: T-0206
title: tickets-archive.md has a stale duplicate T-0169 entry from a ledger-conflict
  splice
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- tickets-archive.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Found while merging main into the T-0169 worktree: tickets-archive.md on main contains a T-0169 block with state=queued and no Done report/evidence, silently spliced in by an unrelated ledger-conflict merge (same incident class the agent playbook's ledger-conflict splice guidance warns about) -- NOT a real close. The authoritative T-0169 record is in tickets.md (in-progress, with a full Done report). Delete the stray tickets-archive.md duplicate so frob ticket listings don't show two T-0169 records in conflicting states. Also check tickets-archive.md for other stray splices from the same merge incident. (The branch's second draft, e1beb2a8 covering the html_render self-match, was dropped at landing as a duplicate of T-0201, which carries the same analysis and is already dispatched.)

## Failure log
- 2026-07-18 attempt 1: Premise stale on main: the stray queued-state T-0169 archive duplicate existed only in the T-0169 worktree's pre-archive ledger copy (branched at 1101c3e). Current main archive (rebuilt at 0b4ff16) has zero T-0169 entries and a cross-ledger id-duplicate grep is clean. Nothing to delete.

<!-- ticket:T-0207 -->
```yaml
id: T-0207
title: 'structural PII/secrets detection: waivable checks over data structures, schemas,
  and env access'
state: queued
kind: security
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- src/frob/strata/**
- src/frob/vet/**
- src/frob/lang/**
- design/frob.strata
- tests/**
- docs/**
- frob.toml
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: info-disclosure
```
User mandate 2026-07-18 ('if it passes, it's safe'): extend T-0154 (PII flow proofs) and T-0157 (secrets token scan) with STRUCTURAL detection over data surfaces, every rule waivable via frob:waive with a written reason so zero-unwaived means every PII/secret surface is either declared or consciously waived. Detector families: (1) DATA-STRUCTURE FIELDS: pydantic/dataclass/TypedDict/attrs field names and types across supported languages (name keyword table: email, phone, ssn, dob, address, ip, password, token, api_key, secret, salt, card/pan/cvv...; type-based: EmailStr, SecretStr, and TS/rust equivalents) -- a detected PII-shaped field on a node without a matching T-0154 PII category declaration (or waiver) fires; declared-but-never-observed goes stale like SYS101. (2) DATABASE SCHEMA: CREATE TABLE / column DDL in migrations (alembic, raw SQL) and ORM models (sqlalchemy columns) scanned with the same keyword+type tables -- schema headers are the highest-value PII surface. (3) ENV/SECRET SOURCES: os.environ[...]/os.getenv/load_dotenv() call sites (and process.env, std::env::var) are secret-source observations that must map to declared strata secret nodes (T-0082 std.secrets) or be waived -- an unmapped env read fires. (4) EMAIL-SHAPE VALUES: detect email-shaped string literals in code/fixtures WITHOUT naive regex (user explicit: regex is bad for email matching) -- use a structural parse (local@domain.tld via a real address parser, e.g. email.utils/parseaddr semantics or the WHATWG algorithm) with the T-0157 fake-marker escape (frob:secret fake / placeholder shapes stay writable). (5) KEYWORD SWEEP: identifier/comment keyword hits at suggestion severity only (no hard fail on names alone). DISCIPLINE (non-negotiable, per registry precedent): single-source keyword/type registry (no duplication between detectors); litmus fire+discharge fixtures per detector (T-0145 style); per-entry parametrized drift-lock (T-0182 style) so a registry keyword without a firing fixture fails; exhaustiveness matrix (detector x language) with written exclusions for unpatterned cells (T-0158 style); self-match exclusion for the registry file itself designed in from day one (T-0201 lesson -- the keyword table must not detect itself); wire into frob check as a new gate family (PII0xx/SEC1xx) default-on at WARN for adoption, severity dial in frob.toml; sys audit gains the joined view (structural observations vs declared PII/secret model). Split into child tickets per detector family at plan time if needed; this is the umbrella.

<!-- ticket:T-0208 -->
```yaml
id: T-0208
title: vet obfuscation scan pathologically slow -- high_entropy_strings dominates,
  no progress/timeout
state: in-progress
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/vet/**
- tests/**
- docs/modules/vet.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 (all 3 repos): frob vet unusable -- lograder killed at 11m47s with 15/30 packages (101MB venv); aprog-public stuck on numpy at 120s. cProfile+SIGALRM around scan_tree(fetch=False): _obfuscation.py:70 high_entropy_strings consumed 82 of 120 profiled seconds (785 calls); tree-sitter/capability scans fine. Fix: cap candidate string count/length per file, skip literal-table files over a size threshold, optimize the entropy loop, add per-package progress lines and --timeout/--jobs. Acceptance: frob vet completes on lograder's venv under 2 minutes with progress output.

<!-- ticket:T-0209 -->
```yaml
id: T-0209
title: capability scanner matches needles inside comments and strings
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/vet/_capability.py
- src/frob/lang/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 aprog-public: SYS100 reported capability net observed at assignments/api-harvester/assets/starter.py:22 -- that line is COMMENT text describing requests.get; the assignment forbids real network imports. Forced a false may declaration dragging bogus CWE-918 obligations -- corrupts the security posture the model attests (medium-high). Fix: consult tree-sitter comment/string spans (already produced by frob.lang) before substring matching; needle hits fully inside comment spans are dropped (string literals are subtler -- keep string hits for languages where code-in-string is an exec vector, e.g. eval payloads, but drop pure-comment hits everywhere). Litmus: comment-only fixture must NOT fire; code fixture still fires; the T-0151/T-0201 self-match tests stay green. Note duplicate-line issue too: the same site was reported twice (pilot gap 12) -- dedupe observations by (file,line,kind) while in there.

<!-- ticket:T-0210 -->
```yaml
id: T-0210
title: frob test package-fallback treats pytest exit 5 (no tests collected) as FAIL
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/testing/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 aprog-private: editing a file in a package with no tests (activities/git-heist/) makes frob test --base HEAD~1 report [FAIL] python exit=5. pytest exit 5 = collected 0 tests; the package fallback should degrade to the same neutral nothing-touched-selects-any-test outcome the empty-selection path prints. Regression test: fixture package with a source edit and zero tests -> PASS/neutral, not FAIL.

<!-- ticket:T-0211 -->
```yaml
id: T-0211
title: selfconform warns '<repo>/src/frob does not exist' in every non-frob repo
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/strata/_selfconform.py
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 (all 3 repos): the warning prints in every sibling repo while self-conformance PROVED still appears; the checks DO run (verified by falsifiability probes) but the stale frob-self path assumption reads as 'this proof is vacuous' -- trust-eroding. The SYS102 unmodeled join is frob-self-specific (_PACKAGE_ROOT); it should detect it is not in the frob repo and skip silently (one DEBUG line), not warn.

<!-- ticket:T-0212 -->
```yaml
id: T-0212
title: DOC002 slugger disagrees with GitHub anchor algorithm in both directions
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- src/frob/docs/**
- tests/**
- docs/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 lograder (7 DOC002 errors, most error-prone adoption step): 'Output & layouts' -> GitHub #output--layouts vs frob #output-layouts; 'Public/Private Boundary' -> GitHub #publicprivate-boundary vs frob #public-private-boundary. Punctuation runs collapse differently, so anchors satisfying DOC002 can 404 on GitHub and vice versa. Fix: implement GitHub's slug algorithm exactly (test against a table of tricky headings) or accept both forms; T-0165's nearest-anchor suggestions must use the corrected slugs.

<!-- ticket:T-0213 -->
```yaml
id: T-0213
title: COV001 short message says 'undocumented' for symbols that have docstrings
state: queued
kind: ux
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 lograder: COV001 flags DeveloperException/StaffException which HAVE docstrings -- rule means 'no frob:doc edge'; long-form message is correct, short line is wrong and misleads adopters into thinking docstrings satisfy it. Align the short message with the long form.

<!-- ticket:T-0214 -->
```yaml
id: T-0214
title: COV002 close-before-commit catch-22 turns covered changes into hard errors
state: queued
kind: ux
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- src/frob/tickets/**
- docs/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 aprog-public: closing the covering ticket while its strata file is still uncommitted turned every symbol in the file into 'changed with no open ticket' (30 hard errors) which vanish after commit. Either honor recently-done tickets' frob:ticket references for working-tree changes (grace window until commit) or make frob ticket close warn when the covering scope still has uncommitted changes, and document commit-then-close ordering in the playbook. Relates to T-0176 land (which enforces the safe order mechanically).

<!-- ticket:T-0215 -->
```yaml
id: T-0215
title: non-pytest evidence channel for docs/design tickets + close-from-queued hint
state: in-progress
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/tickets/**
- src/frob/app/**
- tests/**
- docs/modules/tickets.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 (gap 10) + coordinator experience this session (T-0167/T-0185/T-0186 all needed drift-lock tests written solely to satisfy close): frob ticket close accepts only pytest node ids. Add a vetted evidence alternative for docs/design tickets -- e.g. --evidence-cmd 'command' whose exit 0 is recorded with its output digest, or gate-based evidence referencing a rule that must be absent/present -- WITHOUT weakening code tickets (kind-gated: only docs/design kinds may use it). Also: close on a queued ticket errors InvalidTransition with no hint -- name the remedy (frob ticket start) in the message. And frob ticket start on an in-progress ticket errors InvalidTransition too -- make it idempotent or hint that it is already started (coordinator hit this on T-0169).

<!-- ticket:T-0216 -->
```yaml
id: T-0216
title: graph build never names the malformed file
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/graph/**
- src/frob/lang/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 aprog-private: malformed=1 in build output, persists across cache flush, no way to find WHICH file (no verbosity flag on the subcommand). Print path + parse error at WARN when malformed>0. Trivial but blocks users from fixing their own files.

<!-- ticket:T-0217 -->
```yaml
id: T-0217
title: sys plan/doc log raw pre-discharge threat counts that contradict the PROVED
  verdict
state: queued
kind: ux
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/strata/**
- src/frob/app/sys_runner.py
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 (gap 13): 'threat: evaluated ... -> 13 violation(s)' logs right before '0 obligation tickets / PROVED' -- the 13 is the pre-discharge obligation count, not live violations. Rename the log line (obligations evaluated, N discharged, 0 residual) or demote to DEBUG; contradictory-looking output erodes trust in PROVED.

<!-- ticket:T-0218 -->
```yaml
id: T-0218
title: graph build reports edges=0 on cache-hit runs while the loaded graph has edges
state: queued
kind: ux
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/graph/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 (gap 14): build counter means newly-parsed edges, so cache-hit runs print edges=0 followed later by load_graph: ... 60 edges. Rename the counter (new_edges=) or report total after load.

<!-- ticket:T-0219 -->
```yaml
id: T-0219
title: secrets scan misses adjacent sk-live key and placeholder-phrase fakes
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/gates/_secrets.py
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P2 (lograder/aprog-public/aprog-private, 2026-07-18). Pilot P2 aprog-private (gap 15): SEC001 flagged a fake Slack token but MISSED the sk-live-... key on the adjacent line (detection gap -- the miss matters more than any false positive), and the fake-marker heuristics missed obvious placeholder phrasing ('real-slack-token-here' contains no recognized fake word). Fix both directions: audit the provider table against the fixture file that produced the miss (why did sk-live- not match -- prefix table or format constraint?), and extend placeholder recognition ('...-here', 'your-', 'insert-', 'changeme') with fixtures. Coordinate with T-0190 (GitHub-unflaggable fixtures) so new fixtures satisfy both constraints.

<!-- ticket:T-0220 -->
```yaml
id: T-0220
title: 'T-0176 scope gap: src/frob/__main__.py missing from declared scope'
state: queued
kind: docs
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
T-0176's scope listed src/frob/tickets/**, src/frob/app/**, tests/**, docs/modules/tickets.md, tickets.md but omitted src/frob/__main__.py -- every prior ticket-subcommand-adding ticket (e.g. T-0162) explicitly included src/frob/__main__.py in scope, since the ticket subcommand argparse wiring lives there, not under src/frob/app/. T-0176 needed exactly that (frob ticket land's --worktree/--dry-run argparse registration) and could not deliver a usable CLI command without it. Waived SCOPE001 at src/frob/__main__.py in T-0176's commit rather than expanding scope unilaterally; this ticket exists to note the gap for future ticket-scope authoring (mechanically: any ticket adding a new frob subcommand should include src/frob/__main__.py in scope up front).

<!-- ticket:T-0221 -->
```yaml
id: T-0221
title: frob vet <lockfile> misparses path arg and exits 0 on ERROR
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/vet/**
- src/frob/app/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 3: frob vet uv.lock -> 'no supported lockfile under /repo/uv.lock' + ERROR LockfileUnsupported + EXIT 0. Two bugs: the path arg is treated as a directory root only (a lockfile path should be accepted), and the error exit code is lost (exit-0-on-error is gate-poisoning, same vacuous-pass doctrine as T-0184). Regression tests for both.

<!-- ticket:T-0222 -->
```yaml
id: T-0222
title: per-node capability excuse channel + missing needles (fs-read, uvicorn bind,
  pyo3 import)
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/strata/**
- src/frob/vet/_capability_registry.py
- tests/**
- docs/strata/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 5 (HIGH for adoption; 6 residual gaps across graphite+feldspar trace here): real-but-scanner-invisible capabilities force permanent SYS101 red or dishonest under-declaration -- may ffi on a pyo3-import node, may net for uvicorn.run, may fs for Path.read_text are all 'declared but never observed'. Fix both sides: (a) BenignCapability-style per-node excuse with a written reason (relates to T-0174 waiver channel -- coordinate, do not duplicate); (b) add the missing needles: fs-read (Path.read_text/open-for-read), socket/uvicorn bind, compiled-extension import as ffi observation. Litmus per needle per T-0182 discipline.

<!-- ticket:T-0223 -->
```yaml
id: T-0223
title: THREAT003 CWE-78 discharge impossible in foreign-less library models
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/strata/**
- tests/**
- docs/strata/threat.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 8 (medium-high): a library repo with no foreign node (feldspar) declaring may exec cannot discharge CWE-78 -- the demanded claim form is NoFlow(foreign src -> node) and no foreign source exists; frob sys plan --apply then mints permanently unclosable tickets (feldspar T-0009/T-0010 left queued as evidence). Add a library-mode discharge form: an argv-confinement assume against the outermost caller, or an explicit no-foreign-sources model-level fact that discharges the foreign-path obligation family with a written reason.

<!-- ticket:T-0224 -->
```yaml
id: T-0224
title: frob sys doc matrix prints PROVED (L4) for claims that were only ASSUMED
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/strata/**
- src/frob/app/sys_runner.py
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 9 (medium, overstates assurance): audit summary says {proved: N, assumed: M} but the matrix rows for assumed CWE discharges read PROVED (L4). Add a distinct ASSUMED status in the matrix rendering; a claim resting on an assume must never print as PROVED. Regression fixture: model with one proved and one assumed claim, assert distinct labels.

<!-- ticket:T-0225 -->
```yaml
id: T-0225
title: TEST003 fires on design/ dir; strata ids need e2e-binding obligation not unit/integration
  gates
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- src/frob/lang/_walk_strata.py
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 10: T-0168 exempted .strata from TEST001/TEST002 but TEST003 ('interface design has 0 integration tests') still fires on the design dir (graphite +16 findings). Per the refs, system ids bind kind=e2e. Decide + implement consistently with T-0168: exempt design artifacts from TEST003, and (design decision, document it) whether a SYS-family obligation should demand e2e bindings for flows instead.

<!-- ticket:T-0226 -->
```yaml
id: T-0226
title: utility/non-transitive flow marking -- SYS003 hub edges destroy true noflow
  claims
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/strata/**
- strata-core/src/parse.rs
- docs/strata/**
- tests/**
- design/frob.strata
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 11 (expressiveness): graphite had to withdraw a TRUE claim ('TUI never crosses HTTP') because SYS003 forced declaring tui->core (logging import) and core->server (entrypoint hosting), and reachability closure then refutes the noflow through the hub. Add a flow attribute (utility / no-transit) excluded from noflow transitive closure, or claim-level path exclusions; litmus pair: hub edge marked utility keeps the noflow claim provable, unmarked refutes it. Grammar change -> tmLanguage drift-lock will fire.

<!-- ticket:T-0227 -->
```yaml
id: T-0227
title: gitio treats untracked gitlink/directory as file (Errno 21 warning spam)
state: done
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/gitio.py
- tests/**
- tickets.md
evidence:
- tests/test_gitio.py::TestWorkingDiff::test_untracked_directory_is_skipped_not_read_as_file
- tests/test_gitio.py::TestWorkingDiff::test_covers_committed_staged_unstaged_and_untracked
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 12: graphite has .claude/worktrees/lithos (gitlink); every frob check/test warns 'could not read untracked file ...: [Errno 21] Is a directory'. Skip directories/gitlinks from ls-files --others handling; regression test with an untracked dir.

## Done report

Changed:
- src/frob/gitio.py -- `working_diff`'s untracked-file loop now checks
  `abs_path.is_dir()` before calling `_count_lines` and skips with a
  DEBUG log line (not WARNING) for untracked gitlinks / nested-worktree
  directories that `git ls-files --others --exclude-standard` lists as a
  path but that are not readable as files. Previously this hit
  `_count_lines`'s `OSError` handler with `[Errno 21] Is a directory` and
  logged a WARNING for every such entry on every `frob check`/`frob test`
  invocation in a repo with an untracked nested worktree/gitlink.

Evidence:
- tests/test_gitio.py::TestWorkingDiff::test_untracked_directory_is_skipped_not_read_as_file
  (new regression test: builds a repo with a genuine untracked nested git
  checkout under `nested-worktree/`, asserts `working_diff` succeeds,
  excludes the directory's path from `diff.hunks`, and asserts no
  "could not read untracked file" WARNING was logged)
- tests/test_gitio.py::TestWorkingDiff::test_covers_committed_staged_unstaged_and_untracked
  (existing untracked-file coverage, still green -- confirms plain
  untracked files are unaffected by the directory-skip check)
- `uv run pytest tests/test_gitio.py -q` -> 13 passed
- `uv run pytest --collect-only -q tests/test_gitio.py::TestWorkingDiff` -> 5 collected
  (confirms the new test id above resolves)
- `uv run frob test --base main` -> touched=5 selected tests/test_gitio.py
  (+ both TestWorkingDiff untracked cases explicitly) -> PASS exit=0
- `ruff check src/frob/gitio.py tests/test_gitio.py` and
  `uv run ruff check src/frob/gitio.py tests/test_gitio.py` -> both
  "All checks passed!" (both-ruff stable per playbook section 12)
- `uv run ty check src/frob/gitio.py` -> "All checks passed!"

Filed: none (no out-of-scope work found)

Note: after this ticket's initial pass, `git merge main` pulled in a large
unrelated batch (T-0157 secrets-scan gate, extending-guides docs, etc.).
Re-ran `make core`, re-ran `uv run frob ticket sweep T-0227` (pre-work
sweep timestamp must postdate the merge per PRE001), re-recorded evidence
via `uv run frob ticket evidence T-0227 <ids>`, and re-verified
`uv run pytest tests/test_gitio.py -q` (13 passed) and
`uv run frob test --base main` (PASS) against the merged tree before
finishing. One line the merge exposed: an unrelated pre-existing assert in
`tests/test_gitio.py` (`TestWorkingDiff::test_covers_committed_staged_unstaged_and_untracked`,
the `assert files == {...}` literal-set comparison) started tripping
PERF003 under the post-merge gate state; added
`# frob:waive PERF003 reason="single set comprehension over hunks compared
by == to a fixed 4-item literal set, not a nested join"` on that line
(tests/** is in this ticket's scope) rather than leave a new unwaived
violation sitting in a file this ticket touches.

Gates: `uv run frob check --ticket T-0227` (post-merge, post-`make core`)
-> gates FAIL with 3 unwaived violation(s) (193 waived), all pre-existing
and out of scope: COV003 on T-0168 (stale evidence id, unrelated ticket),
TEST006 (no coverage stamp -- campaign-wide, instructed to ignore), and
PERF004 on `src/frob/tickets/_land.py:67` (untouched file). Confirmed via
`grep '\[gates\]' <check output>` that no remaining unwaived violation
references `gitio.py` or any line I added outside the one PERF003 waived
above. `ruff check` / `uv run ruff check` on `src/frob/gitio.py` and
`tests/test_gitio.py` both report "All checks passed!"; `uv run ty check
src/frob/gitio.py` reports "All checks passed!".

<!-- ticket:T-0228 -->
```yaml
id: T-0228
title: check summary conflates errors and warnings ('pass ... 987 violation(s)')
state: queued
kind: ux
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/app/check_runner.py
- src/frob/gates/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 13 (all 3 repos; honesty risk): 'pass gates 987 violation(s), 0 waived' on exit 0, 'pass frob-cycle 1 cycle found', and failing lines counting warn-class findings as violations. Split every summary line into N error(s), M warning(s), K waived; never label warn findings violations on a passing gate. Builds on T-0202's output work.

<!-- ticket:T-0229 -->
```yaml
id: T-0229
title: polyglot check-type default silently skips gates then reports clean PASS
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/app/**
- src/frob/process/**
- tests/**
- docs/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 14 (HIGH -- a repo can look enforced while unenforced): lithos frob check warned 'python checks (gates included) NOT running' then printed [PASS] 0 errors 0 warnings exit 0 -- the obligation system never ran. Fix: run all detected stages by default in polyglot repos; if that is too slow, the unpinned-polyglot state must be a FAILING finding, not a warning contradicted by the PASS line. Regression: polyglot fixture repo, unpinned -> nonzero exit or all stages run.

<!-- ticket:T-0230 -->
```yaml
id: T-0230
title: PERF00x findings anchor to enclosing def line, not the offending statement
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/perf/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 15: lithos audit.py:450 PERF002 while the .index() calls sit at 465-466; rust conformance.rs:31 PERF003 points at the fn signature. Report the call-site line. Feeds T-0161 (heuristic fixes) -- coordinate. Regression fixtures asserting the exact reported line.

<!-- ticket:T-0231 -->
```yaml
id: T-0231
title: 'small CLI/UX batch: --version flag, sys plan dry-run label, DOC001 hint for
  missing docs root'
state: queued
kind: ux
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/__main__.py
- src/frob/app/**
- src/frob/gates/**
- src/frob/strata/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gaps 16/17/18 batched: (a) frob --version -> argparse error; add version output from package metadata. (b) frob sys plan without --apply prints 'compiled 1 obligation ticket(s)' with no dry-run label and no --apply mention -- say DRY RUN and name the flag. (c) DOC001 hint says 'link it from docs/index.md' in repos with no docs/index.md (lithos x256) -- resolve the configured/existing docs root or suggest creating one. Three small fixes, one ticket, tests each.

<!-- ticket:T-0232 -->
```yaml
id: T-0232
title: per-gate timing attribution shared/wrong; concurrent frob runs contend on .frob
  db
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- src/frob/graph/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 20: graphite shows secrets=39.71s sys=39.71s tickets=39.69s (identical; 3.6s when quiet) -- shared scan time is attributed to every gate; stages balloon ~56s while a frob vet runs concurrently in the same repo (db contention). Attribute shared scans once (report separately), and check .frob cache.db locking behavior under concurrent invocations (WAL was added once before -- verify it covers this path).

<!-- ticket:T-0233 -->
```yaml
id: T-0233
title: broken frob:doc target suppresses other coverage findings on the same file
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 21 (correctness): feldspar had DOC002 anchor-less targets; fixing them UNMASKED 6 previously-unreported COV001s on the same files -- a broken doc edge was counting as coverage. A frob:doc edge that fails to resolve must not satisfy COV001. Regression: fixture with a broken edge asserts COV001 still fires.

<!-- ticket:T-0234 -->
```yaml
id: T-0234
title: generated-file marker respected by coverage gates (COV001 on generated sources)
state: queued
kind: ux
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- src/frob/graph/**
- docs/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18). P1 gap 23: graphite frontend/src/api/api.generated.ts draws COV001 doc-edge demands (its repo ticket T-0006 documents the dead end). The [graph] excludes leaf exists but repos want generated code IN the graph (xref) yet exempt from doc/test obligations. Add a generated marker (glob list in frob.toml, or filename pattern *.generated.*) that COV/TEST gates respect while graph/xref still see the symbols.

<!-- ticket:T-0235 -->
```yaml
id: T-0235
title: exhaustive log/print call-site classification across src/frob (T-0202 follow-up)
state: queued
kind: ux
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/**
evidence: []
attachments: []
acceptance: []
threat: null
```
T-0202 fixed the check-path log-level bug (stdout handler defaulted to DEBUG unconditionally) and demoted the per-symbol/per-violation INFO calls found in gates/graph along that path. It did not exhaustively classify every _log./print( call site repo-wide (~1016 sites across src/frob) into keep-INFO/demote-DEBUG/convert-print as the ticket's enumerate-first instruction asked -- only src/frob/{gates,graph,check,app/check_runner.py,logging} got a full pass; the other 26 files under src/frob/app/ (89 INFO, 125 ERROR, 46 print call sites) and all non-scope dirs (strata 27, vet 17, fuzz 6, dup 5, tickets 4, testing 3, perf 3, lang 3, serve 2, arch 2, stats 1, release 1, policy 1, mutate 1, cve 1) were only sampled, not individually classified. Do the full pass and produce the classification table T-0202's Done report deferred.

<!-- ticket:T-0236 -->
```yaml
id: T-0236
title: PRE001 stale-sweep churn in the multi-agent loop -- land should refresh the
  sweep
state: queued
kind: ux
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/tickets/**
- src/frob/gates/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Three consecutive reviews (T-0181, T-0203, T-0202) REJECTed solely or partly on a stale PRE001 pre-work sweep, caused not by implementer negligence but by main moving between implementation and review in a multi-agent loop -- any unrelated landing that touches a ticket's scope globs invalidates its recorded sweep. Fix: frob ticket land refreshes the sweep against the post-merge state automatically before close (it already validates evidence/done-report pre-merge; add sweep-refresh as a post-merge, pre-close step), and frob check --ticket's PRE001 message should say when the staleness is due to out-of-scope-agent drift (compare sweep tree hash provenance) vs a genuinely un-swept scope change. Tests: land a ticket whose sweep predates an unrelated main landing; assert land succeeds and the recorded sweep is fresh.

<!-- ticket:T-0237 -->
```yaml
id: T-0237
title: frob:tests edge code endpoints and kind= attr are not gate-verified
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/gates/**
- src/frob/graph/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Found while writing T-0159's extending guides. tests/unit/test_strata_tmlanguage.py:13 declares 'frob:tests strata-core/src/parse.rs::parse_program kind="drift"'. Two problems, neither caught by any gate: (1) the code-side endpoint parse.rs::parse_program does not resolve -- frob.lang's Rust walk qualnames the symbol Parser.parse_program -- yet no DRIFT002 fires; an identical dead endpoint on a frob:describes edge DOES fire DRIFT002 (observed during T-0159: a describes edge to parse.rs::parse_program produced 'DRIFT002 ... gone' until corrected to Parser.parse_program). frob:tests edges appear exempt from endpoint resolution, so a renamed/deleted code symbol silently orphans its test-evidence edge. (2) kind="drift" is not in graph.dsl._TESTS_KINDS (unit/integration/e2e) yet is not reported as a MalformedDirective. Either widen _TESTS_KINDS deliberately or reject unknown kinds loudly; and run frob:tests code-side endpoints through the same DRIFT002 resolution describes edges get. (Refiled: first draft was lost in a tickets.md ledger splice during T-0159's concurrent-agent merge.)

<!-- ticket:T-0238 -->
```yaml
id: T-0238
title: frob outline has no Rust adapter though frob.lang parses Rust
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/outline/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Found while writing T-0159's extending guides: 'frob outline strata-core/src/parse.rs' errors with 'No outline adapter for this file extension' even though frob.lang extracts 151 symbols from the same file (dispatching path=strata-core/src/parse.rs to grammar=rust). The outline adapter registry does not cover every language frob.lang supports; either add the missing adapters (rust at minimum, check c/cpp/tsx too) or have outline fall back to the frob.lang symbol walk so the two language registries cannot drift apart. (Refiled: first draft was lost in a tickets.md ledger splice during T-0159's concurrent-agent merge.)

<!-- ticket:T-0239 -->
```yaml
id: T-0239
title: graph/gates scan gitignored nested git worktrees -- 73 pct wasted work
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/graph/**
- src/frob/lang/**
- src/frob/excludes.py
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from malmberg pilot P3 (/mnt/c, 2026-07-18). Malmberg pilot (HIGH): .claude/worktrees/agent-* checkouts made graph build scan 536 files/3007 symbols vs 144/925 real -- 73 pct of parse/gate work on stale copies; full check 9m47s -> 3m35s after manual exclude. Fix: skip gitignored paths and any directory containing a .git file/dir by DEFAULT (not per-repo config); regression fixture with a nested checkout.

<!-- ticket:T-0240 -->
```yaml
id: T-0240
title: frob ticket sweep unbounded on real scopes -- ignores excludes, walks venvs,
  nonsense xref stems
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/tickets/**
- src/frob/gates/**
- src/frob/dup/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from malmberg pilot P3 (/mnt/c, 2026-07-18). Malmberg pilot (HIGH): sweep on an 8-glob scope never completed on /mnt/c across 5 attempts (>13 min; /proc fd sampling showed it inside .claude/worktrees/*/.venv site-packages); identical repo on Linux fs: 5.2s. It ignores [graph] exclude; xref_hits derives nonsense symbols from glob stems (**, __init__, README); SIGINT prints bare KeyboardInterrupt. Also fold in: PRE001 catch-22 on slow mounts (scope edit demands re-sweep which is this unbounded op) and scope_digest env-sensitivity (hashes snapshot file-hashes so a sweep record cannot be transplanted between identical-content checkouts -- consider content-digest keying). Fix: honor excludes + gitignore, cap/skip venv trees, derive xref terms from real symbols only, clean interrupt message.

<!-- ticket:T-0241 -->
```yaml
id: T-0241
title: 'ticket scope parsing: comma-joined strings match nothing, dir/ prefixes dont
  glob, ledger not implicit'
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/tickets/**
- src/frob/gates/**
- tests/**
- docs/modules/tickets.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from malmberg pilot P3 (/mnt/c, 2026-07-18). Malmberg pilot (HIGH correctness -- same class as T-0181 round-1 incident): a scope entry 'a/,b/,c/' is treated as ONE fnmatch glob matching nothing -- SCOPE001 fired on every touched file and prior sweeps recorded against ZERO files (digest sha256 of empty; dup/xref vacuous pass). Also 'design/' does not match (needs design/**), and tickets.md itself is flagged out-of-scope though frob edits it on every ticket op. Fix: reject or split comma-joined entries at frob ticket new (loud validation), treat dir/ as dir/**, make tickets.md implicitly in-scope for every ticket. Regression tests for all three.

<!-- ticket:T-0242 -->
```yaml
id: T-0242
title: 'strata runner: frob test should invoke sys audit natively for touched .strata
  files'
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/testing/**
- src/frob/strata/**
- tests/**
- docs/modules/testing.md
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from malmberg pilot P3 (/mnt/c, 2026-07-18). Malmberg pilot: touching a .strata file breaks frob test with NoRunner (language strata has selected tests but no [[test.runner]]); workaround registering frob sys audit as runner demands a dummy {ids} placeholder (BadRunnerSpec otherwise). Fix: native strata selection path -- touched .strata invokes sys audit without per-repo runner config; placeholder validation should accept runners that take no ids. Relates T-0149 (closed, per-repo config path) -- this makes it zero-config.

<!-- ticket:T-0243 -->
```yaml
id: T-0243
title: cache.db not invalidated across frob/parser upgrades
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/graph/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from malmberg pilot P3 (/mnt/c, 2026-07-18). Malmberg pilot (medium): a stale cache served 2830 symbols where a fresh parse of identical sources gave 3007 -- cache survived a frob upgrade with changed parser behavior. Include the frob version + grammar/parser fingerprint in the cache key so any upgrade invalidates cleanly. Regression: bump a fake version constant in test, assert cold rebuild.

<!-- ticket:T-0244 -->
```yaml
id: T-0244
title: 'embedded-code blind spot: JS/HTML inside python string literals invisible
  to every scanner'
state: queued
kind: feature
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/vet/**
- src/frob/strata/**
- src/frob/lang/**
- docs/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from malmberg pilot P3 (/mnt/c, 2026-07-18). Malmberg pilot (design-level): the product dashboard is 5400 lines of inline HTML/JS inside a python module -- invisible to capability scanning even post-T-0169. Options to evaluate honestly: (a) detect large embedded html/script string literals and run the TS/JS needle pass over their content; (b) an explicit OutOfScope/managed-style marker declaring embedded-frontend content with a reason, so the blind spot is at least DECLARED not silent. Start with (b) (cheap, honest), spike (a).

<!-- ticket:T-0245 -->
```yaml
id: T-0245
title: 'mount-aware performance: per-file stat storms and sqlite contention on /mnt/c
  (13-60x tax)'
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/graph/**
- src/frob/gates/**
- src/frob/gitio.py
- tests/**
- docs/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Filed from malmberg pilot P3 (/mnt/c, 2026-07-18). Malmberg pilot dedicated /mnt/c findings: same content, same machine -- graph cold 7.4s vs 1.1s, warm up to 31s vs 0.5s, gates-only 19-47s vs 7.9s; ~0.5ms/stat under load (11.3k stats in 90s of sweep strace); sqlite commit 8.2ms vs 2.3ms; concurrent frob processes drove D-state stalls with no lock feedback. Fixes: batch directory walks (os.scandir reuse), cut redundant per-file stats (trust one snapshot pass), sqlite busy_timeout + a visible waiting-on-lock message, and a docs page on WSL-mount expectations. Acceptance: measured cold graph build on the malmberg /mnt/c checkout under 3s.

<!-- ticket:T-0246 -->
```yaml
id: T-0246
title: 'PERF003 correlation: unwind one level of call parens in _operand_names (f(x)
  == g(y) joins)'
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/perf/**
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
T-0161 round-2 review follow-up (non-blocking boundary found by the reviewer): a real nested join comparing derived values -- f(x) == g(y) with x,y the loop variables inside call parens -- does not fire because _operand_names only unwinds bare identifiers and one bracket-pair subscript (a[i-1] == b[j-1] works). Extend the unwinding one level of call parens, symmetric with the subscript handling; keep the attribute-access narrowing (its 4 sibling-loop FP sites are documented in T-0161's Done report). Regression: derived-value join fires; the 4 FP classes stay silent.

<!-- ticket:T-0247 -->
```yaml
id: T-0247
title: store grammar still missing on-deploy/observe/errors_total/panics_contained_by
  from node_prop
state: queued
kind: bug
origin: human
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- strata-core/src/parse.rs,docs/strata/surface.md,src/frob/strata/**,tests/**
evidence: []
attachments: []
acceptance: []
threat: null
```
found while working T-0166: docs/strata/surface.md's std.infra grammar block says store_prop := node_prop | engine | immutable | append_only | rpo, implying store accepts the FULL node_prop set. T-0166 closed the code/may gap (the one this ticket's scope named), but parse_store still has no branch for on deploy/observe/errors_total/panics_contained_by -- store_prop remains a real subset of node_prop, not the full union the grammar block literally claims. Either implement the remaining node_prop items on store (mirroring parse_node) or narrow the surface.md grammar line to enumerate the actual accepted subset instead of the misleading 'node_prop' alias.

<!-- ticket:T-0248 -->
```yaml
id: T-0248
title: grammar-affecting landings leave stale natives on main -- land/check must detect
state: queued
kind: bug
origin: agent
created: '2026-07-18'
blocked_by: []
parent: null
scope:
- src/frob/tickets/**
- src/frob/strata/**
- Makefile
- tests/**
- tickets.md
evidence: []
attachments: []
acceptance: []
threat: null
```
Incident during T-0156 review: T-0166 landed a parse.rs grammar change and design/frob.strata began using it, but main's built strata_core predated the change -- frob check reported SYS004 (design failed to load, suppressing SYS001 project-wide) until the coordinator manually ran make core + tool reinstall. Two fixes: (1) frob ticket land detects when the landed diff touches strata-core/**, frob-core/**, or any native-crate source and prints a LOUD post-land instruction (or optionally runs make core) before the final commit; (2) the SYS004 message should distinguish 'parse failed with unknown construct X' and hint that a grammar/native version mismatch is the likely cause when the construct is recognized by the python-side surface docs. Regression: fixture simulating a grammar-ahead-of-native state asserting the hint appears.
