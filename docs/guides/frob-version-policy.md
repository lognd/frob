<!-- frob:waive REF002 reason="a policy record, deliberately singly-anchored from docs/index.md's guide index -- a second consumer would not be genuine" -->

# frob global-install version policy (T-1980)

## The problem

The `frob` binary on `PATH` (`/home/logan/.local/bin/frob`, installed via
`uv tool install frob`) and this repo's own editable build
(`uv run frob`, invoked from inside this checkout) are different
versions, and the gap grows every time this repo lands a ticket without
anyone running `uv tool upgrade frob`. Measured 2026-08-10:

```
which frob            -> /home/logan/.local/bin/frob
frob --version         -> frob 0.184.0
uv run frob --version  -> frob 0.433.0
```

A 249-version gap. Every one of the 8 frob-wired sibling repos (typani,
logand.app, lograder, aprog-private, graphite, feldspar, aprog-public,
lithos) has no local editable build of its own -- they all invoke the
same stale `PATH` binary for every `frob` command a human or an agent
runs there.

The concrete, already-observed consequence: the global 0.184.0 build
predates T-1615's uniform `--no-commit`-aware ledger auto-commit
(`frob ticket new --help` on the global build has no `--no-commit`
flag at all). Every ledger-mutating command it runs (`ticket new`,
`ticket start`, ...) therefore edits `tickets.md` and never commits
that edit. All 8 sibling repos currently sit with an uncommitted
`tickets.md` diff as a direct result -- not eight independent mistakes,
one deterministic tooling gap repeated eight times.

Beyond the ledger-commit gap, every gate, land-safety fix, and workflow
guard this repo has landed since 0.184.0 is simply absent for those 8
repos: the land-accounting hardening from this same drive (T-1967,
T-1950, T-1922/T-1955), the lease model, the acceptance preflight, and
(per the measurement below) two entire new gate families.

## Decision: staged rollout, not a blind upgrade

**Do not run `uv tool upgrade frob` as a side effect of any ticket
drain.** The global install is outward-facing operator tooling shared
by 8 production repositories that are not the subject of whatever
ticket happens to notice the skew. An upgrade is a deliberate,
separately-authorized operator action, gated on the measurement below,
never an incidental fix.

**Recorded rollout sequence** (unblocks T-1971 -> T-1552):

1. Measure the delta on ONE small sibling repo first (done below, on
   typani, 6 tickets) using the newer build via `frob check
   /path/to/sibling --only gates` -- no upgrade needed for this step,
   the target repo's own build is pointed at from outside via the
   positional `path` argument, entirely read-only with respect to that
   repo's git-tracked content (confirmed below).
2. Only after a human reviews that delta and accepts the new findings
   (or confirms none are workflow-blocking regressions), run `uv tool
   upgrade frob` once, globally.
3. Re-run the same single-repo measurement post-upgrade to confirm the
   live global build now matches what was reviewed in step 1.
4. Roll out to the remaining 7 repos one at a time, each getting its
   own dirty-ledger triage (the pre-existing uncommitted `tickets.md`
   in each repo is NOT cleaned up by this policy or by the upgrade --
   see "what this policy explicitly does not do" below).
5. Point (c) from T-1980's own filed FIX DIRECTION -- making the
   version-skew condition self-announcing at the repo level (this repo
   already has a local Claude Code hook that detects and reports it,
   observed firing correctly on this very session) rather than one
   machine's hook config -- is filed as its own follow-up ticket
   (T-1980's filing session; renumbers at land) with its own
   code-level acceptance test; it is infrastructure, not part of this
   measurement.

## Measured delta: this repo's 0.433 build against typani

Command run (from this repo's own worktree, `uv run frob`, no `--fix`,
positional `path` pointed at the sibling):

```
uv run frob check /home/logan/projects/typani --only gates --json
```

Compared against the stale global 0.184.0 build run the same way from
the same directory:

```
frob check /home/logan/projects/typani --only gates --json
```

| | 0.184.0 (global, PATH) | 0.433.0 (this repo) | delta |
|---|---|---|---|
| errors | 27 | 40 | +13 |
| warnings | 70 | 59 | -11 |

**Every one of the +13 new errors comes from two gate families that did
not exist at all in the 0.184.0 build**, not from an existing gate
getting stricter on code it previously passed:

- `OPAQUE001` (+5) -- container dynamic-key call sites
  (`src/typani/result.py`), a runtime-resolved capability indirection
  the opaque-boundary gate did not exist to catch at 0.184.0.
- `SUPPRESS001` (+8) -- a `# type: ignore`/mypy suppression comment
  whose line `ty` (this repo's own type checker integration) now
  reports as still carrying an unsuppressed diagnostic -- a suppression
  gone stale, invisible before this cross-checker gate existed.

**No previously-clean gate flipped to red.** typani's `frob check
--only gates` is already non-zero-exit under the CURRENT 0.184.0 build
(27 pre-existing errors: `DOC002`, `DOC004`, `PRE001`, `SCOPE001`,
`SELFAUDIT001`, `TICK006`) -- upgrading does not turn a green workflow
red, it adds more findings to an already-red one. The 249-version jump
is safe to review calmly rather than treat as an emergency: nothing here
silently breaks a currently-passing repo.

Warnings actually DECREASED by 11 -- some warn-level checks present at
0.184.0 were tightened into a different rule, removed, or reclassified
between versions; not independently triaged here, out of this
measurement's scope.

## Read-only confirmation

Before running either command against typani, `frob check`'s own
`--help` was checked for anything that mutates a target repo's
git-tracked content: no autofix runs unless `--fix` is passed
explicitly (neither measurement run above passed it), and `--stamp-
coverage`/`--stamp-baseline` (the only two flags that intentionally
write) were not passed either. Both runs DO write to the target repo's
own gitignored `.frob/` local cache/parse-artifact state (same as any
normal `frob check` invocation in any repo) -- this is standard,
disposable, untracked build cache, not tracked content or someone
else's in-flight work, and is excluded from version control by every
frob-wired repo's own `.gitignore` (`.frob/` is a standard entry).
`git status --short` in typani was diffed before and after both runs
and shows no change beyond the pre-existing dirty `tickets.md`/
`uv.lock` this ticket's own measurement found already present.

## What this policy explicitly does not do

- Does not run `uv tool upgrade frob`. The global install is untouched.
- Does not commit typani's (or any sibling's) dirty `tickets.md`. That
  content is in-flight work belonging to whoever created it, or to the
  upgraded tool once it exists there with the auto-commit fix.
- Does not close the T-1971/T-1552 chain -- it unblocks step 1 of
  T-1971's own plan (per T-1980's own acceptance criteria: "the
  deliverable is the recorded policy plus a measured single-repo
  result", not the upgrade itself).
