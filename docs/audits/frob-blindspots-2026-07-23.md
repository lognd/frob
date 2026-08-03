# frob self-blindspot audit -- structural inefficiency + security

Scope: frob auditing itself for defects its own gates bless. Calibration class:
the T-0773 rev-parse loop-invariant-spawn incident, the T-0769 prose-as-capability
miscount, and the T-0761 land false-green. Each finding names the nearest gate and
why it does not fire, because each should spawn BOTH a fix ticket and a lint/gate
ticket.

Repo state at audit: main @ d27fbcec, clean tree.

---

## HIGH

### H1. `doable` re-spawns `git rev-parse --git-common-dir` and re-reads every lease file once PER candidate ticket (the exact T-0773 class, un-fixed in the lease path)

- Evidence:
  - `src/frob/tickets/__init__.py:1786-1790` -- `doable` loops
    `leased_by(queue, t, root, breadth=breadth)` over every candidate.
  - `leased_by` (`__init__.py:1148`) calls `_all_leases(queue, root)` every call.
  - `_all_leases:861` -> `_cross_worktree_leases:836` -> `read_all_leases(root)`.
  - `read_all_leases` (`_leases.py:210`) -> `leases_dir` -> `git_common_dir`
    (`_leases.py:84`) which spawns `git -C <root> rev-parse --git-common-dir`
    EVERY call, then `glob("*.json")` + `json.loads` + `Path(record.worktree).exists()`
    (a stat) for every lease file, EVERY call.
- Net effect: with N doable-candidate tickets and M live lease files, one
  `frob ticket doable` performs N subprocess spawns of rev-parse plus N*M file
  reads plus N*M stat() calls, all producing byte-identical results within the
  single call. On this repo's real worktree fleet (5-10 agents, dozens of
  queued tickets) that is dozens of redundant git spawns and hundreds of
  redundant lease reads per invocation. `doable_blocked` (`__init__.py:1813`)
  has the identical shape.
- Why no gate catches it: the T-0453 perf fix memoized only `breadth`
  (`scope_breadth_context`, threaded through as a param); the lease read was
  never hoisted. The new loop-invariant-effect lint (T-0775/T-0776) is still a
  strict-xfail lock (commits 2ed2d2f6/94a2fccc), i.e. NOT enforcing, and even
  once live the effectful call sits 5 interprocedural hops below the loop
  (`leased_by`->`_all_leases`->`_cross_worktree_leases`->`read_all_leases`->
  `leases_dir`->`git_common_dir`->`run_argv`) -- deeper than the rev-parse
  incident the detector was scoped to. No PERF rule models "pure w.r.t. the loop
  variable, so hoist" across that depth.
- Fix direction: compute the lease set once at the top of `doable`/`doable_blocked`
  and thread it into `leased_by` the same way `breadth` already is
  (add a `leases: tuple[...] | None = None` param to `leased_by`/`_all_leases`,
  precompute in the caller). Independently, memoize `git_common_dir(root)` per
  root (the common dir cannot change during a process's run).
- Lint/gate direction: extend the T-0775 loop-invariant-effect detector to
  follow interprocedural call chains to a fixed depth and flag an effectful leaf
  (subprocess spawn OR filesystem read) whose argument set is invariant across
  the loop. This finding is the second real instance of the class -- good
  regression fodder for the detector's depth parameter.

### H2. LINT004 kill-switch waivers on `core`/`fleet`/`tickets_ledger`/`stratamod`/`vet` cite T-0200 as "the follow-on ticket to build" a kill switch that T-0200 already SHIPPED -- and those nodes never wired into it, so `FROB_DISABLE_EXEC` does not stop most of frob's exec surface

- Evidence:
  - `design/frob.strata:351` (`core`), `:296` (`fleet`), plus `tickets_ledger`/
    `stratamod`/`vet` all carry
    `waive "LINT004" reason "no real kill switch around subprocess spawning yet
    -- T-0200 is the follow-on ticket to build one" ticket "T-0200"`.
  - T-0200 IS DONE: it is in `tickets-archive.md` (block at line 17009) and it
    built `src/frob/process/_guard.py::guarded_subprocess_run` (the module
    docstring, `_guard.py:1-17`, describes the mechanism as delivered).
  - Only `checker`-owned code wired in: `guarded_subprocess_run` is imported
    solely by `check/_python.py`, `check/_ts.py`, `check/_native.py`
    (grep confirmed). `core` owns `serve/**`, `gitio.py`, and `tickets/**`'s
    lease git calls -- NONE route through the guard; they call
    `subprocess.run` via `gitio.run_argv` (`gitio.py:91`) directly.
- Concrete failure scenario: an operator hits a runaway/compromised state and
  sets `FROB_DISABLE_EXEC=1` trusting the documented promise that it "genuinely
  stops EVERY process this component spawns" (`_guard.py:14-16`). The
  `frob serve` daemon keeps spawning `git rev-parse main`, `git merge-base`, and
  `git merge-tree` every 20s in its background thread
  (`serve/_daemon.py:123,218,228`), and every `frob` git IO keeps spawning --
  because none of it is behind the guard. The kill switch is a partial no-op that
  reads as total.
- Why no gate catches it: (a) LINT004 is satisfied on those five nodes by a
  WAIVER, and no gate re-litigates a waiver whose justifying ticket has since
  closed -- a "pending T-0200" reason survives forever after T-0200 lands.
  (b) The exec capability the daemon adds (T-0733) lives in `serve/**`, folded
  into `core` as generic "utility mesh"; LINT004 fires per strata node on a
  declared `may "exec"`, and `core`'s is waived, so the daemon's continuously-
  spawning exec surface is invisible to the very rule meant to force a kill
  switch onto it.
- Fix direction: route `gitio.run_argv` (and therefore the daemon and lease
  spawns) through `guarded_subprocess_run`, OR give `serve`/`gitio`/`tickets`
  their own real flag and update the waivers. Either way, DELETE the stale
  "T-0200 is the follow-on to build one" waivers -- the mechanism exists; the
  honest state is "wired: yes/no", not "still unbuilt".
- Lint/gate direction: add a gate that fails when a `waive`/`frob:waive`
  reason references a ticket that is DONE/DROPPED in the ledger (stale-waiver
  detection). A waiver justified by "pending T-XXXX" must not outlive T-XXXX.

---

## MEDIUM

### M1. `poll_rebase_bot` feeds attacker/peer-controlled branch names from lease JSON straight into `git merge-base`/`git merge-tree` argv with no `--` guard and no ref-name validation

- Evidence: `serve/_daemon.py:218` runs
  `("git","-C",str(root),"merge-base","main",branch)` and `:227-229`
  `("git",...,"merge-tree",merge_base,branch,main_head)`, where `branch` comes
  verbatim from a lease record read by `read_all_leases` out of
  `.git/frob-leases/<id>.json` (`_leases.py:219-220`). `read_all_leases` does
  Pydantic-validate the SHAPE but never validates that `branch`/`worktree` are
  well-formed (a `str` field accepts any string, including one starting with
  `-`).
- Failure scenario: any local process that can write under the shared git
  common dir (every co-located worktree agent, any local user with repo write)
  drops a crafted `evil.json` with `branch: "--output=/home/logan/.bashrc"`
  (or any `-`-leading token git parses as an option). The background daemon,
  running unattended, executes `git merge-tree <base> --output=... <head>`.
  It is argv (not shell) so no shell injection, but git OPTION injection is
  live: there is no `--` separating options from the ref operands. Even absent a
  weaponizable merge-tree option, this is an unvalidated trust-boundary read
  driving a subprocess in a background thread.
- Why no gate catches it: SEC/injection gates in this repo look for `shell=True`
  and f-string-into-argv; a plain positional variable that happens to be a git
  ref is not flagged, and no gate models "value crosses a trust boundary
  (repo-writable JSON) then reaches subprocess argv without validation or a `--`
  terminator." The lease file is under `.git/`, which the model treats as
  trusted, but it is writable by every peer worktree the daemon is explicitly
  built to watch.
- Fix direction: insert `"--"` before the ref operands in both git calls, and
  validate `branch` against `git check-ref-format --branch` (or a
  `^[A-Za-z0-9._/-]+$` allowlist that rejects a leading `-`) in
  `read_all_leases` before a record is admitted; drop+log records that fail.
- Lint/gate direction: a taint rule -- values sourced from `read_text`/`json.loads`
  of a path under `.git/`/`.frob/` that reach a `subprocess`/`run_argv` argv
  position must pass through a validator or a `--` terminator. Same rule would
  cover `worktree` reaching `Path(...).exists()`/display.

### M2. `.git/frob-leases/` grows without bound; crashed worktrees leave lease files that are skipped-on-read but never deleted, and each live-path stale lease is re-`merge-tree`d every daemon cycle forever

- Evidence: `release_lease` (`_leases.py:181`) only removes a lease on a clean
  IN_PROGRESS exit. `read_all_leases:224-240` SKIPS (does not delete) a lease
  whose worktree path is gone, and the T-0476 comment there explicitly defers
  cleanup ("cleanup itself is that ticket's job, not this one's"). A lease whose
  worktree DIRECTORY still exists but whose agent died mid-ticket is not even
  skipped -- it stays "live" and `poll_rebase_bot` re-runs two git spawns against
  it every `DEFAULT_POLL_INTERVAL_S` (20s) indefinitely (`_daemon.py:258-261`).
- Failure scenario: over a long-lived multi-agent campaign, agents crash and
  worktrees are pruned; `.git/frob-leases/` accumulates JSON files monotonically.
  Every `doable` call (see H1) then reads+parses+stats the whole growing
  directory N times. A stale-but-live-path lease also burns 2 git subprocesses
  per daemon cycle in perpetuity.
- Why no gate catches it: no gate models unbounded on-disk state growth, and the
  cleanup is a KNOWN deferral (T-0476) that was never built -- there is no gate
  that flags "a `frob:todo`/deferred-cleanup obligation has been open past N
  releases." The skip-don't-delete choice is defensible per-call but has no
  bounding process behind it.
- Fix direction: implement the T-0476 reconcile (opportunistically `unlink` a
  lease when `read_all_leases` judges it stale, guarded so a live worktree's
  lease is never removed), plus a TTL on `recorded_at` for live-path-but-dead
  leases so the daemon stops re-simulating them.
- Lint/gate direction: a gate that flags a long-deferred obligation -- a
  `frob:todo`/ticket referenced in a shipped comment as "that ticket's job" that
  remains open past a release boundary -- so deferred cleanup cannot silently
  become permanent.

### M3. Triplicated `git rev-parse --git-common-dir` resolver -- three near-identical implementations the DUP gate does not unify

- Evidence: identical resolve+absolutize logic in
  `_leases.py:84-94` (`git_common_dir`, returns `Result`),
  `gates/_exclude_hazard.py:50-68` (`_git_common_dir`, returns `Path|None`), and
  the docstring/inline pattern in `_daemon.py`/`gates` that re-derive common-dir
  facts. Same `run_argv([... rev-parse --git-common-dir])`, same
  `if not is_absolute: (root / raw).resolve()` tail, diverging only in error
  channel and log level.
- Failure scenario: a fix to one (e.g. handling `$GIT_COMMON_DIR`, or a
  trailing-newline quirk, or adding the H1 memoization) lands in one copy and
  silently desyncs the others -- exactly the "two copies of a rule is a bug
  waiting to desync" hazard the repo's own CLAUDE.md forbids.
- Why no gate catches it: the DUP gate keys on structural/type-generalized code
  similarity; these differ in return type (`Result[Path,LeaseError]` vs
  `Path|None`) and error handling, enough to slip under the similarity
  threshold, while being semantically one function.
- Fix direction: promote a single `git_common_dir(root) -> Result[Path, GitError]`
  into `frob.gitio` (the declared "ONE git subprocess seam", `gitio.py:1`) and
  have `_leases` and `_exclude_hazard` call it.
- Lint/gate direction: teach DUP to normalize the error-return channel
  (`Result[T,E]` vs `T|None` vs raising) before the similarity compare, so two
  functions that differ ONLY in how they signal failure still register as
  duplicates.

---

## LOW

### L1. `_leases.py` recording path spawns a second git subprocess (`git branch --show-current`) per lease write, redundant with data already resolvable once

- Evidence: `record_lease:150` spawns `git branch --show-current` on every
  `record_lease` (which fires on every IN_PROGRESS transition and every
  `mutate_scope`), in addition to the `git_common_dir` spawn already done by
  `leases_dir` in the same function. Two git spawns per lease write.
- Why no gate catches it: single-shot (not in a loop), so no PERF/loop rule
  applies; it is simply an un-batched spawn.
- Fix direction: minor -- acceptable as-is, but both facts (common dir + branch)
  could be fetched via one `git rev-parse --git-common-dir --abbrev-ref HEAD`.
- Lint/gate direction: none warranted; noted for completeness.

### L2. `read_all_leases` does a `Path(record.worktree).exists()` liveness stat that is a TOCTOU by construction relative to the consuming decision

- Evidence: `_leases.py:224` decides a lease is live/stale by whether the
  recorded worktree path exists AT READ TIME; the `doable`/daemon decision that
  consumes it runs later. A worktree removed between the stat and the dispatch
  (or created between) yields a stale verdict. Low impact -- the lease model is
  explicitly best-effort advisory (`_leases.py:126-133`), not a correctness
  lock -- but the "liveness judged structurally by path existing" claim
  (`_leases.py:229-232`) is weaker than it reads.
- Why no gate catches it: the module is INV006-waived as "design-rationale
  prose describing already-implemented behavior" (`_leases.py:24-29`), which
  removes it from cross-module-contract invariant tracking -- so the
  path-existence liveness claim is never verified against a concurrent-removal
  scenario.
- Fix direction: none required (advisory by design); if strengthened, pair the
  stat with the actual dispatch under a short-lived lock. Documented so a future
  reader does not mistake the path-exists check for a race-free liveness gate.
- Lint/gate direction: none; the INV006 waiver is a deliberate calibration
  decision.

---

## Notes -- checked and found correct (do not re-verify)

- `gitio.run_argv` correctly uses list argv, never `shell=True`, with a
  timeout and captured output (`gitio.py:91-98`). The single-seam claim holds
  for git IO itself (one `subprocess.run` for git).
- `working_diff` handles untracked directories/gitlinks (`gitio.py:245-251`) and
  binary/unreadable untracked files (`_count_lines:257-263`) without crashing.
- `_parse_unified_diff` correctly drops pure-deletion hunks (count==0,
  `gitio.py:188-190`) so a deletion does not select phantom new lines.
- `_daemon` cache writes are lock-guarded (`_set_status:114`), and `_STATUS`/
  `_warm._STATES` are keyed by resolved root -- bounded by repo count, not a
  leak.
- `poll_post_land` correctly short-circuits on unchanged HEAD (`_daemon.py:149`)
  -- that path IS memoized, unlike H1's.
- `exclude_hazard_gate` reads the SHARED common-dir exclude (correct per T-0465)
  and its prefix/shadow matching (`_exclude_hazard.py:117-127`) is sound.
- `_env_flag_set` truthiness handling in `_guard.py` is fine; the guard itself
  is correct -- the defect (H2) is that most exec sites never call it.

## Notes -- skipped or only skimmed (audit boundary)

- `gates/__init__.py` (8568 lines) and `vet/_capability.py` (3331 lines): only
  spot-read around the exec/capability-observer surface; a full gate-by-gate
  vacuous-satisfaction sweep (empty-diff/empty-scope green) was NOT done and is
  the largest remaining unaudited surface.
- `tickets/_land.py` (1992 lines): not re-audited -- the recent T-0761/T-0763
  false-green fixes are assumed sound; I did not re-derive the closeability
  preflight ordering.
- strata kernel/prover (`strata/**`, `strata-core` Rust): treated as trusted;
  did not verify LINT004's own firing logic beyond confirming it is
  waiver-gated per node.
- tree-sitter parsing of untrusted repo files (the `lang/**` collectors): not
  examined for parser-level DoS/traversal; flagged here as an unaudited trust
  boundary worth its own pass.
