# frob.tickets -- git merge driver for tickets.md/rapid-debt.jsonl

Part of the `frob.tickets` reference, split out of `docs/modules/tickets.md` by T-1780 so this subject's own lease no longer blocks every other ticket working a different one; see [`docs/modules/tickets.md`](tickets.md#split-files-t-1780) for the full split index.

## Git merge driver

<!-- frob:describes src/frob/app/ticket_runner/_land_cmd.py::_merge_driver -->

`frob ticket land` (above) is the one-command path; not every
`tickets.md` conflict goes through it though -- a plain `git merge`/
`git pull`/`git rebase` between two branches that each independently
appended a ticket near the same line hits git's default line-level merge
and conflicts, requiring the manual `splice_ledger`-by-hand procedure
`docs/guides/agent-playbook.md` section 10 used to document (T-0323: this
happened by hand roughly 8 times in one coordinator session, twice
silently dropping the `evidence:` field on re-splice). Registering
`frob ticket merge-driver` as a git merge driver removes the manual step
entirely for any `git merge`/`pull`/`rebase` touching `tickets.md`, not
just `land`'s internal ones.

**One-time setup** (per clone -- `.gitattributes` alone does not install a
driver; git deliberately keeps the association (tracked, shared) and the
driver command (local, since it names an executable) as two separate
registrations):

```
git config merge.frob-ledger.name "frob ticket ledger splice"
git config merge.frob-ledger.driver "uv run frob ticket merge-driver %O %A %B"
```

**Use `uv run frob`, never a bare `frob`** (T-1443): a bare, globally-
installed `frob` binary can be stale relative to this checkout's own
`pyproject.toml` version -- exactly the hazard
`docs/guides/agent-playbook.md` section 2 warns about for every OTHER
`frob` invocation, but sharper here because git invokes this command
implicitly on every `git merge`/`pull`/`rebase` that touches
`tickets.md`, with no per-invocation chance to notice or override it.
Confirmed live during T-1371's resume (2026-08-02): a stale global
`frob` (0.184.0) registered as the driver silently ran the pre-T-1437
ledger-splice logic against a checkout whose own source was already at
0.293.0, reintroducing a defect T-1437 had already fixed. `uv run frob`
(editable install) always resolves against the invoking checkout's own
source, the same way every other command in this doc already does.

`.gitattributes` (tracked, already in the repo) then routes `tickets.md`
through it:

```
tickets.md merge=frob-ledger
```

`frob ticket merge-driver %O %A %B` is git's merge-driver protocol
verbatim: git spawns it with three temp file paths -- `%O` (merge base),
`%A` (ours), `%B` (theirs) -- and treats `%A`'s content ON DISK AFTER THE
COMMAND RETURNS as the merge result, regardless of exit status. The
handler:

1. reads `%O`, `%A`, and `%B`'s text,
2. calls the SAME `splice_ledger(ours_text, theirs_text,
   archived_ids=..., base_text=...)` `frob ticket land` uses (never a
   separate reimplementation -- one splice algorithm, two call sites),
3. overwrites `%A` with the result and exits 0 (git records a clean,
   non-conflicted merge).

`%O` (the merge base) -- T-1165 (a T-1154 follow-up): git already resolves
and hands us the true 3-way merge-base's ledger content as a ready-made
temp file, no `git merge-base` shell-out needed the way `land`'s own
internal splice call requires (`_true_merge_base`) -- is read and threaded
through as `splice_ledger`'s `base_text` param, so a genuine same-id
divergence prefers whichever side actually changed since `%O` (the T-1154
wrong-side-merge fix) through a LIVE `git merge`, not just through `frob
ticket land`'s own internal splice step. A `%O` file that is missing or
unreadable degrades to the pre-T-1165 state-rank/Done-report tiebreak
(`_newer`, no base awareness) rather than refusing the merge -- see
`splice_ledger`'s own docs above for the full three-tier fallback.

If `splice_ledger` itself fails (a genuinely malformed `%A`/`%B`, not just
a same-id divergence -- that case always resolves), the driver leaves
`%A` untouched and exits 1: git then reports the ordinary conflict for a
human to resolve by hand, exactly as if no driver were registered. A
merge driver can never turn a real parse failure into a silently-wrong
splice.

**T-1437: `archived_ids` is resolved from git objects, not the working
tree.** `splice_ledger`'s `archived_ids` argument used to come from
`_archived_ids(root)` -- a plain read of `root`'s CURRENT
`tickets-archive.md` off disk. That is wrong specifically for THIS entry
point: git invokes the merge driver as a subprocess mid-merge, one call
per conflicting path, and does not write any path's resolved content back
to the actual working-tree file until the ENTIRE merge finishes -- a
disk read from inside a live driver invocation always sees the PRE-merge
archive, even though `tickets-archive.md` is ALSO registered to
`merge=frob-ledger` and may be concurrently resolving its own new
content in a sibling invocation. The real incident: `frob ticket archive`
ran on `main` after a worktree branched, and every subsequent `git merge
main` inside that worktree resurrected the just-archived ticket into
`tickets.md`, because the disk-based archived-ids read could never see
main's new archive content in time.

`_archived_ids_for_merge_driver` (`src/frob/app/ticket_runner/_land_cmd.py`)
fixes this by reading `tickets-archive.md` from git OBJECTS instead:
`git rev-parse MERGE_HEAD` names the commit git is merging in (set for the
whole duration of an in-progress merge, real regardless of working-tree
staleness), and `git show HEAD:tickets-archive.md` /
`git show MERGE_HEAD:tickets-archive.md` read each side's actual committed
archive content directly from the object store. The union of ids parsed
from both is used, so a ticket archived on EITHER side is honored.
Degrades to the old disk-based `_archived_ids(root)` whenever `MERGE_HEAD`
cannot be resolved (not currently inside a git merge -- the ordinary case
for `frob ticket land`'s own internal, non-live-merge splice calls, which
were never affected by this defect in the first place: there `root` is
the authoritative main checkout being read FROM, not the branch being
merged, so its own disk state was never stale to begin with) or either
ref's archive content fails to parse.

## rapid-debt.jsonl merge rule (T-1873)

<!-- frob:describes src/frob/tickets/_evidence.py::record_rapid_debt -->

`rapid-debt.jsonl` is a tracked, append-only ledger at the repo root --
every rapid-profile land appends one JSON-lines record to its tail
(`frob ticket land`'s own T-1681 relaxation trail). With several agents
landing concurrently, two worktrees routinely append different records
near the same line, which -- BEFORE this fix -- git's default line-level
merge reported as a textual conflict, and nothing told an agent how to
resolve it: each one improvised by hand, on a file whose whole value is
that no debt record is ever lost. Hand-editing an append-only ledger
during conflict resolution is exactly how a record silently disappears,
and a dropped record is indistinguishable afterward from debt that was
never incurred.

**This IS handled -- do not hand-edit a conflict here.** `.gitattributes`
routes both `rapid-debt.jsonl` and `force-overrides.jsonl` (the sibling
tracked append-only ledger, `frob.tickets._force_override`, T-1762 --
covered proactively even though no `--force` override has happened yet
in this repo) through git's BUILT-IN `merge=union` driver:

```
/rapid-debt.jsonl merge=union
/force-overrides.jsonl merge=union
```

Deliberately git's built-in `union` driver, not a new frob driver (the
shape `merge=frob-ledger` above uses for `tickets.md`): union concatenates
both sides' lines, which is exactly the append-only "keep both sides"
semantics wanted, and -- unlike `merge=frob-ledger` -- it needs NO local
`git config` registration at all. That distinction matters specifically
here: the frob-ledger driver needs a one-time per-clone setup (see
"Git merge driver" above), so any worktree or fresh clone that skipped it
silently falls back to the default (conflicting) driver -- exactly the
failure mode this ticket exists to close, and a mechanism this repo does
not need to build when git already ships it. The pattern is anchored with
a leading slash for the same reason `/tickets.md` is (the anchoring
precedent this file's own historical `.gitattributes` comment records) --
unanchored, it would also match any other file named `rapid-debt.jsonl`
anywhere in the tree.

Verified by REPRODUCTION, not by inspecting `.gitattributes`
(`tests/unit/test_gitattributes_merge.py`): two branches each append a
different record to `rapid-debt.jsonl`, a real `git merge` between them
reports a clean merge (exit 0, empty `git status --porcelain`), and both
records survive with zero conflict markers.

**Exact-duplicate lines deduplicate, they do not double up.** Measured
directly (`test_identical_line_appended_on_both_sides_deduplicates`):
when both sides append the byte-identical line, git's union driver keeps
ONE copy, not two. Harmless for this file's shape -- every real record
embeds a unique commit sha, so an exact duplicate can only arise from a
retry re-emitting a byte-identical record for the same commit, and
collapsing that to one entry is the correct outcome, not data loss. No
dedup-on-read pass was added to the reader; this was a measured finding,
not a speculative mitigation.

