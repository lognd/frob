# Agent playbook: per-dispatch checklist

Every worktree agent re-learns the same session lessons from scratch, and
coordinator dispatch prompts have grown into essays carrying them (T-0175).
This page is the canonical home for that process knowledge. Dispatch
prompts should link here instead of re-explaining it; agents should read
this top-to-bottom at the start of every ticket and again before reporting
done.

Each incident referenced below actually happened in this repo's history
(tickets.md / tickets-archive.md Done reports). This is not theoretical
caution.

## 0. Standard dispatch contract (the whole ritual, in order)

This section IS the dispatch prompt. A coordinator prompt that names your
ticket series plus any ticket-specific notes and says "playbook governs"
means exactly this list; everything below it in this file is the detailed
WHY and the recovery recipes.

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
   worktree, `frob sys sync-interface` (writes the fix, not `--check`),
   and the T-1138 Tier-A deterministic auto-fix handlers automatically,
   BEFORE its own merge -- any file one of these three rewrites becomes
   an ordinary uncommitted change, swept into `land`'s existing
   pre-merge wip-commit like anything else. You do not need to run any
   of the three by hand before landing any more; still worth running
   `uv run frob fmt --check`/`uv run frob sys sync-interface --check`
   mid-ticket if you want to see drift EARLY rather than wait for land
   to fix it silently.
6. Evidence: pytest node ids in `file::Class::method` form, bound to
   acceptance indices via `--accepts N` (sec 5). Every `frob:tests` edge
   uses the dotted `Class.method` form, never pytest `::` form. New public
   API needs the REL001 stamp via `uv run frob release` tooling -- never
   hand-edit versions. Docs move in the same change as the code.
7. NEVER `git stash` (sec 1b). NEVER remove a worktree after a failed
   land -- the branch is the recovery path. A land that dies silently may
   have SUCCEEDED: check `git log main` before retrying; after a second
   silent death, keep your commits, report, continue the series.
8. Every residue/follow-up you file is a draft that renumbers at land.
   T-1125 rewrites prose citations automatically, but VERIFY the real id
   exists on main before citing it in your final report. A disclosed cut
   with no ticket is a TICK011 finding -- file it or state why not.
   NEVER hand-refile a draft (read its body out, `frob ticket new` a
   fresh one on main, delete the draft's block, string-swap citations) --
   that recipe is lossy: it discards the draft's evidence and Done report
   (T-1636: 12 evidence ids + a 12KB Done report lost, recoverable only
   via `git show <sha>~1:tickets.md` archaeology) and, on any `write_
   ticket` call, now WARNS loudly about exactly that loss (T-1637's
   content-loss guard, `frob.tickets._store._check_no_content_loss`) --
   heed the warning, do not repeat the recipe anyway. If a draft needs a
   real id BEFORE its own land (a coordinator manually refiling residue
   recovered from an abandoned worktree, or promoting several drafts at
   once), `frob ticket promote <draft-id>` (T-1637) is the first-class,
   atomic replacement: it allocates the next real id and renumbers the
   ledger block plus every code reference in one call (`renumber_one`
   under the hood, same primitive `frob ticket renumber <old> <new>`
   exposes directly for a case where you already know both ids), carrying
   evidence/Done report/scope across intact because it RENAMES the same
   ticket object rather than reconstructing a fresh one.
9. `uv run frob ticket land` (T-1175) prints its own `LAND-PROOF:` line
   after every real (non-dry-run) land -- `commit=<sha>
   is_ancestor_of_main=True/False state_on_main=<state>
   verified=True/False` -- the exact two checks (`git merge-base
   --is-ancestor <hash> main` + the ticket's state on main) this step
   used to ask you to run by hand. Read that line rather than re-deriving
   it; `verified=True` is what "landed" means here. `--finish` runs the
   SAME check internally and, only if it passes, removes `--worktree` for
   you (`git worktree remove`) -- use it once every ticket in the series
   has landed and verified, instead of a manual `git worktree remove`
   loop; a series worktree with more tickets still to land should NOT
   pass `--finish` on an early one.
10. ASCII only. No emojis. No Co-Authored-By lines. End your turn only
    with the full series report: per ticket, the land hash, evidence
    bound, and residue with verified real ids.

## 1. Worktree warm-up (do this FIRST, every time)

0. BEFORE any `git merge main` (warm-up or mid-ticket): check that no
   coordinator land is in flight -- `ps aux | grep "ticket land" | grep
   -v grep` must be empty. A land commits onto main and then may REVERT
   that commit minutes later (post-land sweep refusal, T-1456); a merge
   taken inside that window permanently carries the reverted content
   into your branch, and your later land re-introduces it as brand-new
   errors (2026-08-04 incident: a worktree merged main mid-T-1198-land
   and inherited its reverted `_multifile.py` plus that file's INV006/
   TEST001 findings). If a land is running, wait for it to exit and for
   `git -C <root> log --oneline -1` to be stable across ~30s, then merge.

1. `git merge main` in the worktree, then verify the tip:
   `git log --oneline -1` must show a commit that is `main`'s current tip
   or an ancestor merge of it -- not the worktree's stale creation base.
   Worktrees here have been created from a stale base before; skipping
   this step has silently reverted already-landed features (see the
   T-0167 round-1 incident below). **This is a hard MUST, not a
   nice-to-have -- run these two commands before touching anything else:**
   ```
   git merge main
   git log --oneline -1   # confirm this IS (or descends from) main's tip
   ```

   **Root cause (T-1030, confirmed by direct investigation):** the
   dispatch harness's worktree-creation tool defaults to cutting a new
   worktree from `origin/<default-branch>` (its `worktree.baseRef=fresh`
   default), NOT from the local checkout's current `HEAD`. In this repo,
   `origin/main` lags local `main` -- local `main` accumulates hundreds of
   commits across a dispatch session that are never pushed upstream, so
   `origin/main` can sit dozens to hundreds of commits behind. Three
   separate incidents (fa606fe8, b3589c3e) cut worktrees from exactly the
   stale `origin/main` tip, confirming this mechanism directly (verified:
   `git log --oneline -1 origin/main` reproduced `fa606fe8` byte-for-byte
   during the T-1030 investigation, with local `main` 81 commits ahead
   and unpushed at that time). This is harness-side behavior outside
   frob's own codebase -- frob cannot patch the tool that creates the
   worktree, only detect and warn once inside one. Plain `git worktree
   add <path> -b <branch> main` (no origin fetch involved) does NOT
   exhibit this bug -- it correctly cuts from local `main`'s tip -- which
   further isolates the defect to the dispatch tool's own default, not to
   git or frob.

   Two concrete mitigations exist but are NOT applied automatically --
   see T-1058 (filed by T-1030) for the coordinator-level
   decision on which to adopt:
   <!-- frob:waive DOC006 reason=".claude/settings.json is a real, gitignored per-clone config file (.gitignore:15) -- never tracked by design, so it can never resolve as a tracked path" -->
   - Set `worktree.baseRef: "head"` in `.claude/settings.json` so the
     dispatch tool branches from local `HEAD` instead of `origin`.
   - Push local `main` to `origin` before dispatching a wave, so even the
     `fresh`/origin-based default lands close to the real tip.
   Until one of those lands, step 1's `git merge main` + tip verification
   above is the ONLY reliable per-worktree fix -- treat it as mandatory,
   every single time, not just when something looks wrong.
2. `make core` to build the native extensions (`frob-core`, `strata-core`)
   into the worktree's own `.venv`. Fresh worktrees do not inherit a
   sibling worktree's build -- `strata_core`/`frob_core` come up missing
   and `pytest --collect-only` hard-fails repo-wide (T-0144) until this
   runs. A collection failure with `ModuleNotFoundError: strata_core` or
   `frob_core` in a fresh worktree is an environment artifact, not a
   regression -- run `make core` before concluding otherwise.
   - T-0732 landed a shared, git-common-dir-keyed `CARGO_TARGET_DIR`
     (`Makefile:197`, `frob natives build`'s own cache mechanism) so a
     second/third worktree's `make core` reuses the first worktree's
     compiled cargo artifacts instead of rebuilding from scratch -- warm
     builds measure ~11s, not the multi-minute cold-build figure T-0175
     originally measured before this landed.
3. Use `uv run frob ...` for every invocation inside a worktree, never a
   globally-installed `frob` binary. The global tool may be a different
   version, or may not see gate-affecting source changes at all (next
   section).

## 1b. NEVER `git stash` in a worktree (it is repo-global, not worktree-local)

`git stash` writes to `refs/stash`, which is SHARED across every worktree of
the repo -- it is NOT worktree-local. In a parallel multi-agent session,
`git stash` / `git stash pop` in your worktree collides with other
worktrees' stashes and silently reverts your own uncommitted state (state,
evidence, Done report) -- observed reverting whole tickets mid-flight.

Never `git stash` here. When you need to pull a fast-moving `main` into your
worktree mid-ticket, COMMIT your work-in-progress first (that is the workflow
anyway -- one clean commit per ticket), THEN `git merge main` (or rebase);
git's 3-way merge preserves your committed work per-file and surfaces real
conflicts as conflicts. If a merge conflicts in `tickets.md`, resolve it by
KEEPING BOTH appended sides (the ledger-splice rule, section 10) -- never by
stashing. Committed work cannot be silently lost the way stashed work can.
A mid-ticket merge to pull fast-moving CODE is fine; but do NOT merge main
late just to sync `tickets.md` -- finalize the ledger via the restore +
`done-report` recipe in section 10b instead (a late ledger merge corrupts
sibling tickets).

**This is now backed by a mechanical guard, not just this prose (T-0574).**
Four agents ran `git stash` in one session despite this section existing --
prose alone was not enough. `frob scaffold apply` installs a `.git/hooks/
reference-transaction` hook (`frob.scaffold._managed`'s stash-guard block)
that refuses any `git stash` while `git worktree list` shows more than one
worktree for the clone, with `fatal: ref updates aborted by hook` and a
pointer back to this section. This required actually checking git's hook
surface rather than assuming one exists: a `pre-stash` hook is absent
natively, and neither of the two obvious substitutes actually intercepts
`git stash` -- an `alias.stash` override is silently ignored by git (aliases
cannot shadow a built-in subcommand name, verified empirically) and the
existing `pre-commit`/`pre-merge-commit` hooks never fire for a stash either
(`git stash` builds its commits via `commit-tree` plumbing, not `git
commit`). The `reference-transaction` hook (native, git >=2.28) is the
option that actually works: it fires for every ref update including
`refs/stash` and can abort the transaction. Its own coverage limits are
documented in `frob.scaffold._managed`'s module-level comment -- it is a
per-clone hook (bypassable by an overridden `core.hooksPath`, a deleted
hook file, or a non-CLI git binding), not an unbypassable sandbox; commit
your WIP instead of relying on it as the only line of defense.

Dispatch tooling should also mechanically inject the worktree-lease env
this playbook otherwise just tells you to remember: `eval "$(frob agent env
<worktree-path>)"` prints `export FROB_WORKTREE=...` / `export
FROB_AGENT=1` for a given worktree (T-0574) -- the same two vars section 1
and section 3b's `--only` refusal both depend on, now derivable mechanically
instead of hand-set per dispatch.

## 1b2. A conflicted `stash pop` stages files, and ledger auto-commits sweep the whole index (T-1403)

The second-order failure mode behind section 1b, root-caused from the
c2fd45da incident: a conflicted `git stash pop` does not just conflict --
it AUTO-STAGES every file that merged cleanly, leaving them sitting in the
index of whichever checkout the pop ran in. `git reset --merge HEAD` backs
out the conflicted files, but anything the pop staged cleanly can survive
in the index unnoticed.

The ledger auto-commit every `frob ticket new`/`start`/`drop`/`fail`
performs (`_add_and_commit_tickets_md`) then runs `git add tickets.md`
followed by a bare `git commit -m <message>` -- and a bare `git commit`
commits the ENTIRE index, not just what was added for it. Result: the
pre-staged leftovers land on main inside a `chore(tickets): file T-####`
commit whose message has nothing to do with them. In the incident,
T-1390's in-progress `_land.py` + test changes landed under c2fd45da
("file T-1402 ..."), poisoning future `git blame`/bisect archaeology.

Rules that follow:

- After ANY stash mishap or merge back-out on a shared checkout, run
  `git status` and confirm the index is EMPTY before running any frob
  verb that auto-commits (`ticket new`/`start`/`drop`/`fail`, land).
  `git restore --staged .` clears accidental staging without touching
  the working tree.
- Never keep unrelated changes staged-but-uncommitted on the shared main
  checkout while ticket verbs run there. Staged state is invisible
  crossfire for every auto-commit.
- The mechanical fix (pathspec-limiting the ledger commit so it CANNOT
  carry passengers) is T-1432; until it lands, the index-hygiene check
  above is the only line of defense.

## 1c. NEVER edit `.git/info/exclude` (it is repo-global, not worktree-local)

Same hazard class as section 1b's `git stash`, same root cause: `.git/
info/exclude` lives under the COMMON `.git` dir every worktree of a clone
shares (`git rev-parse --git-common-dir`), not a per-worktree path. It
looks like a personal, untracked `.gitignore` -- but adding an entry
there to silence `git status` noise from your own scratch files affects
`git status`/`git add -A` in EVERY worktree of the clone and `main`
simultaneously, permanently, until someone notices and removes it.

A real incident: an agent added `src/frob/render/` to `.git/info/exclude`
to hide its own in-progress untracked files. That did not untrack
anything already committed -- but it gave a real, git-tracked source
directory a standing blind spot: every NEW file added under it
afterward, by any agent in any worktree, silently never showed up as
untracked and never got `git add -A`ed or committed. The whole T-0448
foundation went missing this way before anyone noticed.

Never add an entry to `.git/info/exclude` to hide work-in-progress or
quiet `git status`. If a path is genuinely generated/vendored and should
never be tracked, it belongs in the repo's tracked `.gitignore` instead
(reviewable, shared, and NOT this hazard) or scoped narrowly enough that
it cannot shadow a real source directory. `frob check`'s `excludehazard`
stage (EXCL001, unwaivable -- docs/modules/gates.md#excl001-t-0465)
statically flags any existing entry that shadows tracked source; treat a
finding there as a hard stop, not something to waive around (it cannot
be waived at all).

## 1d. Route multi-sentence ticket prose through a `--*-file` flag, never inline shell text

Long ticket prose passed inline through bash as a quoted `--body`/
`--reason`/`--why` argument is exposed to the shell's own command
substitution: a backtick or `$(...)` sequence anywhere in that prose gets
executed by bash BEFORE frob ever sees the string, silently corrupting the
ticket body/reason with whatever that substitution produced (this bit
ticket bodies repeatedly in one session -- T-0627, T-0697, T-0735, T-0736
all lost backticked fragments this way). Every ticket-mutating subcommand
that accepts free-text prose has a file-input twin that reads the text
verbatim from a path instead, structurally avoiding the shell entirely:

- `frob ticket new --body-file PATH` (instead of inline `--body TEXT`)
- `frob ticket new --acceptance-file PATH` (instead of repeated
  `--acceptance TEXT`; blank-line-separated blocks, one criterion each --
  see docs/modules/tickets.md#--body-file--acceptance-file-t-0737)
- `frob ticket scope <id> --reason-file PATH` (instead of inline `--reason
  TEXT`)
- `frob ticket done-report <id> --why-file PATH` (T-0458, the original
  precedent this pattern mirrors)

Write the prose to a temp file first (in your scratch area, not inside the
repo tree), then pass `--*-file <path>`. Reach for inline `--body`/
`--reason`/`--why` only for genuinely short, single-clause text with no
backticks, `$`, or quotes worth worrying about.

## 2. Gate-affecting source only takes effect via

- `uv run frob ...` (editable install picks up local source changes on
  every invocation), OR
- a full `uv tool install` reinstall (`make install-tool`) followed by
  `rm -rf .frob` to drop stale cached state.
Editing `src/frob/gates/**` (or any gate-consulted module) and then running
a stale globally-installed `frob` binary silently checks against the OLD
gate logic. If a gate change does not seem to be firing, confirm which
`frob` is actually running (`which frob` vs `uv run frob --version`) before
assuming the change is wrong.

## 3. Never pipe state-changing or verifying commands through tail/grep/head

Run `frob check`, `frob test`, `pytest`, `git merge`, `frob ticket start`,
and similar commands BARE and inspect the full output afterward. Piping
through `| tail`, `| grep`, `| head` masks the real exit code (the shell
reports the pipeline's last stage, not the command you actually care
about) -- this has caused silent failures where a command failed but the
truncated output looked clean. If output is long, redirect to a file and
read the file, or scroll -- do not filter the live command.

## 3b. Foreground + explicit `timeout` wrapper is the ONLY sanctioned pattern (T-1004)

As a dispatched sub-agent, backgrounding a verification is never a choice
that ends well -- there is no agent-initiated background mode where the
completion notification can actually reach you. Do NOT run pytest / frob
check / builds with `run_in_background` (or set a `Monitor`) and then end
your turn "waiting for the notification". The moment you end your turn
with no live background children, no notification will EVER arrive -- the
mission silently stalls until a coordinator manually notices and pokes
you. A full-drive coordination-churn audit measured this as the single
largest recurring stall class in this repo's history (~10 occurrences,
`docs/audits/coordination-churn.md` item 5): an agent runs a long
command, the harness auto-backgrounds it at ~120s, and the agent then
waits forever on a notification that structurally cannot arrive.

The sanctioned pattern is mechanical, not just prose discipline: run
every verification command in the FOREGROUND, wrapped in an explicit
`timeout` comfortably under your harness's auto-background cap, so a
command that runs long fails loudly and immediately with output you can
act on in-turn -- never a silent stall:

```
timeout 100 uv run frob check --only "$s"
timeout 100 uv run pytest tests/unit/test_foo.py -p no:cacheprovider -q
```

Pick a `timeout` value with margin under the ~120s cap (100-110s leaves
room); a command that trips it exits nonzero instead of crossing into
auto-background territory. There is no sanctioned exception left to this
rule: `make coverage` (section 6b) is not run by a sub-agent at all,
foreground or background, full stop -- it is a coordinator-only step.

**A bare `frob check` is the single most common way to trip the
auto-background trap by accident** (T-0627: 4+ occurrences in one session
before this was fixed). A full check/gates pass on this repo measures
well past the ~120s foreground cap on its own -- an agent who runs plain
`frob check` is not choosing to background it, but the harness does it
anyway the moment the timeout hits, and the stall described above follows
automatically. As of T-0627, this is a hard stop rather than a trap: when
`FROB_AGENT` is set in your shell (T-0574 -- true for every dispatched
worktree agent), a bare `frob check` with no `--only`/`--budget`
selection REFUSES immediately (exit 1) instead of running and stalling.
Use `--budget` or the manual `--only` loop below every time; do not reach
for `FROB_ALLOW_FULL_CHECK=1` (the escape hatch, meant for a
coordinator's own shell, not a sub-agent's) just to silence the refusal.

**Recipe 1 -- `frob check --budget SECONDS` (T-1004, preferred whenever
you just want "whatever fits, safely, in one shot" rather than a specific
named stage):** self-selects and orders `--only` stage groups to fit
inside `SECONDS`, using a rolling estimate of how long each group
actually took last time (persisted in `.frob/check-budget-timing.json`,
seeded from a conservative ~90s default the first time a group is
measured). It runs the selected subset in ONE foreground, `timeout`-
wrapped invocation, updates the timing estimate for every group it ran,
and -- if anything did not fit -- persists exactly which groups are still
outstanding (`.frob/check-budget-state.json`) and reports them LOUDLY: a
`BUDGET001` warning naming every deferred group by name, never a silent
drop. Re-running the identical command continues from the resume state
instead of restarting from the top:

```
timeout 110 uv run frob check --budget 100
# BUDGET001 names anything deferred -- just run it again to continue:
timeout 110 uv run frob check --budget 100
```

This removes the main reason an agent used to reach for a long/
unbounded command in the first place: you never have to enumerate stage
names yourself, and you never have to guess how much is left --
`--budget`'s own output tells you, in the same invocation that ran what
it could. Add `--ticket T-XXXX` / `--json` exactly as you would to a
single `frob check` call.

**Recipe 2 -- the manual `--only` loop (T-0627; use this when you want an
exact stage by name, or for `--stamp-baseline`'s own chunking, which
`--budget` does not cover -- see the next paragraph and section 6):** run
one `--only` stage-group per invocation, each measured comfortably under
the ~90s per-stage budget on this repo, `timeout`-wrapped per the rule
above:

```
for s in $(timeout 30 uv run frob check --only list); do
  timeout 100 uv run frob check --only "$s"
done
```

<!-- frob:enumerates src/frob/check/__init__.py::_STAGE_GROUPS members="lint,static,gates-fast,gates-native,gates-security" -->
`uv run frob check --only list` prints the current stage-group names, one
per line (`lint`, `static`, `gates-fast`, `gates-native`,
`gates-security`) -- discover them this way rather than hardcoding the
list, since new groups may be added later. Add `--ticket T-XXXX` /
`--json` / `--delta` to each iteration exactly as you would to a single
`frob check` call; every existing flag composes with `--only` unchanged.
A stage-group name is just a preset `--only` value (see
`frob.check._STAGE_GROUPS`) -- naming an individual tool (`ruff`) or gate
(`doclink`) directly still works exactly as before, unaffected.

`frob check --stamp-baseline` used to share this exact hazard (it ran one
undelta'd all-gates `run_gates` call, same as a bare `frob check` -- T-0751
measured ~187s wall, ~172s inside `run_gates` alone). As of T-0751, a bare
`--stamp-baseline` (no `--only`) is now explicitly a COORDINATOR-ONLY path,
same shape as `make coverage` (section 6b) -- running every gate chunk back
to back in one process is still slower in total than the old single call
(re-loading gate inputs per chunk adds overhead: measured ~240s wall for
the naive in-process chunk-and-sum), so it does not help a dispatched
agent and must not be run from one. An agent instead passes `--only
<group-or-gate>` (repeatable, exactly like a normal `frob check --only`) to
`--stamp-baseline` itself: each invocation runs and records just that
chunk's gates into a scratch accumulator
(`.frob/baseline-chunks.json`, `_baseline_chunks_path`), and the moment
every gate has been covered across however many separate calls that took,
the real `.frob/baseline` is (re)stamped from their union and the scratch
file is deleted -- so N separate, individually-cheap CLI calls converge on
exactly the same baseline the old one-shot call used to produce. Under
normal load the three stage groups (`gates-native`, `gates-security`,
`gates-fast`) each stay comfortably under the cap (~19s/~24s/~87s
measured); under contention (multiple agents' `frob` processes competing
for CPU, as in a busy parallel-drive session) `gates-fast` specifically can
still push past 120s on its own since it is the largest single group --
split it further by passing individual gate ids (any bare gate name works
via `--only`, not just a stage-group alias), e.g.:

```
timeout 100 uv run frob check --stamp-baseline --only gates-native
timeout 100 uv run frob check --stamp-baseline --only gates-security
timeout 100 uv run frob check --stamp-baseline --only test
timeout 110 uv run frob check --stamp-baseline --only drift --only coverage --only invariant \
  --only policy --only doclink --only docanchor --only fuzz --only release \
  --only decisions --only tickets --only refs --only registry --only compliance \
  --only docblocks --only walk_lint --only excludehazard --only debt --only deprecated \
  --only render_lint --only parse_failures --only lang_conformance \
  --only lang_project_conformance --only scope --only prework --only fmt --only affect_drift \
  --only ffi_boundary
```

(`test` split out on its own because it is the single heaviest gate in
`gates-fast`, ~35s alone even unloaded.) Order does not matter and neither
does batching -- the accumulator only cares that the union of every gate id
seen across calls eventually covers every gate that exists; each call logs
how many of the total it has covered so far, so a `chunk recorded (N/35
gate(s) covered so far)` line means keep going, not that something failed.
`--budget` (Recipe 1 above) does not drive `--stamp-baseline` -- it self-
selects `--only` groups for a normal check run, not the gate-only
accumulator `--stamp-baseline` builds; use this explicit `--only` chunking
for stamping a baseline specifically.

## 3c. A verification that cannot fit the timeout is a COORDINATOR step

Section 3b's foreground-`timeout` rule and section 6b's `make coverage`
carve-out leave one trap open, and it has been walked into: a brief that
asks a sub-agent for a verification which structurally cannot finish
inside the ~100s foreground budget. The full unscoped suite (`uv run
pytest -n 4` over the whole tree) is the common case; a full unscoped
`frob check` is another. Section 3b forbids backgrounding it, and no
timeout value makes it fit, so the agent is handed a required step with
no sanctioned way to perform it.

What happens next is improvisation, and it is expensive. The measured
instance (2026-08-01, T-1392): an agent launched the full suite, watched
it via ~40 successive reads of the growing log file, and narrated a
percent-complete line after each one. It spent its context window on log
tails instead of on the five failures it was dispatched to diagnose --
the worst possible trade, and one that makes a weak fix likely.

The rule, generalizing 6b beyond `make coverage`:

- A dispatched sub-agent runs ONLY verifications that fit comfortably in
  a foreground `timeout` -- the specific failing node ids, each touched
  test FILE in full, and the test files covering any production module it
  changed. One command per file.
- Anything that cannot fit -- the full unscoped suite, `make coverage`, a
  full unscoped `frob check` -- is a COORDINATOR step, run after the land,
  never delegated.
- If a command unexpectedly trips its timeout, REPORT that fact. Do not
  background it, do not poll a log for it, and never narrate progress
  percentages. Report a result or a blocker, nothing in between.

Coordinators: do not write "run the full suite" into a dispatch brief.
You own that step. Ask the agent for the scoped runs above, then measure
unscoped yourself -- which you must do regardless, per section 6c.

## 4. Scope conventions

- `tickets.md` is always in scope, implicitly, for any ticket -- the Done
  report lives there.
- Touch only files/symbols matching the ticket's declared `scope` globs.
  Anything else you find that needs fixing gets filed as a new ticket
  (`frob ticket new`), not silently folded in.

## 4b. Land-owned files are untouchable in a worktree (T-0731)

`pyproject.toml`'s `version = "..."` line, `CHANGELOG.md`, and `uv.lock`
belong to `frob ticket land` EXCLUSIVELY -- never bump the version, never
hand-append a changelog entry, and never touch the lockfile yourself in a
worktree, no matter what a ticket's plan or an older Done report from
before T-0731 implies. This used to be the single largest measured
coordinator time sink: every concurrent public-API ticket collided on
these same three files, because REL001 used to force an in-worktree
bump-and-chase (bump, watch a sibling worktree bump past you, re-bump,
resolve the resulting merge conflict by hand -- repeat). That dance is
gone, not just discouraged:

- REL001's version-bump/changelog half is suppressed automatically
  whenever `FROB_AGENT` is set (true for every dispatched worktree agent,
  T-0574) -- `frob check`/`frob check --ticket T-XXXX` will not ask you to
  bump anything. The open-debt and expired-deprecation halves of REL001
  still run and still gate you; only the bump/changelog half is affected.
- `frob ticket land` computes the version bump AND auto-generates the
  CHANGELOG.md entry from the ticket id/title/kind at land time
  (`_apply_release_bump_for_land`, T-0338/T-0731) -- the changelog is
  derived state now, never something a worktree commits by hand.
- A scaffolded `pre-commit` hook mechanically refuses a worktree commit
  that touches CHANGELOG.md, uv.lock, or `pyproject.toml`'s version line
  at all, unless `FROB_LAND_INTERNAL=1` is set (land's own escape hatch,
  never set by a worktree agent). `tickets.md` gets a warning, not a
  refusal, on the same commit -- reliably telling a CLI-written ledger
  change from a hand-edit from inside a shell hook is not solved yet
  (v1 heuristic); treat the warning as a prompt to double check you used
  the `frob ticket` CLI, not permission to ignore it.

If you find yourself editing any of these three files for a reason other
than the guard hook itself (this ticket's own scope), stop -- that is a
sign the plan assumed the old bump-and-chase workflow. File a ticket or
say so in your Done report; do not work around the guard.

## 5. Evidence recording

- Evidence ids must use real class/function names and must resolve against
  a fresh `pytest --collect-only` pass -- never claim a node id you have
  not actually observed collected.
- `frob:tests` directives use the `path::Class.method` (or `path::function`)
  qualname form, matching what `pytest --collect-only -q` prints.
- Never claim a test count you did not personally observe in command
  output. "Should pass" is not evidence; a pasted pass count is.
- Docs-only tickets with no pytest surface of their own: do not invent a
  test. Record the existing CLI-dispatch integration test as evidence
  instead, per the T-0167 precedent:
  `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches`.
  Add a small drift-lock test only if a gate actually demands one (e.g. a
  doc that must stay in sync with a generated list) -- do not add tests to
  satisfy a feeling of thoroughness.
- Run the CLI evidence-collection step (`frob ticket evidence` / a fresh
  `pytest --collect-only`) from a natives-built checkout (`make core` has
  run) -- otherwise repo-wide collection hard-fails (T-0144) and the CLI
  cannot record anything, for any ticket, not just ones touching strata.

## 5b. Recording evidence for `tests/system/**` needs no `FROB_AGENT`/`FROB_WORKTREE` care (T-0880, fixed)

Section 1's `FROB_WORKTREE=<path>` / `FROB_AGENT=1` shell env used to leak
into `tests/system/**`'s own `run()` helper (`tests/system/conftest.py`),
which spawns the real `frob` CLI as a subprocess via `os.environ | env`.
Because that merge inherited the *dispatching* agent's own lease vars, a
system test that called `run("check", ...)` unscoped inherited
`FROB_AGENT` and tripped the section 3b bare-check refusal, and a test
running `frob check`/`stamp-coverage` against its own `tmp_path` inherited
`FROB_WORKTREE` and tripped the section 12b worktree-lease guard (cwd !=
leased worktree) -- both spurious, since these tests simulate an end user
invoking the CLI directly, never a dispatched worktree agent.

`run()` now strips `FROB_AGENT`/`FROB_WORKTREE` from its base environment
before merging in a test's own `env=` overrides, so a dispatching agent's
shell-level lease vars can never leak into the subprocess under test. A
test that specifically wants to exercise `FROB_AGENT`/`FROB_WORKTREE`
behavior still can -- pass it explicitly via `run(..., env={"FROB_AGENT":
"1"})`, as `TestCheckAgentRefusal` already does. You do not need to unset
your shell's lease env before recording evidence for `tests/system/**`
tickets; the helper handles it.

## 6. Gate measurement discipline

Prefer `frob check --delta` against a stamped baseline over stash-isolation
dances (stash changes, run check, unstash, diff).

T-1346 turned the digest-keyed gate-result cache ON by default for every
`frob check`. If a gate reading looks impossibly stale (e.g. a DRIFT001
that survives the `frob ack` you just ran -- the gate-cache staleness bug filed from the T-1436 session),
re-measure once with `FROB_NO_GATE_CACHE=1` before trusting or reporting
it; a cached-vs-fresh disagreement is itself a finding worth a ticket.

```
timeout 100 uv run frob check --stamp-baseline --only gates-native      # once, before starting work
timeout 100 uv run frob check --stamp-baseline --only gates-security    # (chunked -- see section 3b)
timeout 100 uv run frob check --stamp-baseline --only gates-fast         #
# ... implement ...
timeout 110 uv run frob check --budget 100 --delta   # or the --only loop; every flag composes with --budget
```

A missing or stale baseline degrades `--delta` to the full violation set
with a warning -- re-stamp if the tree has moved significantly since the
last stamp. `--stamp-baseline` and `--stamp-coverage` are independent
artifacts (`.frob/baseline`, `.frob/coverage-stamp`); stamping one does not
touch the other.

New public symbols need both a `frob:doc` edge and a `frob:tests` edge --
`COV001` (missing doc) and `TEST001` (missing test) are ERROR-level gates,
not warnings. Add both at the point you add or change the symbol, not as a
follow-up.

**`--stamp-baseline` is no longer a one-shot, accept-the-risk step for a
dispatched agent** (T-0751 fixed the hazard T-0627 had left as future
work). A bare `--stamp-baseline` (no `--only`) is now a coordinator-only
path, same as `make coverage` (section 6b) -- see section 3b above for the
full explanation and the exact chunked recipe an agent must use instead
(`--stamp-baseline --only <group-or-gate>`, repeatable across as many
separate CLI calls as needed; results accumulate in
`.frob/baseline-chunks.json` until every gate is covered, then the real
stamp is written once).

## 6b. Do NOT run `make coverage` as a dispatched sub-agent -- you cannot wait on it

`make coverage` runs the full suite and exceeds the 120s foreground cap, so
the harness auto-backgrounds it and your turn ends. As a DISPATCHED SUB-AGENT
you fundamentally CANNOT observe its completion: the completion notification
is routed to the coordinator, not to you. Backgrounding it (even with a
`Monitor` or an `until`-loop "wait") just makes you yield and loop "waiting
for make coverage" forever until the coordinator nudges you -- a wasted
resume cycle every time. Do not do it.

Instead, verify your change the FAST way and let the coordinator stamp
coverage at land:

- Run only YOUR OWN new/changed test files, foreground, fast:
  `uv run pytest <your test files> -p no:cacheprovider -q`. This proves your
  change works and stays well under 120s.
- Run `uv run frob check --ticket T-XXXX` (scoped; needs no coverage stamp)
  for gate verification, and `uv run frob check --delta` for new-violation
  triage.
- Record evidence, write the Done report, and COMMIT -- without ever running
  `make coverage`.
- The COORDINATOR runs `make coverage` + `frob check --stamp-coverage` once,
  at land, against the merged result. That is the only place the full-suite
  coverage stamp belongs.

(If you hit `NativeExtensionUnavailable`, that's a missing native, not a
coverage problem: `make core` then `frob test --collect`, and re-run your
targeted tests.)

The coordinator, running at the top level, CAN wait on `make coverage`
(background + a Monitor/until-loop) because completion notifications come
back to it -- so the full-suite stamp is a coordinator responsibility, not a
sub-agent one.

## 6c. A `--only`/`--ticket`-scoped "0 findings" is not a package-clean claim (T-1351)

`frob check` now prints its own `gate:scope-note` line whenever `--only`
and/or `--ticket` could make a clean-looking run be misread as "the whole
package is clean" -- read it before reporting a burn-down package clean,
not after. This exists because it already went wrong twice for real:

- **T-1293**: a burn-down agent verified with `frob check --only test
  --ticket T-1293`, saw "0 findings", and closed the ticket reporting its
  package clean -- it had actually fixed 1 of 64 TEST005 findings. `--ticket`
  does NOT filter most gate families' violation counts to the ticket's
  scope (verified directly: `gate:TEST`, `gate:COV`'s COV001, etc. report
  the exact same repo-wide counts with or without `--ticket`) -- only
  `gate:SCOPE`/`gate:PREWORK` and the diff-driven checks folded into
  `gate:COV` (COV002/TODO001) and `gate:FMT`/`gate:AFFECT` are actually
  scoped to the ticket's touched set. A scoped-LOOKING "0 findings" from
  any other gate is a repo-wide number, not a ticket-scoped one.
- **T-1337**: an agent verified with `frob check --only opaque --ticket
  T-1337` and landed 2 new INV006 errors it never saw, because `--only
  opaque` never ran `gate:INV` at all -- absence of a result is not
  evidence of a clean result.

**The measurement protocol for a coverage-gated (TEST005/TEST006) burn-down
specifically**: a package's real TEST005 count can only be trusted against
a FULL, unscoped `make coverage` run's stamp (section 6b above: this is a
coordinator-only step, not a sub-agent one) -- a `--ticket`-scoped or
locally-scoped `pytest --cov=<subset>` run produces a `coverage.xml` that
only measures that subset, and TEST005 silently SKIPS any symbol whose
whole FILE has no coverage data at all (by design, to tell "never
measured" apart from "measured and failing" -- see `_test005_symbols`'s
docstring in `src/frob/gates/_coverage.py`) -- so a locally-scoped
coverage run structurally cannot produce a trustworthy TEST005 count for
anything outside what it measured, and will look emptier than reality
everywhere else. Never substitute a scoped `pytest --cov` run for the
full `make coverage` stamp when reporting a TEST005 burn-down number.

To verify your own ticket's package is actually clean (not just "the
subset I selected reported clean"): run the RELEVANT gate family
unscoped (no `--only`, no `--ticket`) and read its `gate:<FAMILY>` line
directly, or read `gate:scope-note`'s disclosure on a scoped run and
confirm none of the families it lists as "not run"/"repo-wide, not
filtered" are ones your claim depends on.

## 6d. TEST005 reads `coverage.xml`, and `make coverage` DELETES it

`make coverage`'s recipe ends with `frob clean -y`, which removes
`coverage.xml` from the repo root. So the moment a coverage run finishes,
the artifact the TEST005 gate reads is gone. Any `frob check` afterwards
evaluates coverage against whatever is (or is not) on disk, which is why a
TEST005 number taken casually after a run is not trustworthy.

The run's real report survives at `.frob/coverage.partial.xml`. To inspect
or re-measure, copy it back and delete your copy afterwards:

```
cp .frob/coverage.partial.xml coverage.xml
timeout 540 uv run frob check --only test
rm -f coverage.xml
```

**Do NOT substitute `frob-coverage.lock.json` for the report.** It is
tempting -- it survives `frob clean`, so it is what is still on disk
exactly when the real data is gone -- and that convenience is the trap.
Its `module_line` map has been measured disagreeing with the
`coverage.xml` of the very run whose `source_sha` it records: 81.2% logged
for `src/frob/__main__.py` against a report showing 0 of 133 lines hit,
65.1% for `src/frob/serve/_socketd.py` against 0 of 264. That defect is
T-1401; until it closes, the lock is not evidence of anything.

This is not hypothetical caution. A coordinator read those lock values as
ground truth, concluded the per-symbol join was broken, and filed a
critical ticket (T-1398) on a premise that thirty seconds with the raw XML
would have disproved. The agent dispatched to fix it correctly tested the
premise first, found the join working, and failed the ticket. T-1398 was
then dropped.

Rule: when a coverage claim matters, read `coverage.xml` -- the primary
artifact -- and say which artifact you read. A derived record is never
evidence for a defect in the thing it was derived from.

## 6e. The "~53% of known modules join" mystery was a denominator bug, not a
## measurement gap (T-1406/T-1407)

A recurring, alarming-sounding number showed up across several
investigations: even a full, healthy `make coverage` run's committed
`frob-coverage.lock.json` only ever joined roughly half of this repo's known
`.py` modules (measured: 447 of 851, `module_join_fraction` ~0.53) -- right
next to `_DEFLATION_FLOOR` (0.5), which made it look like real coverage data
was silently going missing on every single run.

T-1407 investigated and T-1406 found and fixed the actual cause: `module_
join_fraction`'s denominator (`_known_repo_paths`) counted every `.py` file
in the WHOLE repo -- `tests/**`, scripts, everything -- even though `make
coverage` runs `pytest --cov=src/frob`, which can structurally never report
coverage for anything outside that root. 447 real `src/frob` modules divided
by 851 repo-wide modules is not a measurement gap; it is arithmetic against
the wrong denominator. `_scope_known_paths_to_coverage_roots` now scopes the
denominator to whatever root(s) `coverage.xml`'s own `<sources>` block
declares before dividing, so a healthy run's `module_join_fraction` reads
close to 1.0, not ~0.53, going forward. `_known_repo_paths` itself stays
unscoped for its OTHER caller (`_parse_classes`'s root-join disambiguation,
which genuinely needs the full repo-wide set) -- only the join-fraction
denominator narrowed.

This does NOT explain (and T-1406 does not fix) a DIFFERENT, still-open
risk T-1407 also flagged: a burn-down agent's own scoped `pytest --cov` run
(section 6b's sanctioned workaround for "don't run `make coverage` as a
sub-agent") leaves a narrow `coverage.xml` on disk that a LATER, unscoped
`frob check` can silently misread as if it were a full run's data -- there
is currently no mechanism that tells these two situations apart at read
time. A follow-up ticket (filed by T-1407) tracks adding a stamp-time
provenance check for that specific gap; this section exists so nobody
re-derives the denominator explanation from scratch first.

**T-1435 closed that gap.** `stamp_coverage` (`src/frob/gates/_coverage.py`)
now compares the CURRENT run's joined module count against the last
COMMITTED `frob-coverage.lock.json`'s own module count (`_provenance_drop`),
independent of `_DEFLATION_FLOOR`'s own self-comparison -- a locally-scoped
run can join 100% of the few modules it measured (the deflation floor alone
reads that as clean) while still covering a fraction of what the committed
lock recorded; a drop below `_PROVENANCE_MIN_MODULE_RATIO` (0.5, deliberately
the same threshold as `_DEFLATION_FLOOR` rather than a second number to keep
in sync) now refuses the stamp outright instead of silently narrowing
committed history. Skipped entirely when there is no committed lock yet (a
fresh checkout) or the committed lock itself predates
`_DEFLATION_MIN_KNOWN_MODULES` known modules (sample-size noise, same floor
the deflation check already applies). This is a read-time defense at
`--stamp-coverage`, not a fix to `frob check`'s other, unscoped TEST005
reads -- an agent following section 6b's sanctioned workaround still should
not treat a scoped `pytest --cov` run's `coverage.xml` as full-run evidence
for anything beyond its own touched set (section 6c).

## 6f. `frob ticket land` COULD silently discard a freshly stamped
## `frob-coverage.lock.json` -- confirmed and fixed (T-1434)

T-1419/T-1270 both independently observed `frob-coverage.lock.json`
reverting to an older committed value some time after a genuine, correct
stamp -- T-1270's agent found a stray lock diff at land time and resolved
it by hand with `git checkout`, without knowing why it was there. T-1434
investigated and confirmed a real, reachable defect (now fixed): the file
is essentially never inside a landing ticket's own `scope`, so whenever it
GENUINELY conflicts during `frob ticket land`'s worktree-merge (both the
worktree and main independently stamped coverage since diverging --
possible even though only a coordinator should run `make coverage`,
because a worktree can also pick up a stray local stamp from directly
running `frob check --stamp-coverage` while investigating something),
`_auto_resolve_out_of_scope_conflicts` in
`src/frob/tickets/_land_git_ops.py` used to resolve it the same way it
resolves any other out-of-scope conflict: blindly keep one side (`git
checkout --theirs`, i.e. main's side) and discard the other's data
entirely, with no freshness or ratchet comparison at all. For an ordinary
source file that is correct (main is authoritative for something the
ticket never touched); for this specific file it silently threw away real,
freshly measured coverage numbers -- exactly the "reverted to an older
committed value" shape both prior investigations saw.

Fixed narrowly, scoped to this one file: `_merge_coverage_lock_conflict`
resolves a `frob-coverage.lock.json` conflict by taking the ELEMENTWISE
MAX of both sides' `module_line` percentages (the same "never silently
lower a committed floor" principle `_apply_lock_ratchet`/T-1363 already
applies to a single side's own write, extended across a two-sided merge)
instead of picking one side wholesale. Falls back to the pre-T-1434 blind
-checkout behavior only if either side fails to parse as the expected
shape -- never worse than before, only better when it succeeds. This is a
merge-time fix, not a workflow correction: an agent hitting a stray
`frob-coverage.lock.json` diff at land time no longer needs the
`git checkout` workaround T-1270's agent improvised -- land itself now
merges it correctly.

## 6g. Run `frob check --land-parity` before writing your Done report (T-1535)

Every blind repair round on 2026-08-04/05 traced back to a worktree-check
vs. land-sweep DIVERGENCE: a `--ticket`-scoped run passed while the exact
same tree would refuse at land (a gate-result cache hid a finding until
`FROB_NO_GATE_CACHE=1`; a scoped run skipped a family the unscoped sweep
still evaluates -- SELFAUDIT whole-design, diff-driven DUP, registry-level
PII012). `frob check --land-parity` runs the EXACT evaluation the land
pre-commit/post-land sweeps run (`_unscoped_error_findings` +
`_drop_checkpoint_exempt_findings`, `frob.app.ticket_runner._land_cmd.
land_parity_findings`) against your CURRENT worktree tree, cache-bypassed,
with the T-1524 checkpoint-artifact exemptions applied -- so you can
converge BEFORE the coordinator ever lands, instead of discovering the
divergence only after a real land sweep refuses:

```
timeout 400 uv run frob check --land-parity
```

Exits 0 with a clean message when the land sweep would see zero unscoped
errors, exits 1 and prints every `(rule, file)` finding otherwise (add
`--json` for a machine-readable `{"findings": [...]}` payload), and exits
1 with a loud "could not evaluate" message on an unmeasurable run (spawn
refused, timeout, unparsable output) -- never a false-clean pass. Run this
once, section 3b's foreground-`timeout`-wrapped, right before writing your
Done report -- it is not a substitute for the scoped `--only
test/archgate/coverage/sys --ticket T-XXXX` checks section 0 already
requires, it is the one extra check that catches what those necessarily
scoped checks cannot (playbook section 6c's own scope-note: `--ticket`
narrows SCOPE/PREWORK/COV002/TODO001/FMT/AFFECT only, every other family
stays repo-wide).

## 7. Waive discipline

`frob:waive RULE-ID reason="..."` suppresses one specific violation and
must always carry a `reason=`. `WAIVE001` fires if the reason is missing;
`WAIVE002` fires if the rule id can never match anything (a waiver typo,
or a waiver for a rule that already can't fire on that line) -- both are
gate errors, not silent no-ops. Never add a blanket waiver to make a gate
go quiet; waive the specific violation with a specific, honest reason, or
fix the underlying issue.

## 8. Done-report requirements

- Report only measured numbers: command output you actually ran and read,
  not estimates or "should be" figures.
- Disclose cuts honestly. If something in the ticket's plan was not done
  (an investigation that turned up nothing buildable in scope, a mechanism
  not implemented), say so plainly in the Done report rather than let
  silence imply it was done.
- Do not claim a merge, diff, or test result is durable beyond what you
  actually verified against. A round-1 Done report that says "nothing else
  missing" based on a merge against a `main` that has since moved is
  stronger than it should be -- see the deletion-filter incident below for
  what this cost in a real case.

## 9. The deletion-filter land rule (verify before every finish)

Before finishing (committing your final state), run:

```
git diff main --diff-filter=D --stat
```

This MUST be empty of anything outside your ticket's declared scope. A
worktree created from (or merged against) a stale `main` can silently
revert already-landed features when squash-applied or merged forward --
this happened for real: a round-1 merge based on a stale `main` structurally
could not carry six files / 2331 lines of another ticket's already-landed
work forward, and it took a second `git merge main` plus this exact
deletion-filter check to catch it (T-0167 in `tickets-archive.md`). If the
filter shows deletions you did not intend, merge main again before
proceeding -- do not commit through it.

## 10. Ledger-conflict splice guidance

`tickets.md` is a shared, append-mostly ledger; concurrent worktrees can
produce a merge conflict on it. Register the `frob ticket merge-driver`
git merge driver once per clone (`docs/modules/tickets.md#git-merge-driver`)
and any `git merge`/`pull`/`rebase` touching `tickets.md` auto-
splices via `splice_ledger` instead of conflicting -- do this before
touching a worktree, not after hitting the first conflict.

If the driver is not registered (or a genuinely malformed ledger still
gets past it, and git falls back to a real conflict), resolve by hand:
keep the NEWEST state per ticket section (the most recently updated
`state:`/Done-report block for a given ticket id wins), not by
mechanically taking "ours" or "theirs" -- a naive resolution can silently
drop a state transition one side made. After resolving, audit the
open-ticket count (`frob ticket doable` / `frob ticket show <id>` on
anything touched by the conflict) to confirm no ticket regressed to an
earlier state or vanished. `frob ticket land` also resolves any
`tickets.md` conflict it hits internally via the same `splice_ledger`
call, no manual step needed there either.

## 10b. Finalizing the ledger before you report (do NOT `git merge main` to fix it)

MULTI-TICKET-WORKTREE WARNING: the restore recipe below (`git checkout
main -- tickets.md`) restores MAIN's ledger -- which does NOT contain the
closures of tickets you already finished ON THIS BRANCH. Running it for
your second/third ticket in the same worktree silently reverts your own
earlier tickets' closed states (a real incident: T-0405's closure got
reverted to queued while finalizing T-0406). For every ticket after the
first, restore from your own last-good branch commit instead:
`git checkout <your-prior-close-commit> -- tickets.md`, then replay only
the current ticket's CLI operations. Verify EVERY prior ticket's
`state:` line before your final commit.

Once your code and tests are done, DO NOT `git merge main` again to "sync"
your `tickets.md`. This is a timing trap: main keeps advancing while you
work, so any merge you do is immediately stale. Right before landing, the
coordinator lands OTHER tickets -- now `git diff main -- tickets.md` shows
YOUR older ledger as if it reverts those newly-landed tickets (a done
ticket appears in-progress, its evidence/Done-report deleted). Hand-fixing
the reverts one by one always misses some. In a single session this
reverted 7 sibling tickets in one worktree (T-0281) and silently re-opened
a just-landed ticket in another (T-0379). The `git merge main` at warm-up
(section 1) is fine -- it is merging LATE, near reporting, that corrupts.

Finalize the ledger with this exact recipe instead (no `git merge`, no
hand-edit of `tickets.md`, no `git stash`):

1. Overwrite your worktree ledger with current main's, verbatim:
   `git checkout main -- tickets.md`
   `git add tickets.md && git commit -m "chore: restore tickets.md to main before landing T-XXXX"`
   Then `git diff main -- tickets.md` MUST be empty. Confirm it.
2. Write ONLY your own Done report through the single-writer CLI (T-0458):
   `uv run frob ticket done-report T-XXXX --why-file <path> --base-ref main`
   (write the narrative to a temp file first; it auto-fills Changed +
   Evidence). This never touches another ticket's block.
3. Re-record your evidence ids (idempotent):
   `uv run frob ticket evidence T-XXXX <each node id>`.
4. Refresh the pre-work sweep in place so PRE001 stays clean:
   `uv run frob ticket sweep T-XXXX` -- you do NOT need to merge main for
   this. (`frob ticket land` also refreshes the sweep at land time.)
5. Verify `git diff main -- tickets.md` now shows ONLY your ticket's own
   block. If ANY other ticket id appears in that diff, stop -- do not
   report done, and do not hand-patch it; tell the coordinator.
6. Draft-ticket edge case (T-1093 hit this): step 1's restore WIPES any
   draft ticket you filed into the worktree ledger BEFORE this recipe ran
   -- land then has no block to renumber, and your Done report's draft
   citation becomes a TICK006 phantom on main. File follow-up drafts
   AFTER step 1's restore (or re-run `frob ticket new` for any draft the
   restore ate before writing the Done report that cites it).
7. First-ticket edge case (T-1022 hit this): if YOUR ticket's
   `state: in-progress` transition was only ever written in this
   worktree's branch (never landed to main -- true for the first ticket
   a worktree works), step 1's restore silently reverts it to `queued`,
   and land later refuses the `queued -> done` close as an
   InvalidTransition. After step 1, check your own block's `state:` and
   re-run `uv run frob ticket start T-XXXX` if it regressed -- this is
   self-repair, not corruption.

## 11. Ticket workflow

1. `frob ticket start T-XXXX` -- runs the pre-work sweep (dup+xref) over
   scope; read the ticket's Description and Plan sections fully before
   touching anything.
2. Implement strictly inside the declared `scope` globs.
3. Record evidence (section 5) and write the Done report into `tickets.md`
   (section 8).
4. In a review-gated flow: DO NOT close the ticket yourself. Leave it for
   the reviewer. Only close directly when explicitly told the flow is not
   review-gated.
5. `frob ticket close T-XXXX` (when you are the closer) re-verifies
   evidence and the Done report section from scratch -- it is not a
   formality you can bypass by editing the ticket frontmatter directly.

## 12. Style

- ASCII only, no exceptions.
- No emojis, anywhere.
- No `Co-Authored-By` line in commits, ever.
- Conventional commits: `type(scope): imperative summary`, no trailing
  period, body explains WHY not WHAT.
- `ruff` must be stable under BOTH the PATH `ruff` and the project-pinned
  version (`uv run ruff`) -- a change that's clean under one and dirty
  under the other is not actually clean. Check both before reporting a
  ruff pass.

## 12b. Coordinator worktree cleanup (T-0836)

A coordinator that hand-sweeps stale `.claude/worktrees/` entries with a
raw `git worktree remove` loop, skip-listed only by git's own dirty
check, is not safe: git's dirty check cannot see a LIVE agent between
writes -- a worktree an agent is mid-diagnosis in (nothing uncommitted
yet) reads exactly like an abandoned one. This happened for real: a
coordinator's bulk sweep of 68 stale worktree registrations destroyed a
live agent's clean, in-progress worktree because the skip-list had no way
to tell the two apart.

Use `frob worktree sweep [path] [--dry-run] [--min-age HOURS]` instead of
a raw bulk `git worktree remove` loop, always. It reuses this repo's own
cross-worktree lease machinery (`frob.tickets._leases.read_all_leases`/
`is_lease_ttl_expired`, section 1's T-0473/T-0782/T-0835 lineage) to tell
a genuinely-idle worktree from a live one, removing a candidate ONLY if
it is BOTH clean AND holds no live (unexpired) lease for any
non-terminal ticket -- an expired lease is treated the same as a dead
agent's abandoned worktree and does not block removal. `--dry-run`
previews every verdict (`removed` / `kept:lease(<ticket> <age>)` /
`kept:dirty` / `kept:age`) without removing anything; run it first when
sweeping a session with multiple concurrent agents. `frob worktree sweep`
never deletes a branch -- only the worktree registration/checkout.

Per-worktree verify-then-remove (checking a SPECIFIC just-landed ticket's
worktree by hand: confirm its ticket is closed/dropped/failed, confirm
`git status --porcelain` is empty, then `git worktree remove <path>`) is
still fine for a single worktree you just finished landing yourself --
the hazard is specifically a BULK sweep across many worktrees you are not
individually re-verifying one at a time. A raw bulk `git worktree remove`
loop across `.claude/worktrees/*` is forbidden; `frob worktree sweep` (or
the single-worktree recipe just described) are the only sanctioned paths.

## See also

- `docs/modules/gates.md` -- the full gate catalog, `--delta`/baseline
  mechanics in detail, and waiver semantics.
- `docs/modules/tickets.md` -- the ticket state machine and evidence model.
- `docs/guides/agentic-workflow.md` -- the human/AI split and the
  worktree-per-agent pattern this playbook assumes.
- `docs/guides/testing.md` -- the per-test pytest-timeout guard (T-0692),
  the deadlock class it catches, and how to add an override for a
  legitimately slow test.
