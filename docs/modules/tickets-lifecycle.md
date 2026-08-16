# frob.tickets -- lifecycle: filing, review, scope, lease, organization

Part of the `frob.tickets` reference, split out of `docs/modules/tickets.md` by T-1780 so this subject's own lease no longer blocks every other ticket working a different one; see [`docs/modules/tickets.md`](tickets.md#split-files-t-1780) for the full split index.

## Exact-duplicate refusal at filing time (T-1744)

`new_ticket` refuses a ticket whose `title` and `scope` EXACTLY match an
existing, non-`dropped` ticket's -- `TicketError.DuplicateTicket`
(`_new_renumber._find_exact_duplicate`/`_refuse_exact_duplicate`).
Deliberately HIGH-PRECISION only: exact string equality on `title`,
exact set equality on `scope` (order-independent), never a fuzzy/
similarity match -- this repo files near-identical titles for
genuinely distinct follow-ups constantly (a scope-corrected re-file, a
phase-2 continuation), and a fuzzy matcher would refuse legitimate
tickets at creation time, which is far more damaging than letting an
occasional true duplicate through. Measured 2026-08-07: six duplicate
tickets (exact title AND exact scope, including two triplicates)
reached the queue -- 5% phantom backlog -- before being caught and
dropped by hand.

`dropped` tickets are excluded from the match: a ticket dropped as
obsolete/absorbed does not permanently forbid the same title+scope from
being filed again later. An unreadable ledger fails OPEN (returns no
duplicate, never blocks filing) -- the duplicate class this check
exists to catch is strictly worse than an occasional unnoticed one, but
blocking every `frob ticket new` on a read failure would be worse
still.

## Structured review channel (T-0571)

Adversarial review's verdict used to live only in dispatch-chat prose --
invisible to `frob ticket close` and lost the moment the chat scrolled
away. `frob ticket review` records it as first-class, append-only ledger
evidence instead, and `close --strict` can require it before a ticket is
allowed to transition to done.

### CLI usage

```
frob ticket review <id> --verdict approve|reject --reviewer NAME \
    --findings-file PATH [--commit SHA]
```

- `--verdict` -- `approve` or `reject`, no silent third option
  (`ReviewVerdict`, below).
- `--reviewer` -- who performed the review (freeform name/handle).
- `--findings-file PATH` -- the findings summary, read verbatim from a
  file rather than an inline `--findings` flag, per the same
  shell-command-substitution hazard the other `--*-file` flags guard
  against (playbook section 1d); a blank/whitespace-only file is rejected
  (`Err(ReviewFindingsMissing)`) -- a review record with no findings text
  is indistinguishable from one nobody actually read.
- `--commit SHA` -- the commit reviewed; defaults to the current `HEAD`
  under the ticket's root when omitted. Whatever is supplied is normalized
  to its full 40-char SHA via `git rev-parse` before storage
  (`_resolve_review_commit`) -- never stored abbreviated, since an
  abbreviated value could never satisfy `close --strict`'s later
  exact-match comparison. `Err(ReviewCommitUnresolvable)` if it does not
  resolve to a real commit.

Each call appends one `ReviewEntry` to the ticket's `reviews` tuple
(`record_review`); existing entries are never edited or removed, matching
the append-only discipline `ScopeChangeEntry`/`FailureEntry` already use.
A ticket accumulates as many review records as it goes through review
rounds.

### `close --strict` and `require_review_for_close`

`frob ticket close <id> --strict` requires at least one `verdict: approve`
review record naming the CURRENT final commit before it will let the
transition through -- `Err(MissingApprovedReview)` otherwise. A review
against an earlier commit does not count: the code moved since the last
review, so a stale approval is not an approval of what is actually being
closed (`has_approved_review_for_commit`).

`--strict` alone is not enough to gate anything: it only takes effect when
`frob.toml` also sets

```toml
[tickets]
require_review_for_close = true
```

(`load_require_review_for_close`, default `False`). Both must be true --
`--strict` passed on this specific close call AND the repo-wide config
toggle -- for the CLI to compute a non-`None` `reviewed` predicate and
enforce it; this keeps the gate strictly opt-in per repo instead of
surprising a project that has never turned it on.

### `frob ticket reverify <id>` (T-1005)

The missing verb for a post-close send-back: after a `done` ticket
receives new scope/evidence/done-report edits (most commonly a TEST016
mutation-evidence strengthening requested during review), nothing could
previously re-run `close`'s own verification suite against it --
`close` itself refuses a `done -> done` transition (not a legal edge in
`_TRANSITIONS`), and `start`/`sweep` both refuse a `done` ticket outright.
Lands used to proceed on trust in the ORIGINAL close-time recap alone,
even when the ticket's evidence had since changed.

<!-- frob:waive DOC004 reason="illustrative CLI example using placeholder ticket T-0042 and test_foo.py -- neither is a real anchor target" -->
```bash
frob ticket evidence T-0042 tests/test_foo.py::test_stronger  # bind new/strengthened evidence
frob ticket reverify T-0042                                   # re-run close verification, refresh recap
```

`reverify` re-runs the EXACT SAME checks `close` runs at close time, with
**no state transition either way** on success or failure:

- the injected guards `_close_guards_for_ticket` computes for
  `close` (D-02 `covers_scope`, T-0571 `reviewed` when `--strict` +
  `require_review_for_close` are both set, T-0844 `mutation_evidence`,
  T-0417 `evidence_reverified` -- a fresh re-run of the ticket's own
  recorded evidence against the CURRENT tree, and T-1384
  `own_obligations_clean` once the app-layer computation is wired), and
- `reverify_close_guard`, which wraps the identical `_done_transition_guard`
  `transition(..., TicketState.DONE, ...)` calls at close time: structural
  checks (evidence + Done report present, no open descendants, no
  disallowed `cmd:` evidence, T-0572 acceptance binding) plus the two
  ALWAYS-run diff-derived checks (T-0854 live-tracker citation, T-0756
  new-gate-rule acceptance).

`--evidence`/`--evidence-cmd`/`--accepts`/`--strict`/
`--skip-mutation-evidence` behave identically to `close`'s own flags of the
same name (shared dest names, shared `_apply_close_time_evidence`).

**On a failing guard**: exits 1 with the same remedy text `close` itself
would show (`_close_failure_hint`, now under the `"reverify"` verb) --
e.g. a TEST016 finding that still does not kill a mutant, or an evidence
id that no longer passes. The ticket's state AND recap are left
untouched; nothing is silently downgraded.

**On a fully passing reverify**: the recap is refreshed. `recover_done_
report_why` recovers the ticket's existing Done-report narrative verbatim
from the ledger (the mechanical inverse of `compose_done_report`'s own
narrative half -- the operator never retypes it), and a fresh
`set_done_report` call (the same T-0754 claims-capture callables `frob
ticket done-report` already supplies) rewrites the Changed/Evidence/
Captured-claims sections against the CURRENT tree. `reverify` never calls
`transition` -- the ticket's `state:` field is untouched either way.

### `ReviewEntry` evidence shape

```python
class ReviewVerdict(StrEnum):
    APPROVE = "approve"; REJECT = "reject"

class ReviewEntry(BaseModel):
    verdict: ReviewVerdict
    reviewer: str
    findings: str
    commit: str              # full 40-char SHA, never abbreviated
    at: date

class Ticket(BaseModel):
    ...
    reviews: tuple[ReviewEntry, ...] = ()   # append-only
```

`Ticket.model_config = ConfigDict(frozen=True, extra="allow")`: the
`extra="allow"` relaxation is what let an OLDER frob binary (one that
predates `reviews` entirely) load a ledger a NEWER binary already wrote
`reviews` entries into, without hard-failing `MalformedFrontmatter` --
see `## Data models` below for the forward-compatibility rationale in
full. `TicketError.ReviewFindingsMissing`,
`TicketError.ReviewCommitUnresolvable`, and
`TicketError.MissingApprovedReview` are the three review-specific error
variants (`## Error types` below).

## Scope-lease model (T-0453)

`frob ticket doable` does not just filter on blockers -- by default it also
excludes any queued/planned candidate whose declared `scope` overlaps an
IN-PROGRESS ticket's active scope-LEASE, so two agents dispatched straight
off `doable` can never collide on the same files. This replaces hand-
maintained collision blocklists a coordinator would otherwise have to build
and update on every dispatch.

<!-- frob:invariant INV-024 -->

- **Overlap** is a sound glob-set intersection (`scope_overlap_globs`,
  `_globs_intersect`): two globs collide if some concrete path could match
  both, via the standard two-pattern wildcard DP (`'*'` any-length,
  `'?'`/a bracket class any-single-char), NOT a literal-prefix heuristic.
  `tickets.md` is the ONLY path ignored in the overlap check (every ticket
  implicitly leases it, and the `frob ticket merge-driver` already resolves
  it) -- `tests/**`/`docs/` are deliberately NOT special-cased out; doing so
  would mask real per-file collisions under those trees.
- **`frob ticket doable`** (default): lease-filtered. **`--ignore-lease`**:
  the raw blocker-only list, no collision filtering. **`--show-blocked`**:
  explains every hidden candidate as `held: scope '<glob>' leased by
  in-progress T-0xxx`.
- **Large-glob warning**: a ticket whose scope contains a chronically
  over-broad glob (`tests/**`, `src/frob/**`, `docs/`, `docs/**`, ...) or one
  matching more real files than `[tickets] large_glob_max_files` in
  `frob.toml` (default 25) gets a `large_glob_warnings` nudge. This is a
  NUDGE, not a hard gate: it fixes over-hiding at the scope-DECLARATION
  level instead of ignoring broad directories in the overlap check itself.
  T-0714: the per-nudge detail no longer prints alongside `frob ticket
  doable` output (that flooded every queue query with a repeated
  `WARNING:` wall) -- `doable` now shows one summary count line only
  (`frob.app.ticket_runner._render_scope_breadth_summary`), and `frob
  check`'s TICK009 gate (`docs/modules/gates.md#tick009tick010-t-0714`)
  reports each nudge once, with remediation, alongside `frob check`'s
  other findings. The same T-0714 relocation applies to stale
  cross-worktree leases -- TICK010 reports those.
- **Over-broad-lease demotion**: when a repo root is available (the CLI
  path always has one), a HOLDER's over-broad scope entries -- the exact
  same breadth test the warning uses -- are dropped before the overlap
  check, so one repo-wide in-progress lease (e.g. a `src/frob/**` coverage
  burn-down ticket) demotes to warn-only instead of zeroing out `doable`
  for every other ticket in the repo. A PRECISE entry on the same holder
  (e.g. `src/frob/gates/`) still hard-blocks a real collision under it.
  Callers with no repo root (`root=None`) get the strict, undemoted check.
- **In-flight/dispatchable split and staleness alarm (T-0752)**: the
  default `frob ticket doable` render additionally shows each row's
  `priority=<level>`, splits any row `has_live_lease` finds a live lease
  against (the T-0716 `display_state` overlay, reused verbatim -- a
  worktree already started it even though the local ledger still shows
  `queued`/`planned`) into a separate in-flight section below the truly-
  dispatchable rows, and marks a CRITICAL/HIGH row `undispatched_stale`
  finds sitting dispatchable past its threshold with an `UNDISPATCHED`
  alarm, sorted to the top of the dispatchable section. The per-priority
  threshold, in hours, is `[tickets] dispatch_stale_critical_hours`
  (default `4`) / `dispatch_stale_high_hours` (default `24`) in
  `frob.toml`, same fail-open-to-defaults shape as `large_glob_max_files`
  above. Staleness is measured from `Ticket.created` (`dispatch_stale_hours`)
  -- the ticket model carries no per-transition timestamp yet, so "last
  state change" degrades to "filing" and the measurement is day-granular,
  not true wall-clock hours. `--json`/`--ignore-lease` output stays the
  raw, undecorated `doable()` result -- the split and alarm are a display-
  layer concern only.

## Cross-worktree lease side-channel (T-0473)

The scope-lease model above is derived purely from the LOCAL `tickets.md`'s
`IN_PROGRESS` rows -- fine for one checkout, but a real dispatch session
runs each agent in its OWN isolated git worktree, each with its own copy of
`tickets.md`. A lease taken by `frob ticket start` in worktree A never
reaches worktree B's ledger until one lands/merges into the other, so
`doable`'s collision filter was structurally inert across worktrees before
T-0473 -- two agents in separate worktrees could be handed overlapping
scope with neither's `doable` ever seeing the other's hold.

`frob.tickets._leases` fixes this with a side channel under the git
**common** directory (`git rev-parse --git-common-dir`), which every
linked worktree of one repository resolves to the SAME absolute path
(unlike `root / ".git"`, a per-worktree pointer file for a linked
worktree). `<common-dir>/frob-leases/<ticket-id>.json` holds one
`LeaseRecord` (scope, worktree path, branch, timestamp) per currently
`IN_PROGRESS` ticket -- `frob.tickets.transition` writes it on entering
`IN_PROGRESS` and removes it on leaving, and `mutate_scope` re-writes it
when an in-progress ticket's scope changes. The local `tickets.md`
`state:`/`scope:` fields remain the sole source of truth for anything
this worktree already knows about; the lease record is a DERIVED mirror
of that, kept in sync by `mutate_scope`, never the other way around.

**T-1993: the re-write is a delta-reconciliation against the lease's own
prior state, not a wholesale overwrite from the caller's local ledger
snapshot.** Before T-1993, `mutate_scope` re-wrote the lease as the
calling worktree's OWN freshly-computed `updated_scope` -- which is only
correct when that worktree's local ledger is fully up to date. A worktree
that never merged a sibling's narrowing commit still holds the OLD,
broader scope in its own checkout; blindly re-recording it clobbered a
narrower lease another, more-current worktree had already written,
purely by writing last. `_lease_scope_to_record` (`src/frob/tickets/
_scope.py`) fixes this: it re-applies the SAME `add`/`remove` delta
`mutate_scope` (or `demote_to_evidence_only`) just validated, but onto
whatever scope is CURRENTLY recorded in the shared lease file
(`read_all_leases`), not onto the calling worktree's possibly-stale
snapshot. A fully up-to-date worktree computes the identical result
either way; a stale worktree's legitimate delta now lands on top of the
lease's true current state instead of reverting it. Falls back to the
pre-T-1993 wholesale-overwrite behavior when no lease is recorded yet for
the ticket, or when the lease side channel cannot be read at all
(best-effort, same posture as `record_lease` itself). This does not make
the lease authoritative over the ledger -- the ledger write already
happened and is unaffected; only the derived side-channel mirror is
reconciled differently.

`leased_by` (and therefore `doable`) now unions the local ledger's own
`IN_PROGRESS` rows with every OTHER worktree's recorded lease
(`read_all_leases`), local always winning on an id collision. A lease
whose recorded worktree path no longer exists on disk (a crashed or
abandoned agent checkout, never cleaned up) is treated as stale and
skipped by `read_all_leases` -- a structural, cheap liveness check (path
existence) that keeps a dead worktree's forgotten lease from wedging
`doable` for everyone else forever; the fuller two-way reconciliation
(dead in-progress ticket -> requeue, live worktree with no in-progress
ticket -> flag/clean) is T-0476's job, not this one's.

**Attribution provenance, and a supported release path for an orphaned
lease (T-1743).** `frob ticket doable --show-blocked`'s per-ticket
explanation used to name only a bare holder id (`leased by in-progress
T-####`), with no way to tell whether that id came from a cross-worktree
lease file (`read_all_leases`) or from the LOCAL ledger's own
`IN_PROGRESS` row -- and a local row can be stale relative to `main` for
as long as this worktree has not merged. A real incident: `--show-blocked`
consistently named a ticket whose OWN declared scope (`frob ticket show`)
could not have produced the collision at all, while the actual holder was
a mega-glob (`docs/**`) lease belonging to a worktree from an earlier
session -- two agents spent real time chasing the wrongly-implicated id.
`lease_holder_worktree(root, ticket_id)` names the cross-worktree lease
file's own `worktree` field for a holder id, or returns `None` if no such
file exists (meaning the attribution's source was the local ledger row,
not a lease file) -- `--show-blocked`'s rendering now appends this
provenance to every reason it prints, e.g. `... leased by in-progress
T-1629 (/path/to/worktree)` vs. `... (local ledger row, no lease file)`,
using the exact same `(holder_id, glob)` pairs `doable_blocked` already
computed, never re-derived.

Before T-1743 there was also no supported way to clear an orphaned
lease: `frob ticket scope <id> --remove <glob>` refuses
(`ScopeRemoveNotDeclared`) unless the glob is literally in THAT ticket's
own declared scope, so it structurally cannot reach a lease whose real
scope does not match what a caller expected -- the only prior recourse
was deleting the holding git worktree by hand, an operation no
worktree-isolated agent can perform. `force_release_lease(root,
ticket_id)` (`frob.tickets._leases`) removes a ticket's lease FILE
directly, independent of any ticket's declared scope, logs a WARNING
naming exactly what was released, and is idempotent (`Ok(False)` if there
was nothing to release). It deliberately does not transition the
ticket's own ledger state -- requeuing an abandoned ticket is a separate,
deliberate step (`frob ticket reconcile` / `frob ticket requeue <id>`).
As of T-1743 this is a Python-API-level release path only; wiring it into
a first-class `frob ticket lease release <id>` CLI verb is out of this
ticket's scope (it needs `src/frob/_cli_parsers/**` and
`src/frob/app/config.py`, neither of which T-1743 declared) and is
tracked as a follow-up.

**Lease migration on renumber (T-1173).** The lease file is keyed by
ticket id, but a `T-draft-XXXXXXXX` provisional id (T-0162) is exactly the
kind of ticket most likely to hold a live lease at rename time -- a draft
filed and started `IN_PROGRESS` in one worktree, then renumbered to its
final `T-####` id by `frob ticket land` running in that SAME worktree.
`frob.tickets._new_renumber.renumber_one` calls
`frob.tickets._leases.rename_lease(root, old_id, new_id)` right after its
ledger/code-reference rewrite persists (never before -- a persist failure
must never leave a lease renamed to an id the ledger itself never
actually claimed), which migrates `<old_id>.json` to `<new_id>.json`
under the shared leases directory AND rewrites the record's own
`ticket_id` field to match -- a bare filesystem rename alone would leave
the stale id embedded in the JSON body, which `read_all_leases` trusts
over the path it parsed the record from. Before this, a worktree that
held the draft's lease looked lease-less the instant its own draft
renumbered, and a subsequent `frob check --ticket <final-id>` in that
same worktree spuriously reported no recorded lease at all, even though
the worktree genuinely still held the ticket. A missing old-id lease
file (the common case: a ticket that never entered `IN_PROGRESS`, or
whose lease was already released before the rename ran) is not an error,
mirroring `release_lease`'s same tolerance.

<!-- frob:describes src/frob/tickets/_scope.py::_scope_add_live_lease_conflict -->
**`scope --add` now checks the LIVE lease too, not just the local queue
(T-1868).** `_scope_add_conflicts`'s pre-existing check
(`_scope_add_queue_conflict`) only ever consulted `queue` -- this
worktree's own local ticket ledger, which reflects a sibling worktree's
`start` only after THIS worktree merges that commit in. Two tickets in
different, unconverged worktrees could hold the identical path
simultaneously with neither's `scope --add` ever refusing (confirmed
directly: T-1863/T-1822 both held `design/frob.strata` 36 seconds apart,
neither refused). `_scope_add_live_lease_conflict` closes this the same
way `frob ticket start`'s own foreign-lease refusal already does: it
reads `read_all_leases` (this section's own side channel) instead of the
local queue, so a sibling's lease is visible the instant it is recorded,
with no merge required. TTL-expired leases are excluded, and T-1356's
same-worktree exemption plus T-0561's new-file carve-out both apply
identically to this check -- a live-lease conflict is never STRICTER
than the existing queue-based one for the same holder, only able to
catch a real conflict the queue-based check's merge-dependent staleness
missed.

<!-- frob:describes src/frob/tickets/_leases.py::same_worktree_lease -->
**`doable --show-blocked` no longer reports a same-worktree lease as a
blocker (T-1883).** `frob.tickets._doable.leased_by` (which both `doable`'s
default collision filter and `doable --show-blocked`'s per-ticket
explanation call) used to compare every candidate against every OTHER
in-progress ticket's lease with no same-worktree exemption at all --
`_scope.py`'s `--add` collision check already had T-1356's same-worktree
exemption, but `_doable.py`'s independent query did not, so the two
answered "does this lease conflict?" differently for the identical shape.
This mattered in practice: the recommended grouped-dispatch workflow
(several related tickets, one worktree, one agent, all legitimately
declaring the same shared doc in scope) reliably produced a fully
self-blocked group in `doable --show-blocked`, since a worktree cannot
conflict with itself. `frob.tickets._leases.same_worktree_lease(root,
requesting_id, holder_id)` is now the ONE shared predicate both
`_scope.py`'s `--add` check and `_doable.py`'s `leased_by` call -- `leased_by`
skips any holder this predicate matches before computing a collision, so a
same-worktree lease can never appear as a blocker again, in either
call site, without both changing together.

<!-- frob:describes src/frob/tickets/_scope.py::scope_lease_conflict -->
<!-- frob:describes src/frob/app/ticket_runner/_lifecycle.py::_refuse_on_scope_lease_collision -->
**`frob ticket start` now refuses a scope collision present at GRANT time,
not just one widened afterward via `--add` (T-1880).** T-1868 closed the
door where a ticket's `scope --add` widened its lease into a path another
worktree's live lease already covered. A different door stayed open: a
ticket that simply declares a colliding path in its ORIGINAL FILED scope
and runs `frob ticket start` -- `start`'s guard chain (`_refuse_if_
terminal`, `_refuse_if_foreign_live_lease`, T-1866's `_refuse_over_broad_
scope_on_start`) checked whether the ticket itself already held a lease
elsewhere and whether its own scope was over-broad, but never whether its
scope OVERLAPPED another already-in-progress ticket's live lease. Confirmed
live on this repo's own main: T-1851 declared `src/frob/app/config.py` in
its filed scope and started AFTER T-1870 already held a live lease on the
same path, and nothing refused it.

`frob.tickets._scope.scope_lease_conflict(ticket_id, scope, queue,
own_scope=(), *, root=None)` is the shared entrypoint: given a scope
(a tuple of globs) and the local ledger's `queue`, it returns the first
`(holding_ticket_id, holder_glob)` collision against another in-progress
ticket's lease -- queue-based, or (when `root` is given) also the LIVE
cross-worktree lease side-channel (`_scope_add_conflicts`'s existing
T-0453/T-0561/T-1868 mechanism, unchanged). `mutate_scope`'s `--add`
validation and `_lifecycle.py`'s new `_refuse_on_scope_lease_collision`
(called from `_start`, right after T-1866's over-broad-scope refusal and
before the ticket transitions to `IN_PROGRESS`) both call this ONE
function -- `--add` passes the ticket's own pre-mutation scope as
`own_scope` (T-0485's already-grandfathered-subset exemption still
applies there), `start` passes `own_scope=()` (a grant-time check has no
pre-existing granted subset to exempt against). One shared predicate
means the two call sites cannot answer "does this scope collide?"
differently again, the same discipline T-1883's `same_worktree_lease`
extraction already applied to the doable/`--add` pairing above.

<!-- frob:describes src/frob/app/ticket_runner/_query.py::_stale_lease_reasons -->
<!-- frob:describes src/frob/app/ticket_runner/_query.py::_render_doable_in_flight -->
**`frob ticket doable` now FLAGS a lease that looks dead, in its own
in-flight section (T-1876).** Everything above this paragraph already
built the pieces this closes: `is_lease_ttl_expired` (T-0782), the
worktree-liveness probe (`scan_for_live_worktree_process`, T-1739), and
`lease_staleness_reason`/`orphaned_leases` (T-1789/T-1806), which unify
both into the three-shape "path-gone / ticket-gone / holder-dead"
verdict `frob worktree release-lease` already acts on. What was still
missing: `doable`'s own "In-flight (leased, already being worked)"
section rendered a dead agent's lease identically to a live one, with no
signal at the point a coordinator actually decides what to dispatch --
measured for real, 2026-08-08: a lease recorded hours after its own
worktree's last commit blocked five other tickets the entire time, and
`doable` never said so.

`_stale_lease_reasons(root)` (`frob.app.ticket_runner._query`) builds a
`ticket_id -> reason` map from `orphaned_leases(root)` and
`lease_staleness_reason`, reusing both wholesale rather than inventing a
fourth liveness signal (T-1876's own explicit design constraint: a
liveness check that is too eager would let two worktrees mutate the same
scope at once, T-1868's exact failure class). `_render_doable_in_flight`
prints an extra warning line under any in-flight row this map covers,
naming the reason and the `frob worktree release-lease TICKET-ID`
recovery command -- and does nothing else: the row still appears
in-flight, `doable`'s own dispatchable/blocked partition is completely
unchanged, and no lease is ever released automatically. FLAG, never
auto-release, is the deliberate, conservative posture T-1876 calls for;
reclamation stays an explicit human/coordinator decision via the
existing verb.

## Start-transition auto-commit (T-1054)

`frob.tickets.transition` writes `tickets.md` straight to `root`'s working
tree but never commits it -- `frob ticket start` used to return with `root`
DIRTY (an uncommitted `queued -> in-progress` line) the instant it
succeeded. Because `frob ticket land` refuses with `DirtyMain` on ANY
uncommitted change in the checkout it lands against, the very next land --
by any agent, often in a different worktree entirely -- refused until a
human noticed the stray line and hand-committed it (the recurring
2026-07-27 incident this fixes; a coordinator hand-committing
`chore(tickets): record T-1047 start transition` was the last time this
had to be done manually).

`frob.tickets._leases.commit_start_transition(root, ticket_id)` closes this
the same way `frob.tickets._land_finalize._commit_finalize_writes` already owns
land's own working-tree commits: called from `ticket_runner._start`
immediately after `transition(root, ticket_id, IN_PROGRESS)` succeeds, it

1. No-ops (`Ok(None)`) if `root`'s `tickets.md` is not actually dirty (not
   a git work tree, or nothing to commit) -- never manufactures an empty
   commit.
2. Otherwise stages and commits exactly `tickets.md` with the message
   `chore(tickets): record <ticket_id> start transition`, mirroring the
   coordinator's own hand-written recovery commits' message form.
3. On a commit-step failure (`git add`/`git commit` itself erroring),
   returns `Err(LeaseError.CommitFailed)` and LOGS AN ERROR naming the
   exact recovery command (`git -C <root> add tickets.md && git -C <root>
   commit -m "..."`) -- `ticket_runner._start` treats this as a hard
   `sys.exit(1)`, never a silently-swallowed warning, since a failure here
   IS the DirtyMain-at-next-land bug reproducing itself.

## New/drop/fail auto-commit (T-1130)

Parity with T-1054's start-transition auto-commit above, extended to the
remaining three ledger-writing verbs: `frob ticket new`/`drop`/`fail`
used to leave `tickets.md` dirty the same way `start` did before T-1054
-- "commit before dispatching" was coordinator memory (bit the T-1018
agent once, carried in `docs/guides/agent-playbook.md` as a must-
remember) rather than something the tool itself guaranteed.

`frob.tickets._leases.commit_ticket_ledger_change(root, ticket_id,
message, *, no_commit=False)` generalizes `commit_start_transition`'s own
add-and-commit primitive (both now funnel through the same
`_add_and_commit_tickets_md(root, ticket_id, message)` helper) to an
arbitrary caller-supplied commit message plus an explicit opt-out flag:

1. `no_commit=True` (`frob ticket new/drop/fail --no-commit`) skips
   entirely, no dirtiness check even performed -- for a caller that wants
   to batch several ledger writes into one commit of its own.
2. Otherwise no-ops (`Ok(None)`) if `tickets.md` is not actually dirty,
   same as `commit_start_transition`.
3. Otherwise stages and commits exactly `tickets.md` with `message`.
4. On a commit-step failure, returns `Err(LeaseError.CommitFailed)` and
   logs the exact recovery command -- callers treat this as a hard
   `sys.exit(1)`, the same posture `commit_start_transition`'s callers
   already have.

**T-1432: the commit itself is pathspec-limited (`git commit -m message --
tickets.md`), never a bare `git commit -m message`.** A bare `git commit`
commits the ENTIRE index, not just what this helper staged -- the T-1403
c2fd45da incident: a conflicted `git stash pop` auto-stages every file
that merged cleanly (`docs/guides/agent-playbook.md` section 1b2), and
anything left staged that way rode along into the next `frob ticket
new`/`start`/`drop`/`fail` ledger commit under an unrelated `chore(tickets):
...` message, poisoning `git blame`/bisect archaeology for whatever it
swept in. The pathspec limit (`-- tickets.md`, git's documented way to
commit only a named path regardless of what else is staged) makes this
structurally impossible now: the ledger commit can never contain anything
but `tickets.md`, and anything else pre-staged stays staged, untouched,
exactly as before this helper ran.

Per-verb wiring (`frob.app.ticket_runner._new._new` / `_close_cmd._drop`
/ `_close_cmd._fail`):

- `new` commits LAST, after every other write the command makes
  (`new_ticket`'s own frontmatter block, plus any `--evidence` ids
  applied right after) -- `chore(tickets): file <id> <title>` -- so the
  one commit captures the WHOLE filed block, not a partial commit
  followed by a second separately-dirty write.
- `drop` commits its `## Drop reason` line + DROPPED transition as one
  change -- `chore(tickets): drop <id>`.
- `fail` commits its Failure-log entry (plus any T-1131 requeue
  transition) as one change -- `chore(tickets): <id> fail-logged`.

`start`'s own T-1054 auto-commit is unaffected -- it stays on
`commit_start_transition` (still gated by `warn_if_worktree_stale`, which
`commit_ticket_ledger_change` does NOT run, since a stale-base warning is
specific to the moment a ticket is started, not to every later ledger
write on it). Worktree-side behavior is unchanged either way: both
functions commit under ANY git root they are pointed at, main or
worktree, exactly like `commit_start_transition` already did before this
ticket -- a worktree agent's own eventual close/land commits already
absorb this the same way they always have.

**T-1178: extended to `close`/`evidence`/`done-report`/`requeue`.** The
original filing of this same family (commit 46a115c4) was itself the
2026-07-29 incident T-1179 documents above: a coordinator's `close` wrote
`tickets.md` UNCOMMITTED (`close` was not in T-1130's `new`/`drop`/`fail`
set), a concurrent agent's `land` preflight ran `git reset --hard` in
`root`, and the close silently vanished -- caught only by a doctor
stale-lease scan (the T-0329 epic-close incident this closes, T-0948
lineage). The remaining ledger-writing verbs now call
`commit_ticket_ledger_change` exactly like `new`/`drop`/`fail`, each with
its own `--no-commit` opt-out and commit message
(`frob.app.ticket_runner._close_cmd._close` / `frob.app.ticket_runner.
_verify._evidence` / `_verify._done_report` / `frob.app.ticket_runner.
_lifecycle._requeue`):

- `close` commits LAST, after any `--evidence`/`--evidence-cmd` applied
  at close time plus the DONE transition -- `chore(tickets): close <id>`.
- `evidence` commits its appended evidence id(s)/cmd-evidence entry --
  `chore(tickets): record evidence for <id>`.
- `done-report` commits the composed Done-report section --
  `chore(tickets): <id> Done report`.
- `requeue` commits its QUEUED transition -- `chore(tickets): requeue
  <id>`.

No ledger-writing verb dispatched through the CLI is left able to leave
`tickets.md` dirty by default anymore -- every one of `new`/`start`/
`drop`/`fail`/`close`/`evidence`/`done-report`/`requeue` now auto-commits
(the CLI layer's own atomic-write guarantee; `frob.tickets` library calls
made directly, bypassing the CLI, are unaffected and still leave the
caller responsible for committing, exactly as before).

## Every ledger-writing verb auto-commits uniformly (T-1615)

T-1178's list above was still incomplete: `block`/`scope`/`scope-ack`/
`priority`/`kind`/`component`/`label`/`accept`/`tier`/`attach` each wrote
the ledger directly (`write_ticket`/`_set_ticket_field`/`mutate_scope`/
`mutate_labels`) and left it dirty. Two `frob ticket block` calls back to
back on 2026-08-05 left `tickets.md` uncommitted on `main`; the next
`frob ticket land` from every worktree in the repo correctly refused with
DirtyMain, but the dirt was frob's own doing, silently, on a verb nobody
had reason to think left work behind -- the same incident class T-1130
and T-1178 each closed for a different subset of verbs.

**The fix, deliberately NOT one more per-verb copy-paste.**
`frob.app.ticket_runner._auto_commit_ledger_after_dispatch` wraps the
SINGLE dispatch call site in `run()` (the one place every CLI invocation
already passes through `_ticket_dispatch_table()`), rather than adding a
`commit_ticket_ledger_change` call inside each individual verb handler:
after the dispatched handler returns (success or a verb's own
`sys.exit`), it commits whatever `tickets.md`/`tickets/<id>` residue that
verb's write left dirty for `cfg.ticket_id`, honoring the same
`--no-commit` opt-out. A verb added to the dispatch table LATER is
covered automatically, with nothing new to remember per verb -- the
"verb number twelve" gap this ticket exists to structurally close.
`commit_ticket_ledger_change` itself now WARNS (naming the ticket, root,
and the exact recovery command) whenever `--no-commit` leaves the ledger
dirty, for every verb that reaches it -- a silent opt-out reproduces the
incident with an extra step.

**`archive` is NOT covered by that wrapper** (it operates on no single
`cfg.ticket_id` -- it moves potentially MANY done/dropped tickets from
active into `tickets-archive.md`/`tickets/archive/` in one call) and gets
its own explicit call site instead: `commit_full_ledger_change`
(`frob.tickets._leases`), `commit_ticket_ledger_change`'s twin keyed on
the WHOLE ledger surface (`_full_ledger_pathspecs`) rather than one
ticket's pathspecs, same no-op/warn/commit contract.

**The audit table** (every ledger-writing verb in the real dispatch
table, enumerated programmatically by
`tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable`,
never hand-listed -- a verb the table omits fails
`test_dispatch_table_verbs_are_all_accounted_for` immediately):

| verb | writes the ledger? | commits? | how |
| --- | --- | --- | --- |
| `new` | yes | yes | T-1130, own call site |
| `drop` | yes | yes | T-1130, own call site |
| `fail` | yes | yes | T-1130, own call site |
| `start` | yes | yes | T-1054, own call site |
| `close` | yes | yes | T-1178, own call site |
| `evidence` (plain and `--replace`) | yes | yes | T-1178, own call site (both modes funnel through the same handler) |
| `done-report` | yes | yes | T-1178, own call site |
| `requeue` | yes | yes | T-1178, own call site |
| `block` | yes | **yes (T-1615)** | uniform wrapper |
| `scope` | yes | **yes (T-1615)** | uniform wrapper |
| `scope-ack` | yes | **yes (T-1615)** | uniform wrapper |
| `priority` | yes | **yes (T-1615)** | uniform wrapper |
| `kind` | yes | **yes (T-1615)** | uniform wrapper |
| `component` | yes | **yes (T-1615)** | uniform wrapper |
| `label` | yes | **yes (T-1615)** | uniform wrapper |
| `accept` (append/`--amend`/`--remove`) | yes | **yes (T-1615)** | uniform wrapper |
| `tier` | yes | **yes (T-1615)** | uniform wrapper |
| `attach` | yes | **yes (T-1615)** | uniform wrapper |
| `sprint assign` | yes | **yes (T-1615)** | uniform wrapper |
| `review` | yes | **yes (T-1615)** | uniform wrapper |
| `reverify` | no (re-runs close's guards against an already-done ticket, never calls `transition`) | n/a | n/a |
| `archive` | yes, whole ledger | **yes (T-1615)** | `commit_full_ledger_change`, own call site |
| `migrate` | yes, whole ledger | **deliberately no** | rewrites the storage backend itself (v1->v2); the caller finishes the migration by committing everything as one change |
| `renumber` (both forms) | yes, whole tree | **deliberately no** | rewrites `frob:ticket`/`frob:tests`/... directive references across every tracked file, not just the ledger -- a ledger-only commit here would split one atomic rename into two |
| `promote` | yes, whole tree | **deliberately no** | same reasoning as `renumber` (it IS `renumber_one` under the hood) |
| `land` / `merge-driver` | yes, whole tree | yes, but via its OWN multi-file commit sequence | never through this mechanism -- see `_LEDGER_TRANSACTIONAL_VERBS`'s own docstring |
| `sweep-async` | no (files a NEW bug ticket via `new`, which already commits) | n/a | T-1699 territory (DirtyMain vs. the land lock), not this ticket's |
| `list`/`show`/`doable`/`board`/`epic`/`brief`/`flow`/`sprint show`/`plan`/`work`/`sweep`/`reconcile` | no | n/a | read-only or state-transition-only, no ledger write |

There is no `unblock` verb in the dispatch table to audit.

## Stale-worktree-cut warning (T-1059)

T-1030 root-caused a recurring incident (fa606fe8, b3589c3e): dispatched
worktrees can be cut from a stale base -- the dispatch harness's
`EnterWorktree` tool defaults to branching from `origin/<default-branch>`
rather than local `HEAD`, and this repo's `origin/main` regularly lags
local `main` by dozens to hundreds of commits across a session. The
playbook's warm-up step
(`docs/guides/agent-playbook.md#1-worktree-warm-up-do-this-first-every-time`)
is the manual fix; this is the mechanical detector that catches it at
`frob ticket start` time instead of relying on an agent to remember.

`frob.tickets._leases.warn_if_worktree_stale(root, ticket_id, main_ref=
"main")` runs unconditionally from `commit_start_transition` (before its
own dirty-ledger check), so every `start` measures it regardless of
whether the ledger write needed a commit:

1. `git merge-base HEAD <main_ref>` in `root`.
2. `git rev-list --count <merge-base>..<main_ref>` -- how many commits
   `main_ref`'s tip is ahead of the merge-base, i.e. how far behind `root`'s
   own `HEAD` currently sits.
3. If that count is at or above the `[tickets] stale_worktree_warn_commits`
   threshold (`frob.toml`, default 20), logs a `_log.warning` naming the
   ticket id, the commit count, and the exact playbook anchor to re-read.

Best-effort and non-fatal throughout: any git failure (non-git `root`,
missing `main_ref`, an unparsable count) degrades to a silent no-op, the
same posture `_tickets_md_dirty` already takes for its own optional git
probe -- this is a detector, never a gate, and must never block `start`
itself. `_load_stale_worktree_warn_commits` reads `[tickets]
stale_worktree_warn_commits` via the shared `load_positive_int_config(root,
key, default)` helper (T-1059, DUP001) -- the same degrade-quietly
`frob.toml` reader `_load_large_glob_max_files` (`large_glob_max_files`,
T-0453) now also delegates to, extracted so the absent-file/malformed-
TOML/non-positive-value fallback chain has exactly one home instead of two
95%-identical copies.

## `frob ticket reconcile` (T-0476)

The fuller two-way healing the T-0473 section above defers to. Reuses the
same `frob.tickets._leases` registry (T-0473) to judge two anomaly classes
structurally -- no coordinator polling of output-file mtimes:

1. **Stale hold**: a ticket the checkout's OWN `tickets.md` shows
   `IN_PROGRESS` with no corresponding LIVE lease (`read_all_leases`
   already drops any lease whose recorded worktree path no longer exists,
   T-0473's own liveness guard, so "no live lease" covers both "never had
   one" and "had one, but the worktree died"). Reconciled by transitioning
   it back to `QUEUED` -- the exact same legal state-machine edge `frob
   ticket requeue` (T-0472) uses -- which releases any lingering lease as
   a side effect of `transition` itself (T-0473's sync).
2. **Orphan worktree**: a real, live `git worktree` (`git worktree list
   --porcelain`, excluding the main checkout) that no lease names at all --
   an agent whose ticket was closed/requeued/failed out from under it, or
   that never started one.

```
frob ticket reconcile                          # dry-run: report only
frob ticket reconcile --apply                   # requeue stale holds;
                                                 # flag (not remove) orphans
frob ticket reconcile --apply --remove-orphans  # also `git worktree
                                                 # remove --force` orphans
```

`--apply` alone only touches ticket state (a reversible, cheap action);
actually deleting a worktree (`--remove-orphans`, which requires `--apply`
too) is gated behind its own separate opt-in since it is a strictly more
destructive action than requeuing a ticket -- this is a narrower,
safety-first reading of "auto-clean" than a bare `frob clean` tier reuse
would have been: `frob.clean`'s tiers operate on build/cache ARTIFACTS
(`__pycache__`, `dist/`, ...), not on live git worktrees, so orphan-worktree
removal is its own `git worktree remove` call here, not routed through
`frob.clean`.

## Intent journal (T-0456)

`frob ticket land` mutates more than one artifact in sequence (worktree
merge, ledger splice/close, squash-apply onto the target root, optional
version bump + native rebuild) -- a crash or power loss partway through
used to leave no record that an operation had ever been in flight.
`frob.tickets._journal` closes that gap:

- `write_intent(root, ticket_id, worktree)` records a small
  `<root>/.frob/journal/<ticket-id>.json` marker (via `_store.atomic_write`,
  so the marker itself is crash-safe) at the very start of `land()`, before
  any of its steps mutate anything.
- `clear_intent(root, ticket_id)` removes it -- `land()` calls this from a
  `finally` block, so it runs on EVERY exit: success, a clean/handled
  `Err`, or a raised exception. A marker that OUTLIVES the process is
  therefore only possible if the process died before reaching its own
  cleanup (killed, power loss, OOM).
- `read_all_intents(root)` lists every currently-recorded marker.

`frob ticket reconcile` (above) treats a leftover marker as its third
anomaly class -- **orphaned land intent**: reported (never resumed or
rolled forward automatically) in every run, and cleared (aborted) only
under `--apply`. Automatically resuming/rolling-forward a partially
completed land was judged too risky to attempt blind (the actual git/ledger
state after a crash could be at any of several different points in the
sequence) -- `--apply` here means "stop treating this as in-flight", not
"finish the job"; the ticket itself is left exactly as `land`'s own partial
progress left it, for a human/agent to inspect and re-run `frob ticket
land` from scratch once satisfied nothing was left dangerously
half-applied.

```
frob ticket reconcile           # dry-run: also reports orphaned land intents
frob ticket reconcile --apply   # also clears (aborts, does not resume) them
```

Journal files are LOCAL to `root` -- unlike the T-0473 cross-worktree lease
side-channel (which lives under the shared git common dir so every linked
worktree can see it), an in-flight `land` only ever mutates the one
worktree/root pair it was invoked against, so there is nothing
cross-worktree to reconcile for this anomaly class.

## Atomic ledger writes (T-0456 hardening)

`frob.tickets._store.atomic_write` (every `tickets.md`/`.frob-release.json`
/lease/journal write goes through it) now `fsync`s the temp file before the
`os.replace` that makes it visible under the real path. `os.replace` alone
is atomic AT THE FILESYSTEM level (you never observe a half-renamed file),
but without an `fsync` first, a power loss between the write and the
rename can leave the temp file's data unflushed to disk -- on filesystems
that journal renames separately from data blocks, replaying the rename
after a crash can then surface a zero-length or truncated file even though
the rename itself "completed". `fsync`ing the temp file's own fd first
guarantees the data is durable before the rename runs, so a crash at any
point around a `tickets.md` write leaves either the OLD content or the
FULLY-written NEW content, never a partial one.

## Scope/lease change protocol (T-0455)

`frob ticket scope <id> --add GLOB... --remove GLOB... (--reason TEXT |
--reason-file PATH)` formally expands or reduces a ticket's declared
`scope` -- and, since the
T-0453 tree-lease is derived LIVE from an in-progress ticket's `scope`
(`_in_progress_leases`), its active tree-lease too, in one atomic write.
This is the accountable replacement for the ad-hoc `frob:waive SCOPE001`
dodge (T-0176/T-0220 precedent): an agent that discovers mid-work that a
fix structurally needs a file outside its declared scope runs this instead
of waiving the gate, and the mutation is recorded, not hidden.

- `frob.tickets.mutate_scope(root, ticket_id, add=(...), remove=(...),
  reason="...")` is the library entry point; the CLI subcommand is a thin
  forward with no logic of its own. Held under `ledger_lock` end to end
  (load, validate, write) -- the T-0458 single-writer invariant, never a
  hand-edit of `tickets.md`. T-1123: `mutate_scope` and its private
  validation/conflict-detection helpers live in `src/frob/tickets/
  _scope.py` (carved out of `tickets/__init__.py`, T-1108/T-1103's per-
  family extraction pattern -- smallest cohesive unit, `__all__` re-export,
  zero caller-visible behavior change), re-exported from the package
  unchanged so `frob.tickets.mutate_scope` keeps working for every
  existing caller.
- **Audit trail**: every mutated glob appends one `ScopeChangeEntry` (`op`,
  `glob`, `reason`, `actor`, `at`) to the ticket's `scope_changes` list --
  append-only, never edited or removed, so scope creep is visible in the
  ledger itself rather than buried in a waiver comment.
- **Fails loudly on an `--add` overlapping another lease**: if the
  requested glob's overlap check (`scope_overlap_globs`) against ANY OTHER
  in-progress ticket's full declared scope (not breadth-demoted -- an
  explicit expansion request is a stronger claim than a passive `doable`
  listing) finds a collision, the whole call is rejected with
  `ScopeLeaseConflict` and the error names the holding ticket id and the
  colliding glob (`cannot lease '<glob>': held by in-progress T-0xxx (scope
  '<holder-glob>')`) -- an agent can never silently grab a path another
  agent is actively writing.
- **`--reason-file PATH` (T-0737)**: reads the reason verbatim from PATH
  instead of the shell -- long or backticked/quoted/`$`-laden reason prose
  passed inline through bash risks command substitution before frob ever
  sees it (the T-0627/T-0697/T-0735/T-0736 incidents this fixes for
  `scope`, mirroring `done-report --why-file`, T-0458's precedent).
  Mutually exclusive with `--reason` -- giving both exits 1; giving
  neither also exits 1 (one of the two is always required).
- **Guardrails**:
  - `--add`/`--remove` both empty is `ScopeChangeEmpty`; a blank `--reason`
    is `ScopeChangeReasonMissing` -- neither op is ever a silent no-op.
  - `--remove` of a glob not verbatim in the ticket's current `scope` is
    `ScopeRemoveNotDeclared` (nothing to release).
  - `--remove` of a glob that already covers a recorded evidence id's
    leading `path::` segment is `ScopeRemoveOrphansEvidence` -- a reduction
    can never orphan already-bound work.
  - An over-broad `--add` glob (the same criterion `large_glob_warnings`
    uses) is logged at WARNING, not rejected -- a nudge, not a hard block,
    matching T-0453's existing breadth posture.
- **Example** (the T-0446 new-subcommand scope gap): before T-0446, a
  ticket scoped to `src/frob/tickets/**` that needed to register a new CLI
  subcommand had to run `frob ticket scope T-#### --add
  src/frob/__main__.py --reason "new subcommand registration"` (repeated
  per wiring file) instead of `frob:waive SCOPE001 reason="... T-0176/
  T-0220 precedent"`. This is still the right move for anything OTHER
  than the three well-known wiring files below -- see the next section for
  what no longer needs it.

### CLI-wiring files are implicitly in scope for FEATURE tickets (T-0446)

Every `frob ticket <subcommand>` a feature ticket adds structurally needs
to touch the SAME three files no matter what scope was declared at filing
time: the dispatch table (`src/frob/__main__.py`), the CLI flags it reads
(`src/frob/app/config.py`), and the runner that implements it
(`src/frob/app/ticket_runner/**`, a package since an earlier split of the
<!-- frob:waive DOC006 reason="deliberately names the pre-split module as history -- explains WHY it is now a package; the file legitimately no longer exists under this name" -->
original `src/frob/app/ticket_runner.py` module; T-1163 fixed
`CLI_WIRING_FILES` to match after it had gone stale post-split) --
`frob.tickets._models.CLI_WIRING_FILES`. T-0323 (the `merge-driver`
subcommand) hit exactly this:
scoped to `src/frob/tickets/**`, it needed all three and had to run
`frob ticket scope --add` per file, which is exactly the "scope-expansion
ceremony" T-0446 was filed to close.

`scope_matches(path, scope, kind=ticket.kind)` -- and, downstream, the
SCOPE001 gate (`scope_gate`, which now passes `ticket.kind` through) --
treats `CLI_WIRING_FILES` as implicitly in scope whenever `kind ==
TicketKind.FEATURE`, the same pattern `LEDGER_PATH`'s always-in-scope rule
(T-0241) established for `tickets.md`. This is deliberately FEATURE-only:
a bug/docs/security ticket touching the CLI dispatch table unannounced is
real scope creep, not the structural necessity this closes, so it still
trips SCOPE001 and still needs an explicit `frob ticket scope --add` (or a
new ticket) like any other out-of-scope file. `kind=None` (the default,
and every call site that predates T-0446) preserves the exact prior
behavior -- this is additive, not a loosening of any existing check.

## Organization: components, labels, board, epics (T-0454)

The user's "professional dev-team workflow, no ceremony" request made
concrete: additive fields plus read-only views on top of the existing
flat ledger, never a second parallel store.

- **`component: str | None`** -- which module/area a ticket belongs to
  (`gates`, `strata`, `dup`, `vet`, `deploy`, `render`, `tickets`, ...).
  Freeform, not an `enum`, since the set of components grows with the
  codebase and a fixed enum would need a migration every time a new
  subsystem is carved out. `frob ticket component <id> <name>` sets it
  (`set_component`); `<name>` may be the literal string `"none"` to clear
  it back to uncategorized. `frob ticket new --component NAME` sets it at
  creation time.
- **`labels: tuple[str, ...]`** -- freeform tags orthogonal to
  `component` (cross-cutting concerns like `perf`, `security`, `flaky`).
  `frob ticket label <id> --add TAG... --remove TAG...` (`mutate_labels`)
  mutates an existing ticket's labels; `frob ticket new --label TAG`
  (repeatable) sets them at creation. Comma-joined entries split the same
  way `scope` entries do (T-0241's `_split_scope_entries`, reused as-is).
  Unlike `mutate_scope`, a label mutation carries no lease-conflict check
  (a label is not a filesystem glob) and no `scope_changes`-style audit
  trail -- it is a plain organizational tag, not a claim on the tree.
- **Epic -> story -> task rollup**, via the EXISTING `parent` field made
  first-class: `frob ticket epic <id>` (`epic_rollup`) walks every
  descendant transitively (any depth, not just direct children) and
  reports `done`/`total`/`percent_complete` plus the ids of any LEAF
  descendant (no children of its own) that is currently `BLOCKED` -- the
  two numbers a human scanning an epic wants first, computed once instead
  of hand-counted. `Err(NotFound)` if the epic id itself does not resolve.
- **Priority-ordered board**: `frob ticket board [--component NAME]
  [--label TAG] [--json]` (`board_view`) groups every ACTIVE ticket into
  `BOARD_STATES` columns (`queued -> planned -> in-progress -> blocked ->
  done -> dropped`, always ALL SIX, even empty), each ordered by
  `_doable_sort_key` (highest priority first, then oldest, the same T-0411
  ordering `doable` uses) -- a glance at the board reads like a pipeline,
  not an arbitrary id-ordered dump. `--component`/`--label` narrow to one
  area/tag; a ticket must match BOTH when both are given.
- **Additive, splice-safe**: every new field is optional with a default
  (`component=None`, `labels=()`), so every ticket written before T-0454
  stays valid on load with no migration step, and each round-trips through
  `write_ticket`/`_splice_ticket_section` for free -- both call the
  generic `ticket.model_dump(mode="json", exclude={"body"})` (T-0505's
  single-writer splice path), so a NEW pydantic field needs no
  serialization code of its own, only a schema addition (same as T-0411's
  `priority` field before it). The T-0323 ledger merge-driver
  (`splice_ledger`) operates on whole `<!-- ticket:... -->` sections, not
  individual fields, so it is unaffected by any field addition here too.

**Deliberately NOT built in this pass** (filed as follow-ups rather than
half-landed): sprints/milestones (a `sprint`/`milestone` id+goal+date-
window field plus `frob ticket sprint new/list/show/assign` CRUD) --
"if they fit" per the ticket's own body, and a full sprint lifecycle is a
second feature-sized surface on top of the component/label/board/epic
core this pass delivers; a `--component`/`--label` filter on `frob ticket
doable`/`list` (currently only `board` filters, so a coordinator draining
one area still uses `board` for that, not `doable`); and bulk
component/label reassignment (each mutation is one ticket at a time via
`set_component`/`mutate_labels`, matching every other single-ticket
mutation command's granularity).

## Runs-last marker (T-1613)

frob could express "this ticket is blocked by that ticket" (a fixed,
enumerable `blocked_by` edge set) but not "this ticket must be the last
thing done in the repository" -- a dynamic constraint that has to hold
against whatever tickets exist NOW, including ones filed after the
runs-last ticket itself. The motivating case: an audit whose correctness
depends on nothing else changing underneath it. Its `blocked_by` edges
can only name tickets that existed when it was filed; anything filed
afterward must ALSO precede it, and nothing enforced that -- the
constraint survived only as prose in the ticket body, exactly the kind of
tribal knowledge frob exists to replace with enforcement.

**`Ticket.runs_last: bool`** (default `False`) is the marker.
`frob ticket runs-last <id> <on|off>` (`set_runs_last`) flips it on an
existing ticket; both directions are ordinary single-writer,
ledger-locked mutations, same shape as `set_tier`.

**Definition of "any other ticket open"**: every ticket in the ledger
OTHER than the runs-last ticket itself, and OTHER than any fellow
runs-last ticket, whose state is non-terminal (`queued`/`planned`/
`in-progress`/`blocked` -- `_OPEN_STATES`, the same set `_open_blockers`/
`_start_blockers` already use for `blocked_by`). This was a deliberate
choice over "only in-progress with a live lease": a QUEUED ticket someone
starts a minute later is the identical hazard, just deferred -- gating on
in-progress alone would let a coordinator dispatch straight into the
window the marker exists to close. Fellow runs-last tickets are excluded
from the count so two or more can coexist and order among THEMSELVES via
ordinary `blocked_by` edges, rather than deadlocking each other (each one
would otherwise count the other as permanently "open").

**Structural, not advisory** -- the failure mode a bare warning cannot
close: nothing stops an agent from popping a runs-last ticket early if
the constraint is only a nudge (the same failure `scope-ack`/TICK009
already lives with, T-1484 -- reported repeatedly, acted on by hand).
Two enforcement points close it instead:

- **`doable`** (`frob.tickets._doable._doable_candidates`,
  `_other_open_tickets`): a `runs_last=True` candidate never surfaces
  while any other ticket is open, full stop -- not filtered by
  `--show-blocked`-style demotion, simply absent from the list.
- **`start`** (`frob.tickets._evidence._transition_guard`'s
  `IN_PROGRESS` branch, `_runs_last_start_blockers`): the `queued/
  planned -> in-progress` transition refuses with `TicketError.
  RunsLastBlocked`, and the accompanying log line names every remaining
  open ticket id, so the refusal is actionable rather than a bare error
  code.

**Filing while a runs-last ticket is running invalidates its
precondition** -- this is the requirement that makes the marker real
rather than cosmetic. The failure mode is not starting the runs-last
ticket too early (the two enforcement points above already close that);
it is FINISHING it and then having new work land that silently
invalidates its conclusions. `frob.tickets._new_renumber.new_ticket`
(`_warn_if_runs_last_ticket_in_progress`) logs a loud WARNING -- naming
every runs-last ticket currently `IN_PROGRESS` -- whenever a fresh
ORDINARY (non-runs-last) ticket is filed; this does not block filing
(new work is still legitimate), it makes the invalidation visible instead
of silent.

## `frob ticket brief` (T-0568)

A coordinator dispatching a ticket to an agent hand-typed the same
~400-word briefing (body/plan, scope, playbook hard-rule references,
exact verify commands for the area, gate-baseline status, REL/land rules)
roughly 30 times a session (T-0568's origin note). `frob ticket brief
<id>` composes the whole thing from data already available, so a dispatch
prompt collapses to `frob ticket brief T-XXXX` plus whatever the
coordinator wants to add.

`frob.tickets.brief_ticket(root, ticket_id) -> Result[str, TicketError]`
delegates to `frob.tickets._brief.compose_brief`, which assembles:

- **Body + acceptance** -- the ticket's own Description/Plan body verbatim,
  plus its `acceptance` list if non-empty.
- **Scope + leases** -- the declared scope globs, plus any active lease
  collision (`leased_by`) so the agent sees immediately if another
  in-progress ticket already holds an overlapping path.
- **Concurrent leases (do NOT touch)** (T-1347) -- every OTHER in-progress
  ticket's id, title, and scope globs, resolved live at brief time
  (`frob.tickets._brief._concurrent_leases_section`). Under N-way
  concurrent dispatch this is the single most important thing an agent
  needs and previously the one piece of a dispatch prompt a coordinator
  still had to hand-write; omitted entirely when no other ticket is
  in-progress.
- **Concurrency hazards** (T-1347) -- two fixed reminders: commit any
  new/changed test BEFORE running `frob ticket land` (a killed
  mid-auto-fix land can garble a file, and the obvious `git checkout --
  <file>` recovery then silently discards uncommitted work elsewhere,
  T-1338), and a transient DirtyMain refusal under concurrency is
  expected -- wait and retry, never touch main by hand to clear it.
- **Playbook hard rules** -- `frob.tickets._brief._parse_playbook_sections`
  parses every numbered `## N[letter]. Title` heading out of `docs/guides/
  agent-playbook.md` (a real markdown parse, not a hand-copied section
  list that drifts the moment the playbook is renumbered or a section is
  added/removed) and renders each verbatim. A repo with no playbook at
  that path (a sibling repo the pattern has not spread to yet) gets an
  empty section here, not a hard failure -- every other part of the brief
  still renders.
- **Verify** -- `infer_verify_commands` always includes the scoped gate
  check (`frob check --ticket <id>`), plus a targeted `pytest` invocation:
  scope entries already naming a `tests/` path are used directly; failing
  that, `root/tests` is searched (a real filesystem `rglob`, not a naming
  guess) for a test file whose stem contains a scope entry's own stem.
- **Gate baseline** -- whether `.frob/baseline` exists, so the agent knows
  up front whether `--delta` will report only new violations or degrade
  to the full set (docs/guides/agent-playbook.md#6).
- **REL/land rules** -- a fixed reminder of the REL001/CHANGELOG
  obligation and the "commit per ticket, never push/merge main from a
  worktree" rule, with the CURRENT `pyproject.toml` version filled in
  (`current_version`) so the reminder names a real number, not a stale
  placeholder.

`Err(NotFound)` if `ticket_id` does not resolve, same as every other
single-ticket command.

## Frob ticket brief --cluster (T-1243)

A coordinator dispatching an epic/story's leaf tickets one at a time pays
worktree creation, a playbook read, and a `frob natives build` PER TICKET,
even though every ticket in the series lands into the same worktree in
practice (the "serial-cluster dispatch" coordinator convention). `frob
ticket brief --cluster <epic-or-story-id>` and `frob ticket work --cluster
<epic-or-story-id>` make that convention a first-class verb pair instead
of a hand-assembled dispatch prompt.

`frob.tickets.brief_cluster(root, cluster_id) -> Result[str, TicketError]`
delegates to `frob.tickets._brief.compose_cluster_brief`, which composes
ONE briefing covering `frob.tickets._brief.cluster_descendants`' result:
every `TicketTier.TICKET` descendant of `cluster_id` (via `epic_rollup`'s
parent-chain walk, any depth) that is still {queued, planned} and whose
open blockers, if any, are all other members of the same cluster --
sequenced by a topological sort over those intra-cluster `blocked_by`
edges (ties broken by the same priority/age order `doable` uses), never
listing a dependent ticket ahead of the dependency it needs. Unlike
`compose_brief`, the playbook hard-rule sections and the REL/land rules
render ONCE for the whole mission; the union scope
(`frob.tickets._brief.cluster_union_scope`, a deduplicated, order-
preserving union of every member's declared scope) is the single lease
the mission acquires; each member ticket's own body, acceptance, and scope
render in its own numbered "Member i/N" section; and an explicit "Land
cadence" section reminds the agent to land ONE ticket at a time, in
sequence, as each closes -- never one mega-land for the whole cluster.

`frob ticket work --cluster <epic-or-story-id> [--worktree PATH]`
(`frob.app.ticket_runner._lifecycle._work_cluster`) is the leasing half:
create/reuse ONE worktree (default `.claude/worktrees/<cluster-id-
lowercased>`, same convention as single-ticket `work`), merge `main` for
freshness, and build natives -- each exactly ONCE for the whole cluster --
then walk `cluster_descendants`' dependency order, starting each member
whose blockers are ALREADY resolved (reusing the existing single-ticket
`_start` transition -- auto-plan a queued ticket, background pre-work
sweep -- rather than inventing a second state-machine path). A member
still blocked by an EARLIER member of the SAME cluster cannot legally
start in this same pass: the ticket state machine's own transition guard
refuses an open `blocked_by` entry, and becoming IN_PROGRESS is not the
same as that blocker CLOSING. Such a member is left queued/planned and
reported as deferred -- startable with an ordinary `frob ticket start
<id>` in this SAME already-leased worktree the moment its blocker
actually closes, no new worktree/warmup needed. Before creating or
touching anything, `_refuse_on_cluster_scope_conflict` computes the union
scope and refuses loudly (naming the colliding ticket id and glob) if it
overlaps an ALREADY in-progress ticket's active lease that is not itself
a member of this cluster -- the same disjoint-scope dispatch guarantee
`frob.tickets.leased_by` already gives a single-ticket `start`/`doable`,
extended to the union-scope case so two clusters can never silently
double-lease the same files. Each started member's own lease still
releases individually, exactly like an ordinary single-ticket lease, the
moment that ticket closes -- a cluster mission shares only the worktree
and the one-time warmup cost, not a single combined lease that only
releases when every member is done.

`Err(NotFound)` if `cluster_id` does not resolve; an empty result (no
dispatchable member found -- every descendant is already done/dropped, or
every remaining one is blocked by something outside the cluster) is a
loud CLI refusal, not a silent no-op briefing/lease.

## State machine

```
queued -> planned -> in-progress -> done
   |         |            |-> blocked -> in-progress
   |         |            |-> queued        (yield: agent gives it back)
   +---------+------------+-> dropped      (explicit, with reason in body)
```

Any other transition is `Err(InvalidTransition)`. `done` and `dropped` are
terminal. Cutting scope is `dropped` with a reason -- recorded, not deleted.

`frob ticket drop <id> --reason TEXT [--absorbed-by T-####]` (T-0579) is the
first-class CLI for this transition, replacing the pre-T-0579 workflow of
hand-editing `state: dropped` directly into the ledger (which left leases
dangling and recorded no reason at all). It appends a dated line
(`- <date>: <reason>` with an optional `(absorbed by T-####)` suffix) under
a `## Drop reason` body heading -- same append-a-section shape as
`record_failure`'s `## Failure log` -- then runs the ordinary DROPPED
transition, so a held worktree lease releases exactly the way any other
terminal transition releases one. `Err(DropReasonMissing)` if `--reason` is
blank: a drop with no reason is indistinguishable from a silent discard
later. Works for `queued`/`planned`/`in-progress`/`blocked` tickets (every
state DROPPED is reachable from) and for drafts the same as any other id.

The `in-progress -> queued` yield is `frob ticket requeue <id> [--reason
TEXT]` (T-0472): the honest CLI path for a parked or mis-started ticket,
so it never has to be hand-edited back to `queued`. `--reason` is optional
and, if given, is only logged (not persisted on the ticket) -- requeue has
no Done-report/evidence surface of its own to attach it to. Since the
T-0453 tree-lease is derived live from `in-progress` state + declared
scope, requeuing alone releases the lease -- no separate release step.
Only an `in-progress` ticket can be requeued; anything else is a hard
error naming the ticket's actual state.

## Provisional ids

T-0162's collision-proofing mechanism. `frob ticket new` mints an id
differently depending on which branch the checkout is on
(`frob.tickets._provisional.on_default_branch`, backed by `frob.gitio`):

- **On the default branch** (main/master, or wherever `origin/HEAD` points):
  the next sequential `T-####`, exactly as before -- the merged
  active+archive view is authoritative there, so sequential allocation is
  safe.
- **Off the default branch** (a feature branch, a linked worktree checked
  out to its own branch -- git cannot check the same branch out twice, so
  EVERY linked worktree is, by definition, off the default branch): a
  provisional `T-draft-<8 hex chars>` id (`mint_draft_id`), never a
  sequential one. Two checkouts filing independently each draw from this
  disjoint, content-nonce id space -- collision probability per pair is
  ~1/2^32, and the ledger's own duplicate-id load check still catches the
  freak case loudly (see TICK001 below).
- **Ambiguous** (no git repo, detached HEAD, git unavailable): treated as
  default-branch, so non-git fixtures/CI-detached checkouts keep the old
  sequential behavior unchanged -- drafts are minted only when a non-default
  branch is POSITIVELY identified, never by default.

A draft id round-trips through storage like any other id (the ledger
marker/filename regexes accept `T-draft-<hex>` alongside `T-####` -- getting
this wrong makes a draft ticket silently vanish from `frob ticket list` the
moment it's written, which is exactly the "vacuous pass" class this whole
tool exists to prevent).

`finalize_draft(root, draft_id)` is the callable finalize step: once a
draft has actually landed on the default branch, it assigns the draft its
real sequential id (against the then-current merged view) and rewrites the
ledger plus every code reference via `renumber_one`. `frob ticket land`
(T-0176, see below) calls it automatically as part of an atomic merge/land
step; outside of `land`, finalizing a draft is still a manual `frob ticket
renumber <draft-id> <next-id>` (or a direct `finalize_draft` call from a
script) -- for a worktree not going through `land` at all.

**T-1090: the next-id computation is atomic with the commit.**
`finalize_draft` used to load the merged view and compute the candidate
final id OUTSIDE any lock, only acquiring `ledger_lock` afterward (inside
`renumber_one`, once the id was already fixed) -- two sibling lands each
renumbering their own residue draft against the same root could both read
the same pre-write snapshot and both compute the SAME final id (the
T-1086-vs-T-0684 field incident, third occurrence). The whole read
(`_load_merged`), compute (`_next_ticket_id`), and write (`renumber_one`)
sequence is now held under one `ledger_lock(root)` span (reentrant, so
`renumber_one`'s own internal lock acquisition is a no-op re-entry rather
than a deadlock) -- a concurrent finalizer blocked on the lock always
recomputes its id against the fresh post-write ledger the moment it
acquires the lock, never a stale pre-write snapshot. Mirrors the
`new_ticket`/T-0458 single-writer allocation pattern.

**T-1179: `finalize_draft`'s lock is still only over the WORKTREE it
renumbers -- a ticket filed directly on main is invisible to it.**
`land` (T-0176) always finalizes its landing (and any sibling) draft
against a WORKTREE checkout, which can be stale relative to main's
CURRENT ledger (a ticket filed straight onto main via `new_ticket`, itself
serialized by `ledger_lock(main_root)`, in the window after the worktree
last synced). T-1090's atomic allocation only protects `finalize_draft`
against ANOTHER `finalize_draft`/`new_ticket` racing on the SAME root --
it never reads main's root at all when `root` is a worktree, so it cannot
see a filing that landed on a different path. The 2026-07-29 incident:
`new_ticket` claimed an id directly on main (46a115c4); a land in flight
finalized its own residue draft against the worktree's stale view and
picked the exact same id; the squash-splice then silently overwrote
main's block (17c6ca89). `finalize_draft_for_land(worktree, draft_id,
main_root)` is the fix `land`'s own finalize callers (`_finalize_draft_id`/
`_finalize_sibling_drafts` in `frob.tickets._land`) now use instead of
plain `finalize_draft`: it reads `main_root`'s ledger FRESH from disk
(closing the staleness gap) and computes the id ceiling from its union
with `worktree`'s own view, under `worktree`'s `ledger_lock` (same lock
footprint as plain `finalize_draft`).

This does NOT also lock `main_root` -- that was tried and reverted. Doing
so leaves `main_root/.frob/tickets.lock` behind as an untracked artifact
on `root`'s working tree; on a repo/fixture where `.frob/` is not
gitignored (the worktree branch legitimately tracks its OWN
`.frob/tickets.lock`, T-1006), the land's later `git merge --squash` from
that worktree branch then refuses with git's own "untracked working tree
files would be overwritten by merge" error -- a real, reproduced
regression (`tests/test_ticket_land.py::TestWipCommit`/
`TestWipCommitNormalizationOnlyDirty` caught it), not a hypothetical one.
The narrow residual race the unlocked read leaves (a `new_ticket` landing
on main in the tiny window between this read and the eventual
squash-apply) is closed by the SECOND guard instead: the land-time
ticket-scoped splice (`_overlay_landed_ticket`/`_splice_only_ticket`, see
below) refuses (`IdTitleMismatch`) rather than silently overwrites if the
id it is about to overlay already exists on main under a DIFFERENT
title -- this runs under a REAL lock (`_squash_and_splice_ledger`'s own
`ledger_lock(root)`), at the point that actually commits to main, closing
exactly the window the first guard's unlocked read cannot itself close.
The two guards are deliberately complementary defense in depth, not each
independently sufficient.

**T-1622: land-time promotion, not cross-worktree allocation, is the
committed design.** An earlier draft of T-1622 considered making a
worktree allocate a REAL id at filing time (a shared, cross-worktree
counter under the git-common-dir) so no draft/finalize round-trip was
needed at all. That approach was explicitly rejected: a worktree
allocating against a shared mutable resource re-introduces exactly the
kind of cross-checkout coordination this whole mechanism exists to avoid
(an agent guessing the next free id to dodge the draft round-trip
collided with a real id filed on main the same session). The kept design
is what this section already documents -- a draft stays local and opaque
until `land` promotes it, inside the land transaction, where an exclusive
lease already makes allocation race-free. `_finalize_sibling_drafts` +
`_rewrite_draft_references_in_bodies` (the mapping passed to the rewrite
is `draft_id_mapping`, covering BOTH the ticket actually being landed and
every OTHER draft ticket finalized alongside it) together mean this
promotion already reaches every citation, in every ticket's body, not
just the landing ticket's own -- the exact "an agent files a follow-up
from a worktree, lands its work, and nobody touches the ledger by hand
for the citation to be correct on main" acceptance T-1622 was filed to
guarantee. `tests/test_ticket_land.py::TestDraftReferenceRewriteOnLand::
test_land_rewrites_a_sibling_drafts_citation_in_the_primary_done_report`
proves the cross-ticket shape explicitly (a DIFFERENT ticket's Done
report citing a sibling's draft id, not the landing ticket citing
itself).

### `frob ticket promote` (T-1637)

The first-class replacement for the lossy hand-rolled draft-refile recipe
(read a draft's body out of the worktree ledger, `frob ticket new` a fresh
ticket on main, delete the draft's own block, string-swap every citation
by hand). That recipe drops whatever `frob ticket new` cannot recreate --
most critically, the draft's evidence ids and Done report (the T-1636
incident: 12 evidence ids and a 12KB Done report discarded, recoverable
only via `git show <sha>~1:tickets.md` archaeology). `frob ticket promote
<draft-id> [--path DIR]` is a thin CLI wrapper over `finalize_draft`
(`frob.app.ticket_runner._promote`): it allocates the draft's next real
`T-####` id against the current merged view and rewrites the ledger block
plus every code reference to it via `renumber_one` -- the same rename
primitive `frob ticket renumber <old> <new>` exposes directly for the
case where both ids are already known. Because it is a RENAME, not a
copy-then-delete, every field of the `Ticket` object (evidence, Done
report, scope, state, acceptance) moves onto the new id automatically;
nothing the operation itself does can lose them. A no-op (logged, exit 0)
if the given id is already final -- callers do not need to check
`is_draft_id` first.

`land` already calls this same `finalize_draft`/`finalize_draft_for_land`
machinery automatically for the ticket it lands plus every sibling draft
still in the worktree's ledger (see "Provisional ids" above) -- `promote`
exists for the case a real id is needed OUTSIDE of a land: a coordinator
recovering residue from an abandoned worktree, or promoting several
drafts on main directly without a land transaction to piggyback on.

### Content-loss guard on `write_ticket` (T-1637, defaults flipped T-1679)

`write_ticket` (`frob.tickets._store`) compares an incoming write against
whatever is currently on disk for that id, via `_check_no_content_loss`:
if the existing ticket carries non-empty evidence or a `## Done report`
section and the incoming write has NEITHER, the write is flagged.
`strict_no_content_loss=True` is now the DEFAULT (T-1679): the write
REFUSES (`Err(DoneReportOrEvidenceDiscarded)`) rather than merely warning.
T-1637 shipped this warn-only, since `write_ticket` was also the low-level
primitive several test fixtures used directly to construct a deliberately
"poorer" snapshot on purpose (test fixtures simulating a stale/regressed
ledger side for `splice_ledger`'s own merge-preference tests being the
concrete case that made a hard-refuse-by-default break real, correct code
at the time) -- but a guard whose default is to ALLOW the exact loss shape
it detects is a detector, not a guard: the T-1636 incident it exists to
prevent would still happen today under a warn-only default, just with a
log line attached.

T-1679 flipped the default and gave the genuine "poorer snapshot on
purpose" callers their own explicit primitive instead:
`_write_ticket_unchecked` (T-1711: `tests._write_unchecked`, relocated out
of `frob.tickets._store` so its WIRE001 waiver can use the `permanent=
"true"` test-tree exemption instead of an ever-orphaning `follow_up`
ticket -- private, test-fixture-only, never a production write path)
skips the content-loss check ENTIRELY, no warning at all, and says so
plainly at the call site instead of `write_ticket` itself needing a
weaker default to accommodate it. Every fixture that previously relied on
the old warn-and-proceed default (the `splice_ledger` merge-preference
tests in `tests/test_ticket_land.py`, the `TICK005` land-regression
simulation tests) now calls `_write_ticket_unchecked` explicitly.
`strict_no_content_loss=False` still exists as an explicit, disclosed
opt-out (same warn-and-proceed behavior as before) for a caller with a
specific reason to want it, but no production call site in
this repo passes it -- every real writer (the setters, `add_evidence`,
`transition`, `set_done_report`, etc.) gets the strict-by-default
refusal, confirmed by the full `write_ticket`-touching test surface
passing unmodified after the flip (no production caller legitimately
needs to empty both fields at once).

This is the sibling of `_post_splice_integrity_check` (T-0764/T-1536,
"Storage internals" below) one level down: that guard refuses a write
that would drop a ticket ID from the ledger outright; this one covers the
id SURVIVING while the recorded work on it silently vanishes -- exactly
the T-1636 shape (a hand-rolled refile reconstructing a ticket from
scratch under the same id, losing its evidence and Done report). `old is
None` (first write for a brand-new id, e.g. `new_ticket`) is always fine
-- there is nothing to lose yet.

### Decision record: T-0162

Three real collisions in one day (all sequential max+1 races across
independent checkouts) forced the question of HOW to make id collision
structurally impossible, not just less likely. Candidates considered:

1. **Provisional ids, finalized at land** (CHOSEN). Off-default-branch
   `new_ticket` mints a `T-draft-<hex>` id; sequential ids are only ever
   minted against the default branch's merged view. Two checkouts filing
   independently structurally cannot converge on the same final id -- there
   is no shared mutable sequence for them to race on until one, precisely
   defined, finalize step runs. Composes cleanly with the queued T-0176
   land command: `finalize_draft` is the exact primitive it needs to call.
   Cost: an id that appears in conversation/commits before finalize is not
   the ticket's permanent name (mitigated -- `frob:ticket`/`frob:waive`
   references written against a draft id are rewritten by the same
   `renumber_one` that finalize uses, so nothing needs re-typing by hand).
2. **Branch-tip scanning as defense-in-depth** (partially folded in, not a
   separate mechanism). Making `_next_ticket_id` scan every local ref tip
   (not just the active+archive files at HEAD) was considered as the
   PRIMARY mechanism, but rejected on its own: it only sees refs the local
   git object database already has (an agent's sibling worktree on an
   unfetched remote branch is invisible), so it narrows the collision
   window without closing it, and it makes every `new_ticket` call pay a
   multi-ref git scan. Provisional ids close the window unconditionally and
   pay no such cost on the common path (a single `rev-parse` +
   `symbolic-ref`/`show-ref` check). Not implemented separately.
3. **Content-nonce tiebreak** (folded into (1), not a distinct mechanism).
   Rather than resolving a collision after the fact by hashing content,
   choice (1)'s draft ids ARE content-nonces (`secrets.token_hex`) minted
   up front -- the same idea, applied at allocation time instead of at
   conflict-resolution time, so there is no conflict to resolve.

**Why TICK001/TICK002 are unwaivable** (see `_UNWAIVABLE_RULES` in
`frob.gates`, alongside TEST008): both rules exist specifically to make a
silent break of the T-0162 invariant loud. TICK001 (an id in both active
and archive) is mostly moot in practice -- `_load_merged`/`_parse_ledger`
already hard-Err the whole `frob check` run before a gate violation could
even be produced -- but is kept as an unwaivable gate rule as defense in
depth against a future change that makes ledger loading more permissive.

**T-0929 (perf, no behavior change).** `frob.gates.tickets_gate` used to
have `_tick001_duplicate_ids`/`_tick003_stale_archive`/
`_tick006_phantom_filing` each independently re-read and re-parse the
full `tickets.md`/`tickets-archive.md` ledger text via `load_all`/
`load_archive` (no cache) -- 3 redundant `load_all` calls and 2
redundant `load_archive` calls per `tickets_gate` invocation. The
T-0928 check-performance audit's meta-gap finding (docs/audits/
check-performance.md Finding E, row 10) flagged this class of
same-input-recomputed-N-times cost; `tickets_gate` now loads `active`/
`archived` once and passes the `Result` values to all three rules
instead. Measured `tickets` stage wall time: 2.09s (audit baseline) ->
1.10-1.13s after. TICK001/TICK002's own invariant contract above is
unaffected -- only how many times the ledger text is parsed to answer it.

**T-1129 (`tickets_gate` grew a sibling check, no change to this
decision).** `tickets_gate` now also runs TICK011 (a Done-report
disclosed-cut-without-ticket scan, unrelated to the id-collision
invariant this section documents) alongside TICK001-TICK010 -- see
`docs/modules/gates.md#tick011-t-1129-active-window-narrowed-t-1402` for
TICK011's own design.
TICK002 (a `T-draft-*` id surviving onto the default branch) is the rule
that actually matters: it means the finalize step was skipped, failed, or
forgotten, which is precisely the "collision-proofing silently did not
happen" failure mode this whole mechanism exists to prevent. A
`frob:waive TICK002 reason="..."` sitting in the tree would let a live
collision risk sit there quietly forever -- the same reasoning that makes
TEST008 unwaivable.

Residual assumption (reviewer, land note): `finalize_draft` and
`renumber_one` take no cross-process lock -- two truly simultaneous
finalize calls on the default branch could mint the same final id,
caught after the fact by TICK001 rather than prevented. Finalize is
assumed single-actor/serialized until T-0176 (`frob ticket land`)
formalizes locking; do not rely on it as structurally impossible in
concurrent automation.

