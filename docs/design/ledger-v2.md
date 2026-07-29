# Ledger v2: file-per-ticket store (design)

One sentence: replace the `tickets.md` monofile (and its splice/merge-driver
machinery) with one git-tracked file per ticket, so disjoint tickets are
disjoint git objects and merge/lease/draft/renumber/archive collapse into
ordinary git operations instead of bespoke text-splicing code.

Status: design only (T-1136). No migration in this doc's scope -- see
"Migration" below for what a separate child ticket must do, and why it is
deliberately not started here.

## 0. Why (the incident museum, read as root causes not symptoms)

Every incident below traces to the SAME structural fact: `tickets.md` is
one file holding N tickets' state, so any operation on ticket A's block is
a text-diff over a file that also contains tickets B..Z's blocks. Git,
locks, and hand-written splice code all have to work AROUND that, never
WITH it.

| Incident | Root cause in one line |
|---|---|
| T-0577 land splice regression | draft finalization + version bump + sibling Done-report preservation all had to be reimplemented as whole-file-aware merge logic because a single ticket's write is not a single git diff hunk by construction |
| T-0959 archive clobber | `tickets-archive.md` is a SECOND monofile with the same problem, and it didn't even inherit the first file's splice discipline for a long time -- doubling the surface, not halving it |
| T-1036 ledger churn rewrites | any read-modify-write of "the whole file" races any OTHER ticket's read-modify-write of "the whole file"; the fix was an optimistic-concurrency digest bolted onto every verb, one at a time, because there is no per-ticket unit of write to lock |
| T-1090 id collision | next-id allocation is a computation over the WHOLE ledger (`_next_ticket_id`), so two concurrent allocators racing the same whole-file view compute the same id; a per-file store still needs a shared id counter, but it is the ONE remaining shared resource, not every field of every ticket |
| T-1115/1126/1127/1128 draft deaths (section 10b) | the documented recovery recipe for "finalize the ledger before reporting" is "restore main's whole tickets.md over yours, then replay your own change" -- this WIPES any draft ticket filed in the interim because the draft lived in the SAME file as everything else being restored |
| T-1054 DirtyMain | `frob ticket start`'s write and its commit are two different steps against the same monofile; a crash/short-circuit between them leaves root permanently dirty and blocks every OTHER ticket's land, because land also touches the same file |
| T-0933 / T-0982 lock starvation/deadlocks | not literally about the monofile, but the SAME shape: a single shared `.frob/derived.lock`-class resource with reentrancy tracked by a process-local dict keyed on a spelling-sensitive path. Ledger v2 must not reintroduce a single shared write-lock for the whole ticket set; per-ticket-file locking (below) generalizes the fix these two tickets already proved out for the derived-state lock |

The common fix across all seven: give each ticket its own file. A git
merge, a `git mv`, a `flock` on one path, a `git log --follow` -- all of
these are things git and the filesystem already do correctly and for
free, once the unit of storage matches the unit of concurrency (one
ticket). Every bespoke mechanism above (splice_ledger, digest guards,
archive-specific splice, prose-reference rewriting, sibling Done-report
preservation) exists ONLY because the monofile forced N tickets to share
one diff hunk space. None of it is required once tickets are disjoint
files.

## 1. File-per-ticket layout

```
tickets/
  T-0042/
    ticket.md              # frontmatter + body (the "block")
    done-report.md         # present once state reaches done (or dropped-with-report)
    attachments/
      01-mockup.png
  T-0577/
    ticket.md
    done-report.md
  archive/
    T-0001/
      ticket.md
      done-report.md
_index.json                 # derived, gitignored -- NOT the tracked truth (section 6)
```

- `tickets/T-####/ticket.md`: YAML frontmatter (same schema `Ticket`
  already validates today: id, title, state, kind, origin, created,
  blocked_by, parent, scope, acceptance, ...) + the free-text
  description/plan body. Same shape a dir-mode ticket file has TODAY
  (`_serialize_ticket`/`_parse_ticket_file` in `_store.py` already do
  exactly this per-file frontmatter+body split for legacy dir mode) --
  ledger v2 is not a new serialization format, it is making the ALREADY
  -existing per-file format the only format, one level deeper (one
  subdirectory per ticket instead of one flat file per ticket) so
  attachments and the done report have an obvious home next to it
  instead of a side-channel (`tickets/attachments/<id>/` today).
- `done-report.md`: split OUT of the ticket body into its own file.
  Today's single ledger conflates "the ticket's own description/plan"
  (written once, rarely touched again) with "the Done report" (written
  once, at close, by a DIFFERENT actor in a DIFFERENT phase of the
  workflow) inside one YAML+body blob -- every parse of `_reporting.py`'s
  Done-report section is a regex carve-out of part of the SAME file two
  other pieces of code are also mutating (evidence recording, scope
  changes). Splitting it into its own file makes "write the Done report"
  and "record evidence" and "change scope" three DIFFERENT files' worth
  of git object, hence three independently mergeable, independently
  lockable writes instead of three regex-scoped edits into one blob.
- `archive/T-####/`: archiving becomes `git mv tickets/T-0001
  tickets/archive/T-0001` (see section 4.3) -- no rewrite of file
  contents at all, so there is nothing left to clobber (T-0959 becomes
  structurally impossible, not merely guarded).
- Directory name IS the id (`tickets/T-0042/`, not
  `tickets/T-0042-slug/`) -- today's dir-mode legacy filename embeds the
  slugified title (`_dir_path_for`), which means a title edit renames the
  file, which is itself a needless diff/rename hazard on every retitle.
  Ledger v2 drops the slug from the path entirely; the title lives only
  in frontmatter. (A slug MAY still appear in `ticket.md`'s frontmatter
  for human grep-by-topic convenience, just never in the path.)

### 1.1 Draft tickets

A draft (`T-draft-<hex>`, filed by a worktree agent before land assigns
a real id) is `tickets/T-draft-<hex>/ticket.md` -- an ordinary ticket
directory using the draft id as its directory name. No special-casing:
the same `Ticket` model, same file layout, same everything, distinguished
only by the id's own pattern (already true today).

## 2. Draft lifecycle without splice restores

Today's problem (section 10b of the playbook, the "restore recipe"): to
avoid a stale-snapshot revert of siblings' ledger state at report time,
an agent must `git checkout main -- tickets.md` (wipe the WHOLE file back
to main's copy) then replay only their own operations through the CLI.
Any draft ticket filed into the worktree's copy BEFORE that restore is
annihilated, because the restore does not know "keep this one new
section" -- it operates on the file as an indivisible unit.

Under ledger v2, a draft is `tickets/T-draft-<hex>/ticket.md`, a file
that exists ONLY in the worktree branch until it is added and committed.
There is no monofile to "restore to main's copy" -- restoring "the
ledger" is no longer an operation that touches the draft's file at all,
because the draft's file is a disjoint path main's copy never had an
opinion about. The equivalent of today's section 10b recipe becomes:

1. Nothing to restore. Each OTHER ticket's directory is untouched by
   your branch unless you specifically edited it (you didn't -- scope
   discipline already forbids that). `git diff main --stat` naturally
   shows only YOUR ticket's directory (plus your draft's, if any) --
   this is what git already gives you for free from disjoint paths, with
   zero bespoke code.
2. Write the Done report: `frob ticket done-report T-XXXX` writes
   `tickets/T-XXXX/done-report.md` -- one file, one ticket, one writer.
   No other ticket's file is touched, so there is no sibling-preservation
   logic to write (T-0577 items 1-2 above, T-1036, and the whole
   "newest-wins per-id merge" family in `_land_merge.py` become dead
   code -- see section 5).
3. Land renumbers the draft directory
   (`tickets/T-draft-<hex>/` -> `tickets/T-0999/`, a `git mv`) and
   rewrites references (section 4.1) -- but there is no "restore step"
   that could eat it, because nothing ever un-tracks a draft's own file
   to begin with.

This makes the TICK002 (draft cited, never lands) and TICK006 (draft
cited by final id that turns out wrong or dead) classes described in the
epic's acceptance criteria either impossible or mechanically repairable:

- **TICK002 (phantom draft citation)**: a draft directory that never
  gets committed simply never exists in git history; nothing else was
  ever at risk of being reverted alongside it, because there was never
  a "restore the shared file" step that could take collateral damage.
  A Done report that cites an uncommitted draft is caught the same way
  it is today (grep for the id, confirm it resolves) -- unchanged, but
  now with zero risk of the reverse failure (an innocent sibling being
  wiped by the recovery for a phantom draft).
- **TICK006 (draft renumbered to a real id that then goes stale in
  prose elsewhere)**: T-1125's engine (mapping-based whole-word
  regex rewrite of ticket-id citations, `_rewrite_body_prose_references`)
  is EXACTLY the mechanism ledger v2's renumber needs too (section 4.1)
  -- it already operates per-ticket-body, which is now literally
  per-FILE. T-1125 is explicitly kept as pre-migration value (per the
  epic body) and its rewrite core is reused verbatim, just re-pointed at
  "grep every `tickets/*/*.md` file for the old id, rewrite matches" (a
  glob + regex pass) instead of "scan one ledger's rendered text."
  Because renumber-then-rewrite is now a single small commit touching
  only the renamed directory plus whichever OTHER files actually cited
  the old id (each its own git object), the failure mode "prose
  reference silently goes stale" shrinks to "did the grep miss a file",
  auto-repairable by a `frob doctor` sweep (section 6) that finds any
  `T-draft-` or dead `T-####` token anywhere under `tickets/` and
  offers the exact rewrite, rather than a human/coordinator hand-fixing
  N sites after the fact (the T-0668 8-site incident).

## 3. Lock model

Today: one `ledger_lock(root)` (`.frob/tickets.lock`, `_lock_path` in
`_store.py`) serializes EVERY ticket-mutating verb against EVERY OTHER
ticket-mutating verb, repo-wide, regardless of which ticket(s) they
touch -- because the unit of write is "the whole file", the unit of lock
had to be "the whole file" too. This is the direct ancestor of the T-0933
/ T-0982 lock-starvation shape (a single shared resource, contended by
everything, guarded by a reentrancy registry that has already needed two
separate bug fixes to key correctly).

Ledger v2 replaces this with two independent lock tiers:

1. **Per-ticket file lock**: `tickets/T-####/.lock` (or an flock directly
   on `ticket.md`), held only while writing that ONE ticket's files
   (`ticket.md`, `done-report.md`, its `attachments/`). Two agents
   working DIFFERENT tickets never contend AT ALL -- not "contend
   briefly then proceed", literally never touch the same lock path. This
   is the direct fix for the T-0933/T-0982 lesson generalized: the
   reentrancy-registry class of bug exists only when a shared resource is
   contended by unrelated work; per-ticket locks remove the shared
   resource for the 95% case (any operation that touches exactly one
   ticket: start, scope, evidence, done-report, close).
2. **Allocator lock**: a single `.frob/tickets/_next-id.lock` (or reuse
   of a small counter file, `tickets/_counter`) guards ONLY next-id
   computation (`new_ticket`, `finalize_draft`'s renumber-to-real-id
   step) -- the one remaining genuinely shared resource (T-1090's root
   cause: allocation is inherently a global sequence, no per-ticket file
   split can avoid that). This lock is held for microseconds (read an
   integer, increment, write it back) unlike today's `ledger_lock`,
   which is held across an entire read-render-reparse-write cycle over
   thousands of lines. Contention window shrinks from "the size of the
   whole ledger operation" to "the size of one integer increment" --
   directly addressing the T-1090 incident's actual race window, not
   just moving where the race can happen.

Renumber/archive/land operations that touch MULTIPLE ticket directories
in one transaction (e.g. finalizing three drafts from one land) acquire
the per-ticket locks for all of them in a fixed order (sorted by id) to
avoid a lock-ordering deadlock -- the one new discipline this model
requires, tested explicitly (section 7).

**Implementation status (T-1253):** both primitives described above ship
in `src/frob/tickets/_store.py` as `ticket_lock(root, ticket_id)` and
`allocator_lock(root)`, built on the same `flock`-plus-thread-local-
reentrancy shape as the existing `ledger_lock`/`derived_state_lock`
primitives. They compose ALONGSIDE `ledger_lock` during the compatibility
window (section 7) -- no v1 call site has been switched over yet; that is
the store-backend ticket's job (T-1254+). Verified with real
concurrent-thread tests (two different ticket ids never block each
other; the same id from two threads serializes; the allocator lock
serializes a read-increment-write id-allocation race; both primitives are
same-thread reentrant) -- see `tests/unit/test_process_lock.py`'s
`TestTicketLock`/`TestAllocatorLock`.

## 4. Cross-ticket operations

### 4.1 Renumber, with reference rewrite

`renumber(old_id, new_id, root)`:

1. Acquire per-ticket locks for `old_id` and (if it exists) `new_id`, in
   sorted order.
2. `git mv tickets/<old_id> tickets/<new_id>` (or archive/<old_id> if
   archived).
3. Rewrite `id:` in the moved `ticket.md` frontmatter.
4. Glob every `tickets/**/*.md` (plus `docs/**` registry yaml, per the
   T-1125 precedent) for whole-word occurrences of `old_id` and rewrite
   to `new_id` -- reusing `_rewrite_body_prose_references`'s matching
   core verbatim, just re-pointed at a multi-file glob instead of one
   ledger's rendered text. Each touched file is its own small commit
   hunk; `git diff --stat` for a renumber now literally enumerates every
   site that changed, which is the auto-repair surface `frob doctor`
   needs (section 6).
5. Release locks.

Because step 4 touches N independent files, a partial failure (crash
mid-rewrite) leaves a subset of files still citing the old id -- this is
now a SILENT-BUT-DETECTABLE state (`frob doctor` greps for dangling
`T-####`/`T-draft-` tokens, unlike today where a partial monofile write
was invisible until TICK006 fired downstream), not a silent corruption of
unrelated tickets' state.

### 4.2 Doable ordering

`frob ticket doable` today loads the WHOLE ledger to compute blockers/
scope-lease conflicts (`load_all`/`load_active`). Under ledger v2 it
globs `tickets/*/ticket.md` (excluding `archive/`), parses each
independently, and builds the same in-memory blocker graph -- I/O
pattern changes (many small reads instead of one big read) but the
algorithm is unchanged. This is the ONE place where a plain glob is
measurably slower than a monofile read for a very large ticket count;
section 6's derived index cache exists specifically to keep `doable`/
`list` fast without reintroducing a shared mutable source of truth (the
cache is rebuildable from the files at any time, never authoritative).

### 4.3 Archive as `git mv`

`frob ticket archive` today rewrites TWO monofiles (delete N sections
from `tickets.md`, append them to `tickets-archive.md`) -- exactly the
operation T-0959 corrupted, because it is a whole-file rewrite of both
sides at once. Under ledger v2: `git mv tickets/T-0001 tickets/archive/T-0001`
per ticket being archived. No file's CONTENT changes, only its path.
There is no "clobber the destination file" failure mode left, because
there is no destination FILE being rewritten -- only a rename, which git
handles atomically per path with zero collision surface across different
ids.

### 4.4 Flow / velocity mining

Because every state transition is a real, timestamped git commit against
a SPECIFIC ticket's own file (not a line-range edit inside a monofile
whose blame is muddied by every OTHER ticket's concurrent edits sharing
the same lines' surrounding context), `git log --follow --format=... --
tickets/T-0042/ticket.md` gives a clean per-ticket history: queued ->
planned -> in-progress -> done, each transition its own commit, with an
accurate timestamp and author. A `frob ticket stats`/flow-mining command
becomes `git log` across `tickets/*/ticket.md` grouped by state-transition
diff hunks (frontmatter `state:` line changed from X to Y) -- cycle time,
throughput, WIP-by-state, all derivable from git history alone, no
separate event log needed. Today this is not reliably possible: a
monofile's line-level git blame conflates unrelated tickets' edits on
adjacent lines, and the splice/merge-driver rewriting of large chunks at
once (T-0577, T-1036) further destroys the per-ticket commit history's
fidelity.

## 5. Merge story: the frob-ledger driver retired

Today's `merge.frob-ledger` git merge driver (`frob ticket merge-driver
%O %A %B`, `docs/modules/tickets.md`'s "git merge driver" section) exists
ONLY because `tickets.md` is one file two branches can both modify in
incompatible ways that git's own line-level 3-way merge cannot safely
resolve (two tickets' YAML blocks sitting on adjacent lines look like an
ordinary text conflict to git, but are actually two INDEPENDENT edits
that should both survive). `splice_ledger`'s whole job is being a
smarter, ticket-aware substitute for git's own merge algorithm.

Under ledger v2, two branches editing DIFFERENT tickets touch DIFFERENT
files (`tickets/T-0042/ticket.md` vs `tickets/T-0099/ticket.md`) --
git's own merge has ZERO conflict to resolve; this is the single most
common case (disjoint scope, the norm this repo already enforces via
ticket `scope` globs) and it now needs no custom driver at all, no
digest guard, no splice function. The custom merge driver is retired
(`.gitattributes`' `tickets.md merge=frob-ledger` line is deleted, no
replacement registered) because there is no longer a monofile path for
it to attach to.

The only genuine same-ticket conflict left (two branches BOTH editing
`tickets/T-0042/ticket.md` -- e.g. two agents racing a scope change on
the same ticket) is now an ORDINARY git conflict on one small file,
resolved the ordinary way (a human/coordinator picks a side or merges by
hand) -- this is rare (scope discipline / lease TTLs already try to
prevent two agents working the same ticket concurrently) and, when it
does happen, is now a normal, comprehensible git conflict instead of a
monofile-wide one requiring `splice_ledger`'s bespoke three-tier
resolution to even present. `_land_merge.py`'s ~1500 lines
(`splice_ledger`, `_merge_ledger_tickets`, `_newer`, archive splice,
out-of-scope conflict auto-resolution, id-integrity guards) and
`_land_merge_zones.py` are retired in the migration (not deleted in this
design phase -- see Migration below); their logic is NOT reimplemented
elsewhere because git's native per-file 3-way merge already does the job
once the unit of storage matches the unit of concurrency.

`frob ticket land`'s own job shrinks correspondingly: no more squash-
and-splice of a monofile (`_squash_and_splice_ledger`), no more archive-
specific splice (T-0959's fix), no more sibling-Done-report preservation
heuristic (T-0577 item 2) -- land becomes closer to "merge this branch's
touched ticket directories into main, commit, done", with git doing the
actual merge work it was always meant to do.

## 6. Greppability

A stated design goal today (`grep ticket:T- tickets.md`) must not
regress. Ledger v2's answers:

- `grep -r "^id: T-0042" tickets/` finds a specific ticket's file
  directly (faster than grepping a monofile once ticket count is large,
  since the grep target is one small file, not the union of everything).
- `grep -rl "T-0042" tickets/` finds every OTHER ticket that references
  T-0042 (blocked_by/parent/prose) -- strictly MORE informative than
  today's monofile grep, which finds the same references but mixed in
  with the referenced ticket's own unrelated neighbors' text.
- `frob ticket list`/`show`/`doable` remain the primary UX (nobody
  should actually hand-grep routinely) -- greppability is a fallback/
  debugging property, not the main interface, same as today.
- A derived, gitignored `.frob/tickets-index.json` (rebuildable any time
  from `tickets/**/ticket.md`, analogous to today's `.frob/` graph cache)
  gives `list`/`doable`/`show` an O(1) lookup instead of a full glob+parse
  on every invocation, WITHOUT becoming a second source of truth --
  exactly the same "derived vs tracked" split `.frob/` already draws for
  the symbol graph. If the index is stale or missing, every command falls
  back to a full glob+parse (slower, always correct), never to stale
  data silently presented as current.

## 7. Reversible migration plan (design for the CHILD ticket, not built here)

Migration is explicitly a SEPARATE child ticket (per the epic body) with
its own compatibility window. This section specifies what that child
must deliver; it does not implement any of it.

1. **Compatibility window**: `_store_mode(root)` (already a three-way
   detector: single-file / legacy-dir / fresh-default) gains a THIRD
   real mode, `"v2"` (file-per-ticket-with-done-report-split), detected
   by `tickets/*/ticket.md` existing. All three modes are read-
   transparently supported for one deprecation cycle (mirrors the
   existing single/dir precedent: `frob ticket migrate` already
   collapses dir -> single today; v2's migrator is the same shape,
   monofile -> v2). `frob check`'s DEPR-class gates get a new rule
   (naming TBD, e.g. `LEDGERV1001`) that WARNS (not errors) on a
   `tickets.md`-mode repo once v2 ships, escalating to error only after
   the compatibility window's announced expiry -- mirrors how
   `DEPR005`/deprecation-expiry gates already work elsewhere in this
   repo (seen firing in T-1036's captured gate output), so this is reuse
   of an existing pattern, not a new gate family.
2. **One-shot, reversible migrator**: `frob ticket migrate --to v2`
   reads today's `tickets.md` + `tickets-archive.md` via the EXISTING
   `_parse_ledger`, writes one `tickets/T-####/ticket.md` (+
   `done-report.md`, carved out of the body's `## Done report` section
   via `_reporting.py`'s existing extraction logic) per ticket, `git mv`
   attachments into each ticket's own `attachments/`, and does NOT delete
   `tickets.md`/`tickets-archive.md` in the same commit -- it leaves them
   as an inert byte-for-byte snapshot until a human confirms the v2 tree
   round-trips cleanly, then a SEPARATE commit deletes the monofiles.
   This makes the cutover a two-commit, `git revert`-able sequence
   rather than one irreversible rewrite.
3. **Golden round-trip test**: migrate a fixture ledger (a checked-in
   `tests/fixtures/tickets/golden-monofile-ledger.md` covering: a
   done ticket with a Done report, a queued ticket with blocked_by, a
   ticket with attachments, an archived ticket, a draft-id ticket) to v2,
   then migrate v2 BACK to a monofile rendering, and assert the
   round-tripped monofile is semantically identical to the original
   (same id set, same field values per ticket, same Done-report text) --
   not necessarily byte-identical (v2's normalized field ordering may
   differ), but parses to an equal `dict[str, Ticket]` plus an equal
   `dict[str, str]` of done-report bodies. This is the reversibility
   guarantee: nothing is lossy in either direction for the length of the
   compatibility window.
4. **Cutover**: after the compatibility window, `frob ticket migrate --to
   v2` becomes the DEFAULT for a fresh repo (mirrors today's "fresh repo
   -> single" default in `_store_mode`), the monofile-mode code path
   (`_render_ledger`, `splice_ledger`, `_land_merge.py`,
   `_land_merge_zones.py`) is deleted (a follow-up ticket, not silently
   folded into the migrator ticket), and `.gitattributes`' merge-driver
   line is removed.
5. **Rollback**: because step 2 keeps the monofiles as an inert snapshot
   through the whole compatibility window, rollback at any point before
   final cutover is `git rm -r tickets/` (the v2 tree) plus restoring
   `tickets.md`/`tickets-archive.md` from the pre-migration commit -- an
   ordinary git revert of the migration commit, not a bespoke un-migrate
   tool.

## 8. What this design does NOT cover (open questions for the migration child)

- Exact final choice of per-ticket lock primitive (flock on `ticket.md`
  itself vs a sibling `.lock` file) -- functionally equivalent, pick
  whichever the migration implementer finds least surprising given
  `frob.process._lock`'s existing primitives.
- Whether `_index.json` is rebuilt incrementally (mtime-watched) or
  wholesale on every command that needs it -- a performance tuning
  question, not a correctness one; either is compatible with this
  design's "derived, never authoritative" constraint.
- Exact `LEDGERV1001`-class gate name and severity schedule for the
  deprecation window -- naming/timing decision for whoever files the
  compatibility-window child ticket, following the existing `DEPR00x`
  precedent already in this codebase.
- Whether attachments move under `tickets/T-####/attachments/` (this
  design's stated default) or stay in a shared `tickets/attachments/<id>/`
  side directory for less migration churn -- a genuine tradeoff (more
  self-contained vs smaller migration diff) left for the migration child
  to decide with fresh eyes on the actual attachment volume at that time.

## See also

- `docs/modules/tickets.md` -- current (v1, monofile) storage model,
  state machine, and the merge-driver section this design retires.
- `docs/guides/agent-playbook.md` sections 1b, 10, 10b -- the exact
  splice/restore recipes this design eliminates the NEED for (kept as
  historical record until the migration child actually ships and those
  sections can be deleted/rewritten).
- `src/frob/tickets/_store.py` -- `_store_mode`, `_dir_path_for`,
  `_parse_ticket_file`, `_serialize_ticket` -- the existing per-file
  serialization primitives ledger v2 generalizes rather than replaces.
- `src/frob/tickets/_leases.py` -- `leases_dir`/`_lease_path`, the
  existing per-ticket-file precedent (one lease file per ticket id
  already, today) this design extends to the ticket's own state.
