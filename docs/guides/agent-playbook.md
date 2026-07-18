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

## 4. Scope conventions

- `tickets.md` is always in scope, implicitly, for any ticket -- the Done
  report lives there.
- Touch only files/symbols matching the ticket's declared `scope` globs.
  Anything else you find that needs fixing gets filed as a new ticket
  (`frob ticket new`), not silently folded in.

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
produce a merge conflict on it. Resolve by keeping the NEWEST state per
ticket section (the most recently updated `state:`/Done-report block for a
given ticket id wins), not by mechanically taking "ours" or "theirs" -- a
naive resolution can silently drop a state transition one side made.
After resolving, audit the open-ticket count (`frob ticket doable` /
`frob ticket show <id>` on anything touched by the conflict) to confirm no
ticket regressed to an earlier state or vanished. `frob ticket land`
(T-0176, not yet built) is the planned one-command version of this
procedure; until it exists, this is manual.

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
