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

## 1. Worktree warm-up (do this FIRST, every time)

1. `git merge main` in the worktree, then verify the tip:
   `git log --oneline -1` must show a commit that is `main`'s current tip
   or an ancestor merge of it -- not the worktree's stale creation base.
   Worktrees here have been created from a stale base before; skipping
   this step has silently reverted already-landed features (see the
   T-0167 round-1 incident below).
2. `make core` to build the native extensions (`frob-core`, `strata-core`)
   into the worktree's own `.venv`. Fresh worktrees do not inherit a
   sibling worktree's build -- `strata_core`/`frob_core` come up missing
   and `pytest --collect-only` hard-fails repo-wide (T-0144) until this
   runs. A collection failure with `ModuleNotFoundError: strata_core` or
   `frob_core` in a fresh worktree is an environment artifact, not a
   regression -- run `make core` before concluding otherwise.
   - `make core` is a from-scratch cargo build per worktree today (minutes,
     not seconds). Sharing a prebuilt artifact across worktrees (a shared
     `CARGO_TARGET_DIR`, or a wheel cache reused by `make core`) is
     tracked separately, not yet implemented -- see T-0175's Done report
     for what was investigated and why it was not built in this pass.
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

## 3b. Never background a verification and end your turn to "wait" for it

As a dispatched sub-agent, do NOT run pytest / frob check / builds with
run_in_background (or set a Monitor) and then end your turn "waiting for
the notification". The moment you end your turn with no live background
children, no notification will EVER arrive -- the mission silently stalls
until a coordinator manually notices and pokes you (this has burned
multiple real dispatches). Run every verification command in the
FOREGROUND and wait for it in-turn, even when it takes minutes. The only
sanctioned exception is `make coverage`, which you must not run at all
(section 6b) -- everything else is foreground.

**A bare `frob check` is the single most common way to trip this anti-
pattern by accident** (T-0627: 4+ occurrences in one session before this
was fixed). A full check/gates pass on this repo measures well past the
~120s foreground cap on its own -- an agent who runs plain `frob check`
(or `frob check --stamp-baseline`, which runs the same undelta'd gates
pass) is not choosing to background it, but the harness does it anyway
the moment the timeout hits, and the stall described above follows
automatically. As of T-0627, this is now a hard stop rather than a trap:
when `FROB_AGENT` is set in your shell (T-0574 -- true for every
dispatched worktree agent), a bare `frob check` with no `--only` stage
selection REFUSES immediately (exit 1) instead of running and stalling.
Use the chunked loop below every time; do not reach for
`FROB_ALLOW_FULL_CHECK=1` (the escape hatch, meant for a coordinator's own
shell, not a sub-agent's) just to silence the refusal.

**The sanctioned chunked loop** -- run one `--only` stage-group per
invocation, each measured comfortably under the ~90s per-stage budget on
this repo:

```
for s in $(uv run frob check --only list); do
  uv run frob check --only "$s"
done
```

`uv run frob check --only list` prints the current stage-group names, one
per line (`lint`, `static`, `gates-fast`, `gates-native`,
`gates-security`) -- discover them this way rather than hardcoding the
list, since new groups may be added later. Add `--ticket T-XXXX` /
`--json` / `--delta` to each iteration exactly as you would to a single
`frob check` call; every existing flag composes with `--only` unchanged.
A stage-group name is just a preset `--only` value (see
`frob.check._STAGE_GROUPS`) -- naming an individual tool (`ruff`) or gate
(`doclink`) directly still works exactly as before, unaffected.

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

## 6. Gate measurement discipline

Prefer `frob check --delta` against a stamped baseline over stash-isolation
dances (stash changes, run check, unstash, diff).

```
uv run frob check --stamp-baseline   # once, before starting work, to record pre-existing violations
# ... implement ...
uv run frob check --delta            # reports only violations NEW since the stamp
uv run frob check --delta --ticket T-XXXX --json   # scoped + machine-readable, if needed
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

**`--stamp-baseline` itself still runs the full, undelta'd gates pass**
(T-0627: it is one of the two known-slow full-check shapes, alongside a
bare `frob check`) -- it is deliberately NOT refused under `FROB_AGENT`
(section 3b's refusal only fires for a bare, stage-less invocation), so
the command above can still exceed the ~120s foreground cap and stall the
same way. Chunking `--stamp-baseline` itself is tracked separately (T-0627
considered it and left it as future work, not silently dropped) -- until
that lands, treat `--stamp-baseline` as a one-time, accept-the-risk step:
run it once at the very start of a ticket before the tree has much
uncommitted state to lose, and prefer the section 3b chunked `--only`
loop (which every stage group is measured safe under) for every
verification pass after that.

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
git merge driver once per clone (`docs/modules/tickets.md#git-merge-
driver`) and any `git merge`/`pull`/`rebase` touching `tickets.md` auto-
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

## See also

- `docs/modules/gates.md` -- the full gate catalog, `--delta`/baseline
  mechanics in detail, and waiver semantics.
- `docs/modules/tickets.md` -- the ticket state machine and evidence model.
- `docs/guides/agentic-workflow.md` -- the human/AI split and the
  worktree-per-agent pattern this playbook assumes.
- `docs/guides/testing.md` -- the per-test pytest-timeout guard (T-0692),
  the deadlock class it catches, and how to add an override for a
  legitimately slow test.
