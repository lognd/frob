# Audit round 2: accounting & test-selection layer (post T-0398)

Re-audit AFTER the T-0398 evidence-integrity fix landed (commits 26eadf9,
476bc4c, 2d4ceb3, plus CLI wiring). Scope: `src/frob/tickets/**`,
`src/frob/testing/**`, evidence/close/land enforcement in
`src/frob/gates/__init__.py` and `src/frob/app/ticket_runner.py`. All CLI
claims read against `uv run frob` (0.31.0); bare `frob` is stale 0.9.0.

North-star: closing/landing a ticket must MEAN the work was tested, the tests
cover the changed code, and they passed.

---

## (A) Confirmed-fixed: D-01 .. D-12

Verified by reading the wired CLI call graph
(`_close`/`_apply_evidence`/`_land` -> `add_evidence`/`transition`/`land`),
not just the library. Fixes that are genuinely present:

- **D-01 (evidence must PASS, not just collect)** -- FIXED at record time and at
  land time. `_apply_evidence` (ticket_runner.py:969) computes `passing` via
  `_verify_ids_passing` (ticket_runner.py:868) which actually runs each id
  through `run_selected` (or a direct `pytest` fallback), and passes it to
  `add_evidence(..., passed=passing)`; `_check_evidence_passing`
  (tickets/__init__.py:973) rejects the batch with `EvidenceNotPassing` if any
  non-cmd id is absent from `passed`. Land re-runs via `_land_passed_fn`
  (ticket_runner.py:371) -> `_reverify_evidence_post_merge` (_land.py:570).
  **Caveat: enforced only at the moment evidence is recorded and at land -- see
  N-02 for the close-time hole.**
- **D-02 (evidence must bind to scope)** -- FIXED for the non-empty-scope case.
  `evidence_covers_scope` (gates/__init__.py:279) checks a TESTS-edge binding or
  an in-scope evidence file; `_covers_scope_for_ticket` (ticket_runner.py:691)
  feeds it into `transition(covers_scope=...)`, and `_done_transition_guard`
  (tickets/__init__.py:831) returns `EvidenceScopeUnbound` on `False`.
  **Caveat: bypassable via empty scope (N-01) and via self-declared test scope
  (N-04).**
- **D-03 (Done report substance)** -- SUPERFICIALLY fixed. Now routed through
  `has_substantive_done_report` (_models.py:201). But the thresholds are
  `_MIN_DONE_REPORT_LINES = 1` and `_MIN_DONE_REPORT_CHARS = 3` (_models.py:175)
  -- see N-05; three non-whitespace characters satisfies "substantive".
- **D-04 (config/data files select ZERO tests)** -- FIXED, but over-corrects.
  `_apply_unknown_language_fallback` (_select.py:283) now selects a suite-wide
  run across every known language. See N-07 for the over-selection cost.
- **D-05 (land trusts the worktree, re-runs nothing)** -- FIXED. `_land`
  (ticket_runner.py:406) supplies `collected`/`passed`/`covers_scope` closures;
  `_reverify_evidence_post_merge` (_land.py:570) re-resolves AND re-runs against
  the post-merge worktree, returning `NotCloseable` on any regression. Verified
  main is left untouched on failure (the squash-apply is downstream of the
  re-verify). **Caveat: merge/apply TOCTOU under concurrency, N-08.**
- **D-06 (module-level edit under `fallback=warn`)** -- FIXED via `force_package`
  in `_apply_fallback` (_select.py:246,264): a file the graph knows (has
  symbols) but whose hunk overlapped no symbol span is forced to `package` even
  under `warn`.
- **D-07 (single-hop ripple)** -- FIXED to a bounded 4-hop BFS (`_RIPPLE_MAX_HOPS
  = 4`, _select.py:69,72). See N-06 for the residual 5+-hop gap.
- **D-08 (`new --evidence` / `collected=None` records unresolved)** -- FIXED for
  the CLI: `_new` (ticket_runner.py:131) routes `--evidence` through
  `_apply_evidence`, which always collects and resolves. `collected=None` in the
  library still skips resolution but now WARNS loudly (`_check_evidence_resolution`,
  tickets/__init__.py:952).
- **D-09 (evidence dropped on splice)** -- FIXED. `_reverify_evidence_post_merge`
  re-checks the post-splice evidence, and `_union_evidence` (referenced
  _land.py:581) unions disjoint sets rather than dropping one side.
- **D-10 (cmd-evidence `true` for docs)** -- unchanged; still bounded to docs
  kind, digest still never re-verified. Restated as N-12 (LOW), no regression.
- **D-11 (duplicated collected-match rule)** -- FIXED. Single
  `matches_collected` in `_models.py:151`; gates and tickets both delegate.
- **D-12 (deletion filter keys on agent-controlled scope)** -- unchanged in the
  land deletion filter; but now that D-02 ALSO keys off `ticket.scope`, the
  agent-controlled-scope problem got WORSE, not better -- see N-01/N-04.

---

## (B) + (C) NEW findings (round 2)

### N-01 [HIGH] Empty `ticket.scope` disables the D-02 binding check entirely

- **Where**: `_covers_scope_for_ticket` (ticket_runner.py:691, guard at :714:
  `if not non_cmd or not ticket.scope: return None`), consumed by
  `_done_transition_guard` (tickets/__init__.py:831, which only rejects on
  `covers_scope is False`, never on `None`).
- **What's wrong**: `covers_scope=None` means "skip the scope-binding check."
  `_covers_scope_for_ticket` returns `None` whenever `ticket.scope` is empty.
  Scope is OPTIONAL at ticket creation -- `_new` (ticket_runner.py:112) never
  requires `--scope`, and `Ticket.scope` defaults to `()` (_models.py:279). So a
  ticket with no scope skips D-02 completely and closes on ANY collected+passing
  evidence id, exactly the rubber-stamp D-02 was created to stop.
- **Failure scenario**: `frob ticket new --title x --kind feat` (no `--scope`)
  -> `frob ticket start T-X` -> `frob ticket evidence T-X
  tests/test_logging.py::test_levels` (an unrelated, stable, passing test; it
  runs green so D-01 is satisfied too) -> add a 3-char Done report ->
  `frob ticket close T-X` succeeds. D-02 never fired because scope was empty.
  The overwhelmingly common lazy path (omit scope) is the fully-unbound path.
- **Fix direction**: treat empty scope as fail-closed for code-kind tickets --
  either require a non-empty scope to close a code ticket, or (better) when
  scope is empty derive the touched set from the ticket's own git diff /
  `frob:ticket`-annotated symbols and bind against THAT instead of returning
  `None`. At minimum, `None` for an empty-scope code ticket should block, not
  skip.

### N-02 [HIGH] `frob ticket close` (without `--evidence`) never re-runs tests; the pass-check is a stale record-time snapshot

- **Where**: `_close` (ticket_runner.py:731). It re-applies evidence only if
  `cfg.ticket_evidence_ids` is set (:753); otherwise it computes ONLY
  `covers_scope` (:767, a graph query, no test run) and calls
  `transition(DONE)`. `transition`/`_done_transition_guard`
  (tickets/__init__.py:862,796) check evidence-non-empty + Done report +
  covers_scope -- they never re-run tests. `passed` is verified once in
  `add_evidence` and is NOT persisted (evidence is a bare `tuple[str, ...]`,
  _models.py:280); nothing downstream re-checks it.
- **What's wrong**: the documented, normal workflow is `frob ticket evidence`
  then later `frob ticket close`. Between those two commands the working tree
  can change arbitrarily. Close trusts the record-time pass observation.
- **Failure scenario**: `frob ticket evidence T-X tests/test_foo.py::test_bar`
  while green (recorded, passes) -> edit `src/foo.py` to break `test_bar` (or
  edit the test) -> `frob ticket close T-X`. Close does not re-run; the ticket
  closes DONE with a now-RED evidence test. `frob check`/COV003 only checks the
  id still COLLECTS, never that it passes, so main carries a green DONE ticket
  over a failing test indefinitely (compounds into N-11). This directly
  violates the north-star: "closed" does not mean "currently passing."
- **Fix direction**: at close, re-run the ticket's non-cmd evidence ids (reuse
  `_verify_ids_passing`) the same way `land` already does via
  `_reverify_evidence_post_merge`, and reject on any non-passing id. Close and
  land should share one "re-verify against current tree" path; today only land
  has it.

### N-03 [HIGH] Vacuous tests count as "passed" -- exit-0 is the only pass criterion

- **Where**: `_verify_one_bucket_passing` (ticket_runner.py:908): `if run.is_ok
  and run.danger_ok.ok: return frozenset(items)`. `run_selected` /
  `_run_pytest_directly` (ticket_runner.py:950) equate pass with process exit 0.
  No assertion-count, coverage-delta, or mutation check exists anywhere in the
  evidence path.
- **What's wrong**: a test that asserts nothing (or whose body is `pass`, or
  that only exercises code without asserting on the result) exits 0 and is
  recorded as passing evidence. This is the vacuous-test class the reviewer
  repeatedly catches. The T-0398 fix closed "the test failed" but not "the test
  proves nothing."
- **Failure scenario**: write `def test_foo(): import frob.foo` (imports the
  changed module, asserts nothing) in `tests/test_foo.py`, add a `frob:tests`
  edge or put the file in scope (N-04), `frob ticket evidence T-X
  tests/test_foo.py::test_foo` -> passes vacuously, records, closes. The ticket
  is "tested" and "covering" and "passed" by every gate while proving nothing.
- **Fix direction**: this is a genuinely hard problem; the smallest bounded step
  is to run the evidence test under coverage and require it to execute at least
  one line of a touched/scope symbol (turn the static `covers_scope` graph claim
  into a dynamic "the evidence run actually hit the changed code" check). A
  fuller answer is per-evidence mutation testing, which is a large feature --
  flag it rather than hand-wave.

### N-04 [MEDIUM] `covers_scope` route-2 is self-satisfying: declaring the test file/dir in scope makes binding trivially true

- **Where**: `evidence_covers_scope` (gates/__init__.py:308-314), the second
  disjunct `scope_matches(evidence.split("::", 1)[0], ticket.scope)`. This
  returns True whenever the evidence file path is textually inside the declared
  scope glob, with NO binding to any source symbol.
- **What's wrong**: scope is agent-controlled. Declaring `scope: tests/` (or the
  repo's blessed `scope: [src/foo.py, tests/test_foo.py]` convention with a
  broad test dir) makes ANY passing test under that path satisfy D-02. The
  binding degenerates to "an evidence file is inside a glob the author chose,"
  which the author can always arrange.
- **Failure scenario**: `frob ticket new --kind feat --scope tests/` ->
  `frob ticket evidence T-X tests/test_logging.py::test_levels` (unrelated to
  the actual code change) -> `scope_matches("tests/test_logging.py", ("tests/",))`
  is True -> covers_scope True -> closes, despite the evidence testing nothing
  the ticket changed.
- **Fix direction**: route-2 should require the evidence file's scope match to
  be a SOURCE file paired with a covering test, or require that when the scope
  contains test files it ALSO contains the source under test and the evidence
  dynamically hits it (see N-03). At minimum, do not accept a test file being
  in-scope as coverage of itself; coverage must reference a non-test scope entry.

### N-05 [MEDIUM] "Substantive" Done report is a 3-character gate -- boilerplate defeats D-03

- **Where**: `has_substantive_done_report` (_models.py:201) with
  `_MIN_DONE_REPORT_LINES = 1`, `_MIN_DONE_REPORT_CHARS = 3` (_models.py:175).
- **What's wrong**: the docstring claims it rejects a bare heading; it does, but
  only that. One non-blank line of three non-whitespace characters passes. The
  D-03 "substance" upgrade over the old heading-only check is cosmetic.
- **Failure scenario**: body `## Done report\nok.` -> `has_substantive_done_report`
  True -> close precondition met. Any lorem-ipsum line, `TODO`, or `done` passes.
- **Fix direction**: raise thresholds to something a real report clears but a
  stub does not (e.g. >= 3 non-blank lines and >= ~80 chars), and/or require
  named subsections the workflow already asks for ("what changed", "tests").
  Purely-lexical checks are always gameable by a deliberate actor; the goal is a
  lazy-dev deterrent, so at least make the floor non-trivial.

### N-06 [MEDIUM] Ripple horizon still misses 5+-hop dependency chains

- **Where**: `_RIPPLE_MAX_HOPS = 4` and `_ripple_symbols` (_select.py:69,72).
- **What's wrong**: D-07 widened the single hop to 4, but a covering test 5 or
  more `USES_CONTRACT` hops above a changed leaf is still never selected. The
  bound is defensible for graph-blowup reasons, but it is a hard cliff, not a
  cost-based cutoff, and it fails silently (no warning that the frontier was
  truncated with unreached dependents remaining).
- **Failure scenario**: a leaf helper changed; the only test covering the
  behavior is an integration test 5 hops up the call chain (A->B->C->D->E->leaf,
  test covers A). `frob test` selects nothing that exercises the change and
  reports a neutral pass; a real behavior change ships green.
- **Fix direction**: keep the bound but emit a WARNING when the BFS frontier is
  non-empty at cutoff (so under-selection is at least visible), and consider a
  larger bound gated by graph size. Document the residual limit next to
  `_RIPPLE_MAX_HOPS`.

### N-07 [MEDIUM] Unknown-language fallback over-selects the entire multi-language suite for any config/doc change

- **Where**: `_apply_unknown_language_fallback` (_select.py:283, :307-308): for
  a `.toml`/`.json`/`.yaml`/`.md` change under the default `package` fallback it
  adds `ALL_SENTINEL` for EVERY known language.
- **What's wrong**: editing a README, a changelog, or any data file now triggers
  a full run of the entire test suite across all languages. Two real costs:
  (1) a massive perf regression that pushes people toward skipping `frob test`;
  (2) FALSE POSITIVE -- a pre-existing unrelated red test in any language now
  blocks an honest one-line doc edit, teaching operators to ignore/bypass the
  gate. The D-04 fix traded a silent-under-test hole for a noisy over-test one.
- **Failure scenario**: fix a typo in `CHANGELOG.md` -> `frob test` selects
  `ALL_SENTINEL` for python + rust -> full suite runs; if any unrelated rust
  test is currently red, the doc-only change reports FAIL.
- **Fix direction**: scope the unknown-language fallback to the specific data
  file's likely consumers (tests whose files reference it, or a configured
  mapping in `frob.toml`), or make suite-wide unknown-language fallback opt-in
  rather than the default-`package` behavior. A doc-only change should not
  select the whole suite.

### N-08 [MEDIUM] Land re-verify -> squash-apply TOCTOU under concurrent lands

- **Where**: `land` (_land.py:489). Order is: merge main into worktree ->
  `_reverify_evidence_post_merge` (runs tests in the WORKTREE, :570) ->
  `_land_squash_apply` -> `_squash_and_splice_ledger` (git merge --squash onto
  root/main, :996). No lock guards main between the re-verify and the apply.
- **What's wrong**: the pass observation is made against `worktree = main@T +
  branch`. The squash then applies onto `main@T+delta`. A second land (or any
  push to main) between the two moves main; the applied tree is not the tree
  that was verified. Textual conflicts outside tickets.md abort, but a
  semantic-only interaction (main added a caller of the changed symbol, no
  textual conflict) lands unverified.
- **Failure scenario**: two agents land against the same main concurrently.
  Agent A verifies green in its worktree; agent B's land commits to main first;
  A's squash-apply succeeds (no textual conflict) but A's evidence was never run
  against B's new main state. A regression that only manifests with B's change
  present lands green.
- **Fix direction**: take an exclusive lock (flock on `.frob/land.lock` or a
  ledger-level lock) around the re-verify + squash-apply window, or re-merge and
  re-verify after acquiring the apply lock so the verified tree equals the
  applied tree. Bounded fix: serialize lands with a lockfile.

### N-09 [MEDIUM] Direct-pytest evidence fallback strips `addopts`, weakening the pass criterion

- **Where**: `_run_pytest_directly` (ticket_runner.py:950,958): `("uv", "run",
  "pytest", *node_ids, "-q", "-o", "addopts=")`.
- **What's wrong**: `-o addopts=` discards the project's configured pytest
  options. If a repo enforces pass-relevant options via `addopts`
  (`--strict-markers`, `--cov-fail-under`, `-p no:randomly`, custom plugins that
  turn warnings into errors), the evidence-time verification runs a LOOSER
  configuration than the real suite. An id can be recorded "passing" here yet
  fail under the repo's actual `pytest` settings.
- **Failure scenario**: repo sets `addopts = --strict-markers` in pyproject;
  a test uses an unregistered marker. Real `pytest` errors; frob's evidence
  fallback with `addopts=` passes it and records the id as passing.
- **Fix direction**: only clear the specific options that would break node-id
  targeting (if any) rather than blanket-clearing `addopts`; or run the fallback
  through the same config the real suite uses. Document precisely why any option
  is stripped.

### N-10 [MEDIUM] Inconsistent fail direction rewards omitting scope

- **Where**: `_covers_scope_for_ticket` (ticket_runner.py:707-724): graph
  unavailable -> return `False` (blocks, fail-closed); empty scope -> return
  `None` (skips, fail-open).
- **What's wrong**: a ticket that HONESTLY declares scope but hits a
  graph-load failure (fresh worktree without built native extensions, a known
  environment artifact per repo memory) is BLOCKED, while a ticket that declares
  NO scope sails through with the D-02 check skipped. The gate punishes the
  careful author and rewards the lazy one -- the exact inversion of intent, and
  a strong incentive to stop declaring scope (feeding N-01).
- **Failure scenario**: honest agent in a fresh worktree, graph won't build ->
  cannot close a genuinely-tested ticket; lazy agent omits scope -> closes an
  untested one. Both outcomes are wrong and point the same direction.
- **Fix direction**: make empty-scope code tickets fail-closed too (N-01), and
  give the graph-unavailable case a clear operator remedy (build the graph /
  `frob check`) rather than a silent block, so the two paths are consistent.

### N-11 [LOW] `passed` is never persisted, so no gate detects a DONE ticket whose evidence later went red

- **Where**: evidence stored as bare `tuple[str, ...]` (`Ticket.evidence`,
  _models.py:280); COV003 / `_evidence_valid_for_ticket` (gates/__init__.py:251)
  checks only collection membership, never pass state.
- **What's wrong**: once closed, a ticket's "passed at close" fact is not
  recorded and never re-checked by `frob check`. Combined with N-02, main
  accumulates DONE tickets over failing evidence tests that no gate surfaces.
- **Failure scenario**: N-02 closes a ticket over a now-red test; weeks later
  `frob check` still reports it clean because the id still collects.
- **Fix direction**: persist a per-evidence pass timestamp/commit-sha, and have
  `frob check` (or a periodic `frob test`) flag DONE tickets whose evidence no
  longer passes. Smallest step: record the commit sha at which each evidence id
  was last observed passing.

### N-12 [LOW] Docs-kind cmd-evidence `true` still accepted; digest never re-verified (restated D-10)

- **Where**: `_evidence_valid_for_ticket` (gates/__init__.py:251-273); COV003
  explicitly does not re-run cmd evidence.
- **What's wrong**: unchanged from round 1 -- for a docs-kind ticket,
  `--evidence-cmd true` (exit 0) is accepted as proof and the sha256 is never
  re-checked. Bounded to docs kind, so LOW; noted so the fixer knows it was
  deliberately not addressed by T-0398, not missed.
- **Fix direction**: none required beyond keeping `CMD_EVIDENCE_ALLOWED_KINDS`
  narrow; if docs tickets ever need stronger proof, require the command to
  produce a checkable artifact rather than just exit 0.

### N-13 [LOW] Evidence-time verification runs the batch once -- no flake guard

- **Where**: `_verify_ids_passing` (ticket_runner.py:868) runs each bucket once
  via a single `run_selected`.
- **What's wrong**: a flaky test that happens to pass on the single evidence
  run is recorded as passing; there is no re-run or quarantine. This is a weaker
  concern than N-03 but shares the "one green observation is treated as proof"
  shape.
- **Failure scenario**: an order/timing-dependent test passes on the evidence
  run and is recorded, then fails in CI. Nothing in the accounting layer flags
  the instability.
- **Fix direction**: out of scope for a bounded fix; note as accepted risk or
  add an optional `--repeat N` for evidence verification of known-flaky suites.

---

## Convergence verdict

**NOT converged.** The T-0398 fix genuinely closed the "the named test does not
exist / was never run / failed at record time / land trusts the worktree"
family (D-01, D-04..D-09, D-11 are solid). But it left the north-star reachable
around three CLI-accessible bypasses that require no `--force` and no config
change:

1. **Omit `--scope`** -> D-02 binding is skipped entirely (N-01), so any
   passing unrelated test closes any ticket.
2. **Close is not re-verified** -> record green, break the code, `frob ticket
   close` still closes (N-02); "closed" does not mean "currently passing."
3. **Pass == exit 0** -> a vacuous test satisfies D-01/D-02 (N-03), and a
   self-declared test scope satisfies D-02 (N-04).

Plus D-03's "substance" check is a 3-character floor (N-05). The subsystem
enforces "at some past instant, a named test that exists ran green, and (if the
author declared a scope and wrote a test that touches it) that test is loosely
associated with the change." That is stronger than round 1 but still not the
north-star. The two highest-leverage fixes: (a) re-verify evidence at CLOSE the
way land already does (N-02), and (b) fail-closed on empty scope for code
tickets (N-01). After those, N-03/N-04 (dynamic coverage of the changed line)
are the remaining conceptual gap between "a test ran green" and "the change is
proven."

---

## Notes -- checked & correct (do not re-verify)

- Land's post-merge re-verify (`_reverify_evidence_post_merge`, _land.py:570)
  really does re-collect and re-run against the merged worktree and returns
  `NotCloseable` before the squash-apply; main is untouched on failure. The D-05
  fix is real (its only gap is the concurrency TOCTOU, N-08).
- `_verify_ids_passing` per-language bucketing and the no-`[[test.runner]]`
  direct-pytest fallback are sound in structure (their gaps are N-03 vacuity and
  N-09 addopts-stripping, not logic errors).
- `matches_collected` is now single-sourced (_models.py:151); D-11 desync risk
  is genuinely resolved.
- `add_evidence`'s wholesale batch rejection on any unresolvable OR non-passing
  id (tickets/__init__.py:926-942) is correct all-or-nothing semantics.
- Evidence union on splice (D-09) and the state machine / id-allocation halves
  were correct in round 1 and unchanged; not re-audited in depth.

## Notes -- skipped / skimmed (audit boundary)

- I did NOT execute a full live end-to-end repro of each N-finding against a
  throwaway ledger (modifying this repo's tracked `tickets.md` was avoided);
  findings are constructed from reading the wired CLI call graph
  (`_close`/`_apply_evidence`/`_land` -> library) end to end, plus a live
  `uv run frob --version`/`ticket --help` confirming 0.31.0 and the absence of
  any `--force` on close/land. Each repro is a construction from that reading.
- `tickets/_store.py` ledger parse/render and `tickets/clipboard.py` were not
  re-line-audited (unchanged by T-0398; a parse bug surfaces loudly, low
  north-star risk).
- Rust symref resolution and cargo collection were read for interface only; the
  `tests/<stem>/` submodule approximation remains a known selection imprecision
  upstream of this layer.
- Graph completeness (`build_graph`, TESTS / USES_CONTRACT edge emission) is a
  trusted input; N-03/N-04/N-06 assume the graph is complete-as-built. Missing
  edges compound under-selection and under-binding independently.
</content>
</invoke>

frob:waive REF002 reason="one-off round-2 testing audit doc, anchored from docs/index.md by design; not a living doc other files should also link"
