# Agent playbook: per-dispatch checklist

Every worktree agent re-learns the same session lessons from scratch, and
coordinator dispatch prompts have grown into essays carrying them (T-0175).
This page is the canonical home for that process knowledge -- the hot
path only: every rule an agent must obey IN THE MOMENT, kept short enough
to read at the start of every ticket and again before reporting done
without itself becoming the token cost it exists to prevent.

**The full narrative -- every incident, every measurement, every rarely-
needed recipe -- lives in `docs/guides/agent-playbook-appendix.md`
(T-2909). Nothing was deleted, only moved: this file states the rule and
points to the appendix section for the WHY and the full incident when you
want it.** Each incident referenced below (here or in the appendix)
actually happened in this repo's history. This is not theoretical caution.

## 0. Standard dispatch contract (the whole ritual, in order)

This section IS the dispatch prompt. A coordinator prompt that names your
ticket series plus any ticket-specific notes and says "playbook governs"
means exactly this list; everything below it in this file is the detailed
per-topic rule, and the appendix holds the full WHY and recovery recipes.

1. ONE named worktree per series (`.claude/worktrees/<slug>`), reused for
   every ticket in the series. `EnterWorktree`, fallback
   `git worktree add <path> main`. Verify base == current main tip; merge
   main if stale (sec 1). `uv run frob ticket work T-XXXX` (T-1175)
   collapses this step plus step 2 plus `start` into one command for a
   SINGLE ticket's own worktree (`--worktree PATH` to override the
   default `.claude/worktrees/<id-lowercased>`); for a multi-ticket
   SERIES worktree, still cut it by hand once with `EnterWorktree`/`git
   worktree add` and use plain `uv run frob ticket start T-XXXX` for the
   second and later tickets in that same worktree.
2. `uv run frob natives build` in the worktree BEFORE anything else --
   missing natives = mass phantom findings, not real drift (NATIVE001
   exists but do not wait to hit it). ALWAYS `uv run frob`, never bare
   `frob`. (`frob ticket work`, step 1, already does this for you.)
3. Long frob verbs (`land`, `done-report`, `check`, `test`) MUST be run
   foreground with the Bash TOOL-level parameter `timeout: 600000` PLUS a
   shell-level `timeout 540 ...` wrapper. A project PreToolUse hook DENIES
   the call otherwise. The shell wrapper alone does NOT prevent the ~120s
   harness auto-background (sec 3b). Never background these, never arm a
   Monitor on them, never end your turn waiting for anything.
4. Work strictly inside the ticket's scope; narrow a broad scope to the
   real files via `uv run frob ticket scope` before working (sec 4). If
   `ticket start` refuses on a lease collision, skip to the next series
   item and retry later; report anything still blocked -- never wait idle.
5. `uv run frob ticket land` (T-1175) now absorbs `frob fmt` on the
   worktree and the T-1138 Tier-A deterministic auto-fix handlers
   automatically, BEFORE its own merge -- you do not need to run either by
   hand before landing any more; still worth running `uv run frob fmt
   --check` mid-ticket if you want to see drift EARLY. `land` still
   refuses synchronously if `design/frob.strata` fails to PARSE at all
   (appendix sec 0, step 5's full note).
6. Evidence: pytest node ids in `file::Class::method` form, bound to
   acceptance indices via `--accepts N` (sec 5). Every `frob:tests` edge
   uses the dotted `Class.method` form, never pytest `::` form. New public
   API needs the REL001 stamp via `uv run frob release` tooling -- never
   hand-edit versions. Docs move in the same change as the code. For a
   `bug`/`security`-kind ticket, `--designate-repro NODE-ID` VALIDATES at
   designate time -- it re-runs NODE-ID against the ticket's parent commit
   and REFUSES (no write) unless the outcome is `FAILED_AT_PARENT`. Check
   this BEFORE binding evidence you intend to designate:
   `frob ticket evidence T-#### --check-repro [NODE-ID] [--base-ref REF]`
   (appendix sec 0, step 6, for the escape hatch and the incidents this
   closes).
7. NEVER `git stash` (sec 1b). NEVER remove a worktree after a failed
   land -- the branch is the recovery path. A land that dies silently may
   have SUCCEEDED: check `git log main` before retrying; after a second
   silent death, keep your commits, report, continue the series.
8. Every residue/follow-up you file is a draft that renumbers at land.
   VERIFY the real id exists on main before citing it in your final
   report. A disclosed cut with no ticket is a TICK011 finding -- file it
   or state why not. NEVER hand-refile a draft (read its body out, `frob
   ticket new` a fresh one, delete the draft's block) -- use `frob ticket
   promote <draft-id>` instead if a draft needs a real id before its own
   land (appendix sec 0, step 8, for the lossy-recipe incident this
   replaces).
9. `uv run frob ticket land` prints its own `LAND-PROOF:` line after every
   real (non-dry-run) land -- `commit=<sha> is_ancestor_of_main=True/False
   state_on_main=<state> verified=True/False`. Read that line rather than
   re-deriving it; `verified=True` is what "landed" means here. `--finish`
   runs the same check internally and, only if it passes, removes
   `--worktree` for you -- use it once every ticket in the series has
   landed and verified.
10. Before landing, check the land slot rather than hand-rolling a `ps`/
    `pgrep` probe (appendix sec 13 explains why every hand-rolled form is
    unreliable):
    ```
    export FROB_LAND_DEADLINE_S=540
    uv run python scripts/wait_for_land_slot.py --max-in-flight 1 --timeout 480
    # land only if that exited 0 (exit 1 = retry later, exit 2 = UNMEASURED, also retry)
    timeout 540 uv run frob ticket land <ticket> --worktree <wt>
    ```
11. ASCII only. No emojis. No Co-Authored-By lines. End your turn only
    with the full series report: per ticket, the land hash, evidence
    bound, and residue with verified real ids.

## 1. Worktree warm-up (do this FIRST, every time)

0. BEFORE any `git merge main` (warm-up or mid-ticket): check that no
   coordinator land is in flight via `uv run python scripts/fleet_status.py`
   and read its `LANDS IN FLIGHT: N` line. **Never hand-roll a `ps
   aux`/`pgrep` check for this** (T-2742) -- the polling shell's own
   command text (and every sibling agent's) contains the very pattern it
   is searching for, so the count can never reliably reach zero while
   anyone is polling. `fleet_status.py` identifies a land structurally, not
   by cmdline text. Do NOT park on a Monitor waiting for a land slot to
   open -- nothing wakes you. If a land is running, wait for it to exit and
   for `git -C <root> log --oneline -1` to be stable across ~30s, then
   merge. (Appendix sec 1, item 0, for the reverted-merge incident this
   guards against.)
1. `git merge main` in the worktree, then verify the tip:
   `git log --oneline -1` must show a commit that is `main`'s current tip
   or an ancestor merge of it -- not the worktree's stale creation base.
   **This is a hard MUST, not a nice-to-have -- run these two commands
   before touching anything else:**
   ```
   git merge main
   git log --oneline -1   # confirm this IS (or descends from) main's tip
   ```
   This exists because the dispatch harness's worktree-creation tool can
   cut a new worktree from a stale `origin/main` rather than local
   `main`'s tip (appendix sec 1, item 1, for the full root-cause
   investigation and the two standing mitigations).
2. `uv run frob natives build` (aliased as `make core`, where `make` is
   available) to build the native extensions into the worktree's own
   `.venv`. A collection failure with `ModuleNotFoundError: strata_core`
   or `frob_core` in a fresh worktree is an environment artifact, not a
   regression -- run this before concluding otherwise. Warm builds (a
   second/third worktree) measure ~11s via a shared cargo target cache
   (appendix sec 1, item 2).
3. Use `uv run frob ...` for every invocation inside a worktree, never a
   globally-installed `frob` binary -- it may be a different version, or
   may not see gate-affecting source changes at all (sec 2).

## 1b. NEVER `git stash` in a worktree (it is repo-global, not worktree-local)

`git stash` writes to `refs/stash`, which is SHARED across every worktree
of the repo -- it is NOT worktree-local. In a parallel multi-agent
session, `git stash` in your worktree collides with other worktrees'
stashes and silently reverts your own uncommitted state.

Never `git stash` here. When you need to pull a fast-moving `main` into
your worktree mid-ticket, COMMIT your work-in-progress first, THEN
`git merge main`. If a merge conflicts in a ticket file, resolve it by
KEEPING BOTH sides' real facts -- never by stashing.

This is now backed by a mechanical guard (T-0574): `frob scaffold apply`
installs a `.git/hooks/reference-transaction` hook that refuses any
`git stash` while more than one worktree exists for the clone. It is a
per-clone hook, not an unbypassable sandbox -- commit your WIP instead of
relying on it as the only line of defense. See appendix sec 1b for why
this specific git hook (not `pre-stash`, not an alias) was the only one
that actually works, and sec 1b2 for the second-order hazard a conflicted
`stash pop` creates even after this guard exists.

## 1c. NEVER edit `.git/info/exclude` (it is repo-global, not worktree-local)

Same hazard class as 1b: `.git/info/exclude` lives under the COMMON `.git`
dir every worktree shares, not a per-worktree path. Adding an entry there
to hide your own scratch files gives a real, git-tracked directory a
standing blind spot for every worktree, permanently, until someone
notices. Never add an entry here to hide work-in-progress -- a genuinely
generated/vendored path belongs in the tracked `.gitignore` instead.
`frob check`'s `excludehazard` stage (EXCL001, unwaivable) statically
flags any existing entry that shadows tracked source. See appendix sec 1c
for the incident where this cost a whole feature directory silently going
untracked.

## 1d. Route multi-sentence ticket prose through a `--*-file` flag, never inline shell text

Long ticket prose passed inline through bash as a quoted `--body`/
`--reason`/`--why` argument is exposed to the shell's own command
substitution: a backtick or `$(...)` sequence anywhere in that prose gets
executed by bash BEFORE frob ever sees the string, silently corrupting the
ticket body/reason. Every ticket-mutating subcommand that accepts
free-text prose has a file-input twin:

- `frob ticket new --body-file PATH` / `--acceptance-file PATH`
- `frob ticket scope <id> --reason-file PATH`
- `frob ticket done-report <id> --why-file PATH`

Write the prose to a temp file first, then pass `--*-file <path>`.

**"Your scratch area" means `/tmp`, concretely -- never a path under the
repo root, not even a gitignored one.** A stray `--*-file` input left at
the repo root becomes committed passenger content on the next `frob
ticket land`, or (if gitignored to hide that) invisible to the
root-cleanliness detectors that would otherwise catch it. Use
`/tmp/t<ticket-id>_<purpose>.md` every time, and confirm afterward that
both `git status --porcelain` AND `git ls-files` show nothing new at the
repo root. See appendix sec 1d for the T-0627/T-0697/T-0735/T-0736/T-2524
incidents this rule closes.

## 1e. The fleet-aware xdist bound is now applied in-process, but only for frob-orchestrated pytest (T-3099)

Section 1 item 0's fleet detection also feeds a per-agent
`PYTEST_XDIST_AUTO_NUM_WORKERS` bound (T-2221): under a live multi-agent
fleet, `-n auto` alone oversubscribes the box (every agent's suite tries
to claim the full CPU count at once). `eval "$(uv run frob agent env
<worktree-path>)"` still prints that bound as `export` lines, but treat
it as covering ONE thing only now: **your own raw shell pytest
invocation** (you typing `uv run pytest ...` directly). Do not rely on it
for anything else -- T-3094 measured 0 of 40 live workers carrying the
bound despite it being computed correctly, because the dispatch harness
resets shell state between tool calls, so an `eval` in one command is
gone before the next command (the one that actually runs pytest) starts.

Every frob-orchestrated pytest spawn (`frob check`, `frob test`, `frob
mutate`, `frob perf profile --tests`, ticket evidence verification) now
applies the bound to its OWN process's `os.environ` in-process
(`apply_agent_env`, T-3094/T-3099) before it spawns pytest, so the child
inherits it with no `eval` hop at all -- you do not need to `eval`
anything before running those commands. If a fleet context exists but
the bound is somehow still missing when one of those commands spawns
pytest, `warn_if_xdist_bound_missing` logs an ERROR naming the gap in
that command's own output; treat that log line as a real defect report,
not noise.

Bottom line: still `eval` before a RAW `uv run pytest ...` you type
yourself; never `eval` for a `frob` subcommand -- it already handles this
for you, and doing so is redundant, not harmful, but signals a
misunderstanding of which layer applies the bound.

## 2. Gate-affecting source only takes effect via

- `uv run frob ...` (editable install picks up local source changes on
  every invocation), OR
- a full `uv tool install` reinstall (`make install-tool`) followed by
  `rm -rf .frob` to drop stale cached state.
If a gate change does not seem to be firing, confirm which `frob` is
actually running (`which frob` vs `uv run frob --version`) before assuming
the change is wrong.

## 3. Never pipe state-changing or verifying commands through tail/grep/head

Run `frob check`, `frob test`, `pytest`, `git merge`, `frob ticket start`,
and similar commands BARE and inspect the full output afterward. Piping
through `| tail`, `| grep`, `| head` masks the real exit code. If output
is long, redirect to a file and read the file -- do not filter the live
command.

## 3b. Foreground + explicit `timeout` wrapper is the ONLY sanctioned pattern (T-1004)

Do NOT run pytest / frob check / builds with `run_in_background` (or a
`Monitor`) and then end your turn "waiting for the notification" -- the
moment you end your turn with no live background children, no
notification will EVER arrive as a dispatched sub-agent. Run every
verification command in the FOREGROUND, wrapped in an explicit `timeout`
comfortably under your harness's auto-background cap (100-110s):

```
timeout 100 uv run frob check --only "$s"
timeout 100 uv run pytest tests/unit/test_foo.py -p no:cacheprovider -q
```

When `FROB_AGENT` is set (true for every dispatched worktree agent), a
bare `frob check` with no `--only`/`--budget` REFUSES immediately instead
of running and stalling. Use one of:

- **`frob check --budget SECONDS`** (preferred for "whatever fits,
  safely, in one shot"): self-selects `--only` stage groups to fit inside
  `SECONDS`, reports anything deferred as a loud `BUDGET001` warning, and
  resumes from there on the next identical call.
  ```
  timeout 110 uv run frob check --budget 100
  ```
- **The manual `--only` loop** (for an exact stage by name):
  ```
  for s in $(timeout 30 uv run frob check --only list); do
    timeout 100 uv run frob check --only "$s"
  done
  ```
- **`--stamp-baseline`** is a COORDINATOR-ONLY path bare; an agent passes
  `--only <group-or-gate>` chunks instead (repeatable across calls; the
  real baseline is written once every gate is covered).

See appendix sec 3b for the full chunking recipe, the coordination-churn
measurement behind this rule, and why `--stamp-baseline`'s naive one-shot
form is banned for a sub-agent.

## 3c. A verification that cannot fit the timeout is a COORDINATOR step

The full unscoped suite, a full unscoped `frob check`, and `make coverage`
structurally cannot fit inside the ~100s foreground budget. Do not
background them, do not poll a log for them, and never narrate progress
percentages -- report a result or a blocker, nothing in between. A
dispatched sub-agent runs ONLY verifications that fit comfortably in a
foreground `timeout`: the specific failing node ids, each touched test
FILE in full, and the test files covering any production module it
changed. Anything broader is a coordinator step, run after the land, never
delegated. See appendix sec 3c for the measured cost of an agent
improvising around this (T-1392: ~40 log-tail reads spent on narration
instead of the five failures it was dispatched to diagnose).

## 4. Scope conventions

- `tickets.md` (or `tickets/T-####/`) is always in scope, implicitly, for
  any ticket -- the Done report lives there.
- Touch only files/symbols matching the ticket's declared `scope` globs.
  Anything else you find that needs fixing gets filed as a new ticket
  (`frob ticket new`), not silently folded in.

## 4b. Land-owned files are untouchable in a worktree (T-0731)

`pyproject.toml`'s `version = "..."` line, `CHANGELOG.md`, and `uv.lock`
belong to `frob ticket land` EXCLUSIVELY -- never bump the version, never
hand-append a changelog entry, and never touch the lockfile yourself in a
worktree. REL001's version-bump/changelog half is suppressed automatically
whenever `FROB_AGENT` is set; `frob ticket land` computes the bump and
generates the changelog entry at land time; a scaffolded `pre-commit` hook
mechanically refuses a worktree commit that touches any of these three
files at all. If you find yourself editing one of these for a reason other
than the guard hook itself, stop -- file a ticket or say so in your Done
report; do not work around the guard. See appendix sec 4b for the
bump-and-chase dance this replaced.

## 4c. A file split must re-check the rules it just promoted (T-2846/T-2695/T-2851)

Moving symbols into a new file is not scope-neutral even when the diff is
"just a move": a new file starts with ZERO inbound doc/test edges, and a
split can force a previously-private helper to cross the new file
boundary with a wider visibility than it had before. Before landing ANY
file split, re-run `frob check --json --ticket <id>` (unbudgeted,
`gate-summary` present) and confirm zero NEW findings for REF001/REF002
(no inbound reference), DRIFT002 (a doc/test edge still naming the OLD
file), COV001/TEST001 (a newly-widened symbol needing a doc/test edge it
never needed as private), and F401/F822 (an import or `__all__` entry left
behind in the old file). None of these require new prose -- repoint the
existing edge. See appendix sec 4c for the three real incidents (T-2846,
T-2695, T-2851) that shipped this exact regression class in one night.

## 5. Evidence recording

- Evidence ids must use real class/function names and must resolve against
  a fresh `pytest --collect-only` pass -- never claim a node id you have
  not actually observed collected.
- `frob:tests` directives use the `path::Class.method` (or `path::function`)
  qualname form, matching what `pytest --collect-only -q` prints.
- Never claim a test count you did not personally observe in command
  output. "Should pass" is not evidence; a pasted pass count is.
- Docs-only tickets with no pytest surface of their own: record the
  existing CLI-dispatch integration test as evidence instead of inventing
  one (`tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches`).
  Add a small drift-lock test only if a gate actually demands one.
- Run the CLI evidence-collection step from a natives-built checkout --
  otherwise repo-wide collection hard-fails (T-0144).

## 6. Gate measurement discipline

Prefer `frob check --delta` against a stamped baseline over stash-isolation
dances. If a gate reading looks impossibly stale, re-measure once with
`FROB_NO_GATE_CACHE=1` before trusting or reporting it -- a cached-vs-fresh
disagreement is itself a finding worth a ticket.

```
timeout 100 uv run frob check --stamp-baseline --only gates-native      # once, before starting work
timeout 100 uv run frob check --stamp-baseline --only gates-security    # (chunked -- see sec 3b)
timeout 100 uv run frob check --stamp-baseline --only gates-fast
# ... implement ...
timeout 110 uv run frob check --budget 100 --delta   # or the --only loop
```

New public symbols need both a `frob:doc` edge and a `frob:tests` edge --
`COV001` and `TEST001` are ERROR-level gates. Add both at the point you
add or change the symbol, not as a follow-up.

`--stamp-baseline` (bare, no `--only`) is a COORDINATOR-ONLY path, same as
`make coverage` (sec 6b) -- an agent passes `--only <group-or-gate>`
chunks instead, repeatable across calls (see sec 3b). See appendix sec 6
for `.frob/coverage.partial.xml` vs `coverage.xml` vs
`frob-coverage.lock.json` (sec 6d, do NOT trust the lock file for a
coverage claim), the deflation-floor/denominator investigation (sec 6e),
and the land-time merge fix for the coverage lock (sec 6f).

## 6b. Do NOT run the full-suite coverage refresh as a dispatched sub-agent -- you cannot wait on it

`uv run frob ticket reconcile --apply && uv run frob doctor && uv run frob
coverage --full` (`make coverage`) exceeds the 120s foreground cap and its
completion notification is routed to the coordinator, not to you.
Instead, verify your change the FAST way:

- Run only YOUR OWN new/changed test files, foreground, fast.
- Run `uv run frob check --ticket T-XXXX` (scoped) and `uv run frob check
  --delta` for new-violation triage.
- Record evidence, write the Done report, and COMMIT -- without ever
  running `frob coverage --full`.
- The COORDINATOR runs `frob coverage --full` + `frob check
  --stamp-coverage` once, at land, against the merged result.

(If you hit `NativeExtensionUnavailable`, that's a missing native --
`uv run frob natives build` then `frob test --collect`.)

## 6c. A `--only`/`--ticket`-scoped "0 findings" is not a package-clean claim (T-1351)

`frob check` prints its own `gate:scope-note` line whenever `--only`
and/or `--ticket` could make a clean-looking run be misread as "the whole
package is clean" -- read it before reporting a burn-down package clean,
not after. `--ticket` does NOT filter most gate families' violation counts
to the ticket's scope -- only `gate:SCOPE`/`gate:PREWORK` and the
diff-driven checks folded into `gate:COV` (COV002/TODO001) and
`gate:FMT`/`gate:AFFECT` are actually scoped. To verify your own ticket's
package is actually clean, run the RELEVANT gate family unscoped and read
its `gate:<FAMILY>` line directly. See appendix sec 6c for the two real
incidents (T-1293, T-1337) this note exists to prevent, and the
TEST005-specific measurement protocol.

## 6g. Run `frob check --land-parity` before writing your Done report (T-1535)

```
timeout 400 uv run frob check --land-parity
```

Runs the EXACT evaluation the land pre-commit/post-land sweeps run against
your CURRENT worktree tree, cache-bypassed -- so you can converge BEFORE
the coordinator ever lands. Exits 0 with a clean message when the land
sweep would see zero unscoped errors, exits 1 and prints every
`(rule, file)` finding otherwise. This is not a substitute for the scoped
`--only test/archgate/coverage/sys --ticket T-XXXX` checks sec 0 already
requires -- it is the one extra check that catches what those necessarily
scoped checks cannot. See appendix sec 6g for the exact blind repair
rounds this closed.

## 7. Waive discipline

`frob:waive RULE-ID reason="..."` suppresses one specific violation and
must always carry a `reason=`. `WAIVE001` fires if the reason is missing;
`WAIVE002` fires if the rule id can never match anything -- both are gate
errors, not silent no-ops. Never add a blanket waiver to make a gate go
quiet; waive the specific violation with a specific, honest reason, or fix
the underlying issue.

## 8. Done-report requirements

- Report only measured numbers: command output you actually ran and read,
  not estimates or "should be" figures.
- Disclose cuts honestly. If something in the ticket's plan was not done,
  say so plainly in the Done report rather than let silence imply it was
  done.
- Do not claim a merge, diff, or test result is durable beyond what you
  actually verified against. See appendix sec 8 for the deletion-filter
  incident this cost in a real case.

## 9. The deletion-filter land rule (verify before every finish)

Before finishing (committing your final state), run:

```
git diff main --diff-filter=D --stat
```

This MUST be empty of anything outside your ticket's declared scope. A
worktree created from (or merged against) a stale `main` can silently
revert already-landed features when squash-applied or merged forward. If
the filter shows deletions you did not intend, merge main again before
proceeding -- do not commit through it. See appendix sec 9 for the T-0167
incident this rule was written from.

## 10. Ledger-conflict splice guidance (v2: per-ticket directories, no driver)

**This repo is on ledger v2** (T-1258/T-2356): `tickets/T-####/`
directories (`ticket.md`, `done-report.md`, `attachments/`) -- ordinary
git objects that git's native per-file 3-way merge already resolves
correctly for the common case. The `frob ticket merge-driver` this section
used to tell you to register is retired for THIS repo, deliberately -- do
NOT register it "just in case."

**main is itself a second writer of `tickets/T-####/` now** (T-2563's
ledger mirror). A worktree's `git merge main` can therefore conflict on
its own ticket's files:

- Different lines/keys of `ticket.md`: native 3-way merges cleanly,
  nothing to do.
- The same key, or `done-report.md` created fresh on both sides: native
  3-way DOES conflict with real markers -- resolve by reading both sides
  and keeping whichever facts are real. Do NOT `git checkout --ours`/
  `--theirs` blindly.

After resolving any real conflict by hand, audit the ticket(s) touched
(`frob ticket show <id>`) to confirm no ticket regressed to an earlier
state or lost a Done-report claim. See appendix sec 10 for the T-2570
`done-report.md`-silently-overwritten defect (now fixed at the source) and
the full merge-driver history, and appendix sec 10b for the (largely
obsolete under v2, but still historically relevant) monofile ledger
finalize recipe.

## 10c. `frob ticket promote` from a worktree: committed, but not visible on main until land (T-2197)

`frob ticket promote <draft-id>` commits its own full rename atomically
before returning. What is still true: a promoted id committed inside a
per-ticket worktree exists ONLY on that worktree's own branch until the
worktree's ticket actually lands -- `frob ticket work <promoted-id>` /
`doable` / a dispatch run against the PRIMARY checkout will see nothing
for it until the branch lands. If you promote a draft and hand its new id
off for dispatch, land first, or expect the dispatch to correctly refuse.
See appendix sec 10c for the fixed uncommitted-rename defect this
replaced.

## 11. Ticket workflow

1. `frob ticket start T-XXXX` -- runs the pre-work sweep (dup+xref) over
   scope; read the ticket's Description and Plan sections fully before
   touching anything.
2. Implement strictly inside the declared `scope` globs.
3. Record evidence (sec 5) and write the Done report (sec 8).
4. In a review-gated flow: DO NOT close the ticket yourself. Leave it for
   the reviewer. Only close directly when explicitly told the flow is not
   review-gated.
5. `frob ticket close T-XXXX` (when you are the closer) re-verifies
   evidence and the Done report section from scratch -- it is not a
   formality you can bypass by editing the ticket frontmatter directly.

## 11b. The diagnosis-nudge Stop hook (T-1734)

A Stop-event hook (`.claude/hooks/diagnosis-nudge.py`) may append a
`systemMessage` at the end of a turn if your own last message stated a
diagnosis-shaped claim ("this is a real bug", "root cause is ...") with no
matching `frob ticket new` in this repo's telemetry stream recently. It is
lexical and state-based, never an LLM judging your prose. It NEVER blocks;
it only nudges, rate-limited per session. If it fires and the diagnosis is
real, file the ticket it names; if it is a false positive, ignore it.

## 12. Style

- ASCII only, no exceptions.
- No emojis, anywhere.
- No `Co-Authored-By` line in commits, ever.
- Conventional commits: `type(scope): imperative summary`, no trailing
  period, body explains WHY not WHAT.
- `ruff` must be stable under BOTH the PATH `ruff` and the project-pinned
  version (`uv run ruff`) -- check both before reporting a ruff pass.

## 12b. Coordinator worktree cleanup (T-0836)

Use `frob worktree sweep [path] [--dry-run] [--min-age HOURS]` instead of
a raw bulk `git worktree remove` loop, always -- git's own dirty check
cannot tell a live agent mid-diagnosis from an abandoned worktree.
`--dry-run` previews every verdict without removing anything. Per-worktree
verify-then-remove (a single worktree you just finished landing yourself)
is still fine; a raw bulk loop across `.claude/worktrees/*` is forbidden.
See appendix sec 12b for the 68-worktree incident this rule was written
from.

## See also

- `docs/guides/agent-playbook-appendix.md` -- the full narrative and
  incident record this file summarizes: every WHY, every measurement,
  every recovery recipe, plus the historical/rarely-needed sections this
  split moved out of the hot path entirely (the conflicted-`stash pop`
  index hazard, the ledger v1 finalize recipe, the TEST005/coverage-lock
  archaeology, and the land-cost design finding).
- `docs/modules/gates.md` -- the full gate catalog, `--delta`/baseline
  mechanics in detail, and waiver semantics.
- `docs/modules/tickets.md` -- the ticket state machine and evidence model.
- `docs/guides/agentic-workflow.md` -- the human/AI split and the
  worktree-per-agent pattern this playbook assumes.
- `docs/guides/testing.md` -- the per-test pytest-timeout guard (T-0692),
  the deadlock class it catches, and how to add an override for a
  legitimately slow test.
