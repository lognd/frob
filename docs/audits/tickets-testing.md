# Audit: accounting & test-selection layer (frob.tickets + frob.testing)

North-star: "if a ticket closes / a test-selection passes, the work was actually
done and actually tested." Verdict up front: **the layer does NOT enforce the
north-star.** It enforces a much weaker property -- "the ticket names at least
one test node id that currently EXISTS in the collected set, and carries a
'## Done report' heading." Whether that test passed, whether it exercises the
ticket's changed code at all, and whether the changed code even has a test are
all outside what any gate here checks.

---

## (A) What the close/evidence/land/sweep flow actually enforces, and how

**Recording evidence** (`add_evidence`, tickets/__init__.py:853; app path
`_apply_evidence`, ticket_runner.py:~662-736):
- Schema-validates each node id (non-empty, single-line, <=300 chars).
- Resolves each id against `collected` = union of `collect_python_tests` +
  `collect_rust_tests` node ids. Resolution = **membership in the
  `pytest --collect-only` / `cargo test --list` output** (i.e. the test was
  discovered), via `_matches_collected` (exact, or `f` matches `f[param]`).
- `collected=None` skips resolution entirely (schema only).
- Never runs the test. "Resolves" means "exists", not "passes".

**Closing** (`transition(..., DONE)`, tickets/__init__.py:812;
`_done_transition_guard` :767):
- Requires `ticket.evidence` non-empty AND `_has_done_report(body)` true.
- `_has_done_report` (:733) = any body line whose `.strip()` equals the literal
  `## Done report`. Heading presence only; content never inspected.
- Rejects `cmd:` evidence on a non-docs kind.
- Does **not** re-resolve evidence against collection, and does **not** run any
  test. A ticket whose recorded evidence has since been deleted/renamed still
  closes; COV003 catches that only later at `frob check` time, not at close.

**Landing** (`land`, tickets/_land.py:434; `_validate_closeable` :173):
- Precheck reuses the exact close preconditions (evidence non-empty + Done
  report heading + cmd-kind consistency) against the **worktree's** ledger.
- Then does git surgery: wip-commit, merge main into worktree, deletion-filter
  (`_unowned_deletions` outside `ticket.scope`), finalize draft id, close,
  squash-apply onto main, ledger splice. It **trusts the worktree ticket
  entirely** -- it never runs the ticket's evidence tests, never re-checks that
  evidence resolves against the merged tree, never verifies the Done report's
  claims against reality. `land` == "close + move commits", not "verify".

**Sweep** (`sweep_ticket`, gates/_prework.py:174) is a pre-work provenance
stamp (dup count, xref hits, scope digest). PRE001 only asserts a sweep exists
and its scope digest still matches. It is orthogonal to evidence and proves
nothing about tests.

**Test selection** (`select_tests`, testing/_select.py:293):
1. `_touched_symbols`: graph symbols whose span overlaps a changed hunk.
2. `_ripple_symbols`: symbols with a `USES_CONTRACT` edge into a touched symbol
   (one hop only).
3. From `TESTS` edges, pick tests whose tested-side symbol is touched / its
   enclosing class / its file / its package prefix.
4. Touched files that are themselves test files are selected directly.
5. `_collect_unbound`: any touched file with no bound test gets the fallback
   (default `package` -> run that dir's package; `suite` -> all; `warn` -> skip).
   A file whose extension has **no known language** is logged and skipped with
   no fallback at all.

Runners (`run_selected`, testing/_runners.py:486) execute selection and return
pass/fail (`TestRunReport.ok`) -- **but this outcome is never fed back into
evidence recording.** `frob test` and `frob ticket evidence` are fully
decoupled flows.

---

## (B) FALSE-NEGATIVE / EVASION findings (the priority class)

Answers to the posed questions:

- *Does close VERIFY the evidence tests PASS, or just that the id resolves?*
  **Neither, at close time -- it only checks the id is non-empty and once
  resolved.** Even COV003/`add_evidence` only check the id was *collected*
  (exists), never that it *passed*. **A ticket can close green with evidence
  pointing at a currently-FAILING test.** Collection lists failing and skipped
  tests identically to passing ones.

- *Can a ticket close with hollow evidence (an id that resolves but tests
  nothing)?* **Yes, trivially.** Evidence has no binding to the ticket's scope
  or changed code. `frob ticket evidence T-XXXX tests/test_unrelated.py::test_x`
  where `test_x` is any pre-existing passing test satisfies every gate. Nothing
  requires the evidence test to touch the code the ticket changed.

- *Can a Done report be faked (heading-only check)?* **Yes.** `_has_done_report`
  matches the literal heading line; an empty `## Done report\n` section passes.

- *Does `frob ticket land` verify claims against reality?* **No.** It trusts the
  worktree ticket; it runs zero tests.

- *Can touched-set selection MISS tests that should run?* **Yes**, several ways
  (see D-06, D-07, D-08 below): config/data files, no-symbol changes across
  language boundaries, and the single-hop ripple horizon.

### Ranked TOP 5 (highest north-star risk first)

**D-01 [HIGH] Close/land never verify evidence tests PASS -- only that they were
collected.** `_done_transition_guard` (tickets/__init__.py:767) +
`_validate_closeable` (_land.py:173) + `_evidence_collected`
(gates/__init__.py:239). A collected id includes failing/errored/skipped tests
(`pytest --collect-only` and `cargo test --list` list them regardless of
outcome). Repro: record evidence on a red test, add `## Done report`, run
`frob ticket close T-XXXX` -> DONE. The entire accounting layer equates
"a test with this name exists" with "the work is proven". This is the single
biggest north-star hole.

**D-02 [HIGH] Evidence has no binding to the ticket's scope or changed symbols
-- any collected test closes any ticket.** `add_evidence` /
`_check_evidence_resolution` (tickets/__init__.py:884) and COV003
(gates/__init__.py:1253) validate resolution only, never that the evidence test
covers `ticket.scope` or a touched symbol. Repro: `frob ticket evidence
T-feature-x tests/test_logging.py::test_levels` (a stable, unrelated test) ->
closes. A dishonest/lazy agent closes real work with a rubber-stamp id. The
select-tests graph already knows which tests cover which symbols; close ignores
it entirely.

**D-03 [HIGH] `_has_done_report` is a heading-only check -- an empty Done report
passes.** tickets/__init__.py:733 and _land.py:52 (duplicated). No length, no
required subsections (no "what changed", "tests", "risks"). Repro: append a bare
line `## Done report` to a ticket body -> close/land precondition satisfied.
A fabricated/empty Done report is indistinguishable from a real one to every
gate.

**D-04 [HIGH] Config/data-file changes select ZERO tests silently.**
`_collect_unbound` (testing/_select.py:239) -> `extension_language(file)` returns
`None` for `.toml`/`.json`/`.yaml`/`.md`/etc.; the file is logged
`unknown language` and **skipped with no fallback**. Repro: change only
`frob.toml`'s `[[test.runner]]` command, or a data fixture, or a `.json` config
consumed at runtime -> `frob test` selects nothing and reports a neutral pass.
Silent under-testing of exactly the change class (config/data with no symbol)
the task flagged.

**D-05 [HIGH] `land` trusts the worktree report; it re-runs and re-checks
nothing.** _land.py:434. The only "reality" checks are git-shaped (deletion
filter, conflict detection). Evidence resolution is not even re-run against the
post-merge tree (it is run against the worktree's *pre-merge* collection state
only if the agent happened to run `frob ticket evidence` there). Repro: in a
worktree, hand-add a resolvable-but-unrelated evidence id + `## Done report`,
`frob ticket land` -> lands onto main with a `feat(...)` commit, no test ever
executed. A false Done report merges to main unchallenged.

### Remaining evasion findings

**D-06 [MEDIUM] No-symbol source edits under-select via graph gaps.**
`_touched_symbols` (testing/_select.py:52) only flags symbols whose span
overlaps a hunk. A change to module-level code *between* symbols (imports,
module constants, decorators applied at import, a top-level side-effecting call)
overlaps no symbol span -> `touched_symbols` empty for that file. It still lands
in `touched_files` so `_collect_unbound`'s package fallback saves the `.py`
case -- but only because the default is `package`; under `fallback = "warn"`
(a supported mode) such a change selects zero tests. Repro: set
`fallback = "warn"`, edit a module-level constant that changes behavior ->
no tests selected.

**D-07 [MEDIUM] Ripple horizon is a single `USES_CONTRACT` hop.**
`_ripple_symbols` (testing/_select.py:65) collects only direct dependents of a
touched symbol. A caller two hops away (A tests-covered, A calls B, B calls
changed C, no test directly covers C or B) is never selected. Repro: change a
leaf helper C used only transitively; its own covering test is missing; the
integration test that covers A is two hops up and never selected. Genuine
behavior change ships with a green touched-set run.

**D-08 [MEDIUM] `add_evidence(collected=None)` records evidence with NO
resolution check.** tickets/__init__.py:857,884. `new_ticket --evidence`
(tickets/__init__.py:264) also only schema-validates -- it never resolves. So
`frob ticket new --evidence "tests/does_not_exist.py::test_ghost"` stores a
bogus id. It is caught later only if the ticket reaches DONE and `frob check`
runs COV003; a ticket parked in-progress carries unresolved evidence silently.
The docstring claims a typo "can never sneak into evidence" -- false for the
`new_ticket` and `collected=None` paths.

**D-09 [MEDIUM] Evidence can be lost / downgraded on land splice (T-0357
class).** `_newer` (_land.py:58) breaks a same-id, same-state, same-Done-report
tie by `len(evidence)` then falls back to `b` (theirs). If two worktrees both
close the same id with disjoint evidence sets, the splice keeps ONE ticket's
evidence and silently drops the other's -- there is no union. Repro: two agents
close T-X with different evidence lists; land both; final ledger reflects only
one side's evidence, so COV003 coverage that existed is lost.

**D-10 [MEDIUM] `run_cmd_evidence` digest is not reproducible / not verified,
and the "docs-only" gate is the only thing standing between it and code
tickets.** tickets/__init__.py:929. The sha256 is over stdout only and is never
re-checked (COV003 explicitly does not re-run it, gates/__init__.py:249). For a
docs ticket, evidence is "a shell command exited 0 once". If
`CMD_EVIDENCE_ALLOWED_KINDS` is ever widened, or a ticket's kind is set to
`docs` for unrelated reasons, `cmd:true exit=0 sha256=...` (literally the shell
builtin `true`) is accepted as proof. Today bounded to docs kind, hence MEDIUM.

**D-11 [LOW] `_matches_collected` / `_evidence_collected` duplicated across
module boundaries and can desync.** tickets/__init__.py:840 vs
gates/__init__.py:239 -- deliberate (cycle-avoidance), acknowledged in the
docstring, but two copies of the resolution rule means a future change to
parametrized-id matching in one silently diverges from the other. No live bug;
flagged as the desync-risk the codebase's own NO-DUPLICATION rule warns about.

**D-12 [LOW] Deletion filter keys on `ticket.scope`, which the agent controls
and can over-broaden.** `_unowned_deletions` (_land.py:341) treats any deletion
inside `ticket.scope` as owned. `scope_matches` expands a bare `dir/` to
`dir/**`, so a ticket scoped `src/` silently authorizes deleting anything under
`src/`. An over-broad scope (`.` or a top-level dir) defeats the stale-base
deletion guard entirely. Repro: ticket scope `src/frob/`, worktree stale-base
drops an unrelated `src/frob/other/mod.py`; land does not flag it. Bounded by
requiring an over-broad scope, hence LOW.

---

## (C) FALSE-POSITIVE / soundness (things that could wrongly BLOCK honest work)

- `_is_neutral_outcome` (testing/_runners.py:472) correctly treats pytest exit 5
  (no tests collected) as non-failing, avoiding a spurious [FAIL] on
  package-fallback selections. Sound.
- `_cargo_env` / `_run_cargo_test_list` return `Err` (not a fabricated pass)
  when the PyO3 env is unavailable -- correct fail-closed posture.
- COV003 fires on a DONE ticket whose evidence id was legitimately renamed by a
  refactor. That is a real false-positive churn source, but it is the *intended*
  fail-closed direction and has a documented remedy (`frob test --collect`).
  Not a soundness defect, noted for completeness.
- `_drop_resurrected_ids` degrading an unreadable archive to empty (_land.py:225)
  is the one place a soundness gap leans permissive: if `tickets-archive.md` is
  malformed at land time, archive-resurrection prevention silently turns off.
  Low real-world trigger (malformed archive is itself loud elsewhere).

No false-positive found that would block genuinely-tested, genuinely-done work
under normal (default `package` fallback, well-formed ledger) conditions.

---

## (D) Per-component pessimistic verdict (RIGHT vs FAST)

- **tickets/__init__.py close/transition** -- NOT good enough for the north-star.
  It is FAST (no test execution) at the cost of being RIGHT: it cannot tell a
  proven ticket from one citing an unrelated green test with an empty Done
  report. The state machine and id-allocation halves are solid; the *evidence
  semantics* are the weak point.
- **tickets/_land.py** -- Solid as a git-choreography tool (deletion filter,
  splice, dry-run unwind are genuinely careful). As a *verification gate* it is
  hollow: it re-checks the same weak close preconditions and trusts the report.
  RIGHT for merge safety, absent for work-actually-done.
- **tickets/_models.py scope_matches** -- Correct and well-consolidated (single
  impl, comma-split, dir-glob expansion, implicit ledger). The only exposure is
  that scope is agent-controlled and feeds the deletion filter (D-12).
- **testing/_select.py** -- The most sophisticated piece, but structurally
  optimistic: single-hop ripple, symbol-span-only touch detection, and
  silent-skip of unknown-language files make it FAST but capable of selecting
  zero tests for real behavior changes. Under-testing is silent, which is the
  worst failure direction for a test selector.
- **testing/_runners.py / _collect.py** -- Genuinely careful (fail-closed on
  missing env, neutral exit-5 handling, native-fingerprint cache invalidation,
  nested-cwd collection). Their correctness is wasted because the pass/fail
  `TestRunReport.ok` they produce is never wired into evidence.

**Bottom line:** the layer is RIGHT about *bookkeeping* (ids, states, merges,
collection caching) and FAST-but-wrong about the one thing the north-star cares
about (*proof of work*). The smallest correct closing move is to make evidence
mean "this test covers a touched symbol AND passed", by (a) having `frob test`
write pass/fail results that `add_evidence`/close consume, and (b) binding at
least one evidence id to a touched/scope symbol via the graph the selector
already builds.

---

## (E) Concrete gaps/defects table

| ID | Sev | One-line repro | Site |
|----|-----|----------------|------|
| D-01 | HIGH | Record evidence on a red test + `## Done report`; `frob ticket close` -> DONE | gates/__init__.py:239; tickets/__init__.py:767 |
| D-02 | HIGH | `frob ticket evidence T-X tests/test_logging.py::test_levels` closes unrelated feature | tickets/__init__.py:884; gates/__init__.py:1253 |
| D-03 | HIGH | Append bare `## Done report` line -> close precondition met | tickets/__init__.py:733; _land.py:52 |
| D-04 | HIGH | Edit only `frob.toml`/a `.json` fixture -> `frob test` selects 0 tests, neutral pass | testing/_select.py:239,257 |
| D-05 | HIGH | Hand-add resolvable-unrelated id + Done heading in worktree -> `frob ticket land` merges, 0 tests run | tickets/_land.py:434,173 |
| D-06 | MED | `fallback="warn"`, edit module-level constant (no symbol span) -> 0 tests | testing/_select.py:52,233 |
| D-07 | MED | Change transitive leaf helper (2 hops from any test) -> not selected | testing/_select.py:65 |
| D-08 | MED | `frob ticket new --evidence tests/ghost.py::test_x` stores bogus id, no resolution | tickets/__init__.py:264,884 |
| D-09 | MED | Two worktrees close same id w/ disjoint evidence; land both -> one side's evidence dropped | tickets/_land.py:58 |
| D-10 | MED | Docs ticket: `frob ticket close --evidence-cmd true` accepted as proof | tickets/__init__.py:929; gates/__init__.py:249 |
| D-11 | LOW | Two copies of collected-match rule can desync | tickets/__init__.py:840 vs gates/__init__.py:239 |
| D-12 | LOW | Over-broad `scope: src/` authorizes deleting any `src/**` past the stale-base guard | tickets/_land.py:341 |

---

## Notes -- checked & correct (do not re-verify)

- Id allocation / draft-id / renumber / finalize_draft: the off-default-branch
  provisional-id mechanism and active+archive merged-max allocation are sound
  and defend against the T-0162/T-0140 collision classes as documented.
- `splice_ledger` archive-resurrection guard and non-tickets.md conflict abort
  paths are correct; `land`'s dry-run merge/abort/reset unwinding is genuinely
  symmetric with the real run.
- Collection caching: `_collection_cache_key` (content hash + native
  fingerprint) correctly invalidates on test-file edits and native rebuilds
  (T-0333); nested-cwd collection union (T-0317) is correct.
- Runner env fail-closed behavior (`_cargo_env`, `_runner_env_overlay`) and
  pytest exit-5 neutral handling are correct -- no fabricated passes there.
- `scope_matches` consolidation and comma/dir-glob normalization are correct and
  single-sourced.

## Notes -- skipped / skimmed (audit boundary)

- `tickets/clipboard.py` and `attach`/attachment paths: skimmed only; not on the
  close/evidence critical path.
- `tickets/_store.py` ledger parse/render internals (`_parse_ledger`,
  `_render_ledger`): read for interface, not line-audited for markdown
  round-trip edge cases -- a parse bug there would surface as a loud Err, not a
  silent false pass, so lower north-star risk.
- Rust symref resolution (`_module_path_to_symref`,
  `_integration_module_path_to_symref`): read; the documented
  `tests/<stem>/` submodule approximation is a known selection imprecision, not
  re-derived here.
- I did not execute the suite or reproduce D-01..D-12 live; findings are from
  reading the close/evidence/land/select/collect call graph end to end. Each
  repro is a construction from that reading, not an observed run.
- Graph construction (`build_graph`, `USES_CONTRACT`/`TESTS` edge emission) is
  upstream of this layer and treated as a trusted input; D-06/D-07 assume the
  graph is complete-as-built, and any missing edges there compound the
  under-selection independently.
</content>
</invoke>
