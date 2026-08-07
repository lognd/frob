## Done report

**Correction to the survey finding this ticket is based on:** by the time
this ticket was picked up, `DUP001`/`DUP002` were ALREADY wired into
`frob.gates.__init__.dup_gate`, already registered as the opt-in `"clones"`
gate in `_ALL_GATES`/`run_gates`, and already calling the real smart
`find_clones` (R1-R5) pipeline, not the legacy scanner -- landed by
`a3eef8d8` (2026-07-17, T-0037/T-0001), one day before the survey doc
(`840c128b`, 2026-07-18) that describes it as "never invoked." Confirmed by
reading `src/frob/gates/__init__.py::dup_gate`/`_ALL_GATES`/`run_gates`
directly, not from docs. `docs/modules/dup-sota-survey.md` section 0's
"DUP001/DUP002 are pure rule functions but NOT wired" claim is therefore
stale and should be corrected in a follow-up doc pass (not filed as T-draft-56694d02 (never refiled)
below) -- not fixed here since `dup-sota-survey.md` is not in this
ticket's scope.

What was actually still broken, found by exercising the gate end-to-end
rather than trusting the survey:

1. **The clones gate was correctly wired but pathologically slow at this
   repo's scale.** `frob.dup._cache` (`get_fingerprint`/`put_fingerprint`/
   `get_verdict`/`put_verdict`) opened a brand-new `sqlite3.connect` +
   ran `executescript(_SCHEMA)` on EVERY SINGLE call. With ~5100 symbols
   in this repo's graph and 3 fingerprint rungs (r3/r4fp/r5) plus a
   verdict lookup per R4/R5 candidate pair, that is thousands of
   open+parse-schema+close cycles per `frob check` run. Measured before
   the fix: `[dup].enforce=true`, `uv run frob check --only clones`,
   cold cache: clones stage alone **76.23s** (`real 2m37.772s`,
   `user 2m34.769s` total, most of it this thrash); warm cache still
   several seconds because reconnection dominates even on a cache hit.
   Fixed in `src/frob/dup/_cache.py`: connections are now cached in a
   process-lifetime dict keyed by resolved `.frob/dup.db` path
   (`_conn_cache`/`_conn_lock`, `_connect`), reused across every
   get/put in one `find_clones` run instead of reopened per call; added
   `close_all()` for test teardown. Measured after the fix, same repo,
   same enabled state: cold-cache clones stage **43.25s** (`user 21.025s`,
   down from `2m34.769s` -- the CPU-bound thrash is gone; wall time was
   still contended by ~6 other worktree agents' concurrent `frob check`
   runs on the same machine at the time of this measurement), warm-cache
   (second run, same process/db) clones stage **2.36-3.59s**. This IS the
   "candidate-pair caching the pipeline already has" the ticket pointed
   at -- the caching logic itself was correct, but its own connection
   handling defeated the point at this repo's scale.
2. **A real self-pairing bug in the R4 rung, found via the above fix.**
   `_r4_groups` in `src/frob/dup/_pipeline.py` iterated
   `frob_core.candidate_pairs`' `(i, j)` output directly with no `i == j`
   guard (unlike `_bucket_pairs`, which structurally cannot self-pair via
   `range(i + 1, len(members))`). After the connection fix above, running
   the enabled gate over this repo's own diff surfaced `DUP002:
   src/frob/dup/_cache.py::get_verdict duplicates
   src/frob/dup/_cache.py::get_verdict` -- the SAME symref reported as its
   own clone, because `frob_core.candidate_pairs` can hand back `(i, i)`
   when a symbol's own R4 fingerprint set collides with itself past
   `_R4_MIN_SHARED`. Fixed with an explicit `i == j`/`a == b` skip in
   `_r4_groups`. Re-ran after the fix: 0 violations, the self-pair report
   is gone. `frob-core/src/lib.rs::candidate_pairs` itself (the Rust
   kernel that emits `(i, i)`) is out of this ticket's declared scope
   (scope has no `frob-core/**` glob) -- filed as T-draft-f9131f3e below rather than
   touched here.
3. **Fixture tests added** proving the opt-in gate genuinely fires and
   waives, not just that the rule functions are individually correct
   (which `tests/test_dup_smart.py::TestGateRules` already covered):
   `tests/test_gates.py::TestOptInGates::test_dup_gate_fires_on_planted_clone_when_enabled`
   writes a real `frob.toml` with `[dup].enforce = true` plus a planted
   `compute_total`/`compute_sum` alpha-renamed clone (padded past
   `DupConfig`'s default `min_tokens=40` floor, since `dup_gate`'s
   `frob.toml` reader only exposes `enforce`/`threshold`, not
   `min_tokens`), calls `dup_gate` directly, and asserts `DUP001` fires.
   `tests/test_gates.py::TestOptInGates::test_dup_gate_planted_clone_waived_passes`
   does the same with a `frob:waive DUP001 reason="..."` directive on the
   touched symbol and asserts, via the real `frob.gates._apply_waivers`
   path (same pattern as the existing `test_waiver_suppresses_and_reports`
   test), that the violation is present in `dup_gate`'s raw output but
   absent from `kept` and present in `waived` with a non-None `.waived`.
   `tests/test_gates.py::TestOptInGates::test_dup_gate_off_by_default`
   (pre-existing) already covers the non-opted-in-repo case at the gate
   level.
4. **Legacy Type-1/2 scanner path verified unaffected.** `_legacy.py`/
   `find_duplicates` (the separate scanner `frob check`'s Python stage
   runs via `src/frob/check/_python.py` and `frob.app.dup_runner`,
   independent of `[dup].enforce`) was not touched by this ticket; full
   suite run (`tests/unit/test_dup.py` and the rest, see Evidence) still
   passes, and this repo's own `frob check` (no `[dup]` section in its
   `frob.toml`, i.e. not opted in) still runs the legacy path only, as
   before.
5. **Regression tests for the cache fix itself**:
   `tests/unit/test_dup_cache.py::TestConnectionReuse` (new class) proves
   repeated `_connect` calls against the same root return the identical
   cached connection object, and that `close_all()` drops it (a
   subsequent `_connect` returns a new object) while the on-disk data
   survives.

Cuts / honestly not done: `docs/modules/dup-sota-survey.md`'s stale
section-0 claim is not corrected here (out of this ticket's scope glob);
`frob-core`'s `candidate_pairs` kernel itself still CAN emit `(i, i)` --
only the Python-side consumer was hardened, so any OTHER future caller of
`candidate_pairs` inherits the same footgun unless it also guards (flagged
in T-draft-f9131f3e, not fixed at the kernel).

New tickets filed:
- T-draft-56694d02 (never refiled) (doc drift): `docs/modules/dup-sota-survey.md` section 0's
  "DUP001/DUP002 ... NOT wired into frob.gates.__init__" claim is stale as
  of `a3eef8d8` (2026-07-17); correct it to describe the actual state
  (wired, opt-in, connection-pooled as of T-0191) so a future reader does
  not re-investigate an already-closed gap.
- T-draft-f9131f3e (bug, frob-core): `frob_core::candidate_pairs` can return a
  self-pair `(i, i)` when a symbol's own fingerprint set exceeds the
  shared-token floor against itself; guard it at the kernel so every
  Python-side caller (not just `_r4_groups`, which T-0191 hardened) gets
  the fix for free.

Evidence (measured, this session, `uv run pytest -q` full suite green,
`s`=skip only for frob-core-native-extension-absent guards which are N/A
here since the extension IS built in this worktree):
- `uv run pytest -q tests/test_gates.py::TestOptInGates -v` -- 7 passed
  (includes the 2 new tests above plus the pre-existing 5).
- `uv run pytest -q tests/unit/test_dup_cache.py` -- 8 passed (includes
  the new `TestConnectionReuse` class, 2 tests).
- `uv run pytest -q tests/test_dup_smart.py tests/test_dup_rungs.py
  tests/unit/test_dup_core.py tests/unit/test_dup_cache.py
  tests/unit/test_dup.py tests/unit/test_dup_smt.py tests/test_gates.py
  tests/system/test_cli_dup.py` -- all passed (2 skipped, guarded by
  `core_available()`, not applicable in this build).
- `uv run pytest -q` (full suite, post-merge-to-`423c299`) -- all passed
  (2 skipped, same guard).
- `frob:tests` directives added:
  `src/frob/dup/_cache.py::_connect` and `::close_all` (unit, in
  `tests/unit/test_dup_cache.py::TestConnectionReuse`);
  `src/frob/gates/__init__.py::dup_gate` (integration, in
  `tests/test_gates.py::TestOptInGates`'s two new tests).
- `uv run ruff check`/`uv run ruff format --check` on every touched file:
  clean, both PATH and project-pinned ruff per playbook section 12.

Gates: `frob ticket sweep T-0191` + `uv run frob check --stamp-baseline`
+ `uv run frob check --delta --ticket T-0191` clean, 0 new violations
(`0/4 new`), after merging `main` a second time mid-session (tip moved
`99ec64c` -> `423c299`, T-0192/T-0229/T-0250 landing concurrently; no
scope overlap with this ticket's files, confirmed via `git diff main
--diff-filter=D --stat` empty of anything outside `frob-core/Cargo.lock`/
`strata-core/Cargo.lock` build-artifact churn from `make core`, which was
reverted with `git checkout --` both times before finishing per the
land rule). Not closing this ticket -- leaving for review per the
review-gated flow.

**Aside, not this ticket's to fix:** filing the two tickets above hit a
real `frob ticket new` provisional-id collision live -- `mint_draft_id`
(`src/frob/tickets/_provisional.py`) returned `T-draft-beb2b5da` for the
`dup-sota-survey.md` doc-drift ticket, which was already in use by an
unrelated, pre-existing `T-draft-beb2b5da` ("frob deploy generate
windows...", parent `T-0254`) filed by a different worktree/agent earlier
in this session. `secrets.token_hex(4)` is only 32 bits, and with roughly
a dozen worktree agents minting draft ids concurrently on this machine
today (per the concurrent `ps aux` processes observed while measuring gate
wall time), a collision is well within reach of the birthday bound, and
`mint_draft_id` does not check the existing ledger before returning an id.
Recovered by hand here (renamed my ticket to `T-draft-56694d02 (never refiled)`, restored
the pre-existing ticket's original id, verified `grep '^id: ' tickets.md |
sort | uniq -d` empty afterward) since `tickets.md` is in this ticket's
scope and leaving a duplicate-id ledger would break tooling for every
other agent, but the root cause (`mint_draft_id` not checking uniqueness
against the current ledger) is in `src/frob/tickets/_provisional.py`,
outside T-0191's scope glob -- not filed as a new ticket here since a
provisional-id ticket can't yet be minted for a bug about mint_draft_id
without risking the same collision meta-problem; flagging in prose for the
coordinator to file directly once ids stabilize post-merge.
