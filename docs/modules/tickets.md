# frob.tickets -- statically-checkable ticket and feature queue

One sentence: a git-tracked queue of tickets (features, bugs, audits,
invariant work) with a state machine, blockers, evidence, failure memory,
and image attachments -- the shared work surface for the human and every
agent, so the bottom of the stack is never silently forgotten.

## Storage

Two backends, one interface (auto-detected):

- **single-file ledger** (default): all tickets live in one `tickets.md` at
  the repo root -- the compact central log, no per-ticket file sprawl. Each
  ticket is a `<!-- ticket:T-#### -->` marker + a fenced ```yaml frontmatter
  block + a free markdown body. Greppable (`grep ticket:T- tickets.md`).
- **legacy dir** (back-compat): `tickets/T-####-slug.md`, one file each.
  `frob ticket migrate` collapses an existing dir into the single ledger.

Detection: `tickets.md` present -> single; else `tickets/*.md` -> dir; else
(fresh repo) -> single. Attachments live under `tickets/attachments/<id>/`
in both modes.

```
tickets.md                          the active queue, open + recently-done work
tickets-archive.md                  done/dropped tickets moved by `frob ticket archive`
tickets/attachments/T-0042/01-mockup.png
```

`frob ticket archive` moves every `done`/`dropped` ticket out of `tickets.md`
into `tickets-archive.md` -- same section format, still tracked, still
`grep ticket:T-` compatible -- so the active ledger stays a few hundred
lines instead of growing forever. `load_queue` reads BOTH files (so
blocked_by/parent references and gate joins keep resolving correctly after
a ticket is archived); `frob ticket list`/`doable` read the active file
only (`load_active`), so the archive never bloats them.

A dir-mode ticket file = YAML `---` frontmatter + body; a ledger section is
the same fields in a ```yaml fence. Both pydantic-validated, both strict.

```markdown
---
id: T-0042
title: Clipboard image attach for ticket creation
state: in-progress            # queued|planned|in-progress|blocked|done|dropped
kind: feature                 # feature|bug|security|ux|docs|invariant
origin: human                 # human|agent|auditor
created: 2026-07-16
blocked_by: []                # ticket ids; open blockers make this not doable
parent: T-0040                # hierarchy: planner decomposes goals into trees
scope:                        # blast radius for the scope gate
  - src/frob/tickets/**
  - src/frob/app/ticket_runner.py
evidence: []                  # test node ids, filled before close
attachments:
  - path: attachments/T-0042/01-mockup.png
    caption: paste flow mockup
---

## Description
...

## Plan
...

## Failure log
- 2026-07-16 attempt 1: wl-paste backend; failed -- WSL has no wayland socket.

## Done report
(written by implementer; verified by reviewer before state: done)
```

## Public API

<!-- frob:describes src/frob/tickets/__init__.py::load_queue -->
<!-- frob:describes src/frob/tickets/__init__.py::new_ticket -->
<!-- frob:describes src/frob/tickets/__init__.py::doable -->
<!-- frob:describes src/frob/tickets/__init__.py::transition -->
<!-- frob:describes src/frob/tickets/__init__.py::record_failure -->
<!-- frob:describes src/frob/tickets/__init__.py::attach -->
<!-- frob:describes src/frob/tickets/__init__.py::add_evidence -->
<!-- frob:describes src/frob/tickets/__init__.py::run_cmd_evidence -->
<!-- frob:describes src/frob/tickets/__init__.py::reverify_cmd_evidence -->
<!-- frob:describes src/frob/tickets/__init__.py::add_cmd_evidence -->
<!-- frob:describes src/frob/tickets/clipboard.py::clipboard_image -->
<!-- frob:describes src/frob/tickets/clipboard.py::clipboard_has_image -->
<!-- frob:describes src/frob/tickets/__init__.py::migrate -->
<!-- frob:describes src/frob/tickets/__init__.py::renumber -->
<!-- frob:describes src/frob/tickets/__init__.py::renumber_one -->
<!-- frob:describes src/frob/tickets/__init__.py::finalize_draft -->
<!-- frob:describes src/frob/tickets/__init__.py::archive -->
<!-- frob:describes src/frob/tickets/__init__.py::load_active -->
<!-- frob:describes src/frob/tickets/_provisional.py::on_default_branch -->
<!-- frob:describes src/frob/tickets/_provisional.py::mint_draft_id -->
<!-- frob:describes src/frob/tickets/__init__.py::doable_blocked -->
<!-- frob:describes src/frob/tickets/__init__.py::leased_by -->
<!-- frob:describes src/frob/tickets/__init__.py::large_glob_warnings -->
<!-- frob:describes src/frob/tickets/_models.py::scope_overlap -->
<!-- frob:describes src/frob/tickets/_models.py::scope_overlap_globs -->
<!-- frob:describes src/frob/tickets/__init__.py::set_done_report -->
<!-- frob:describes src/frob/tickets/__init__.py::compose_done_report -->
<!-- frob:describes src/frob/tickets/__init__.py::render_evidence_block -->
<!-- frob:describes src/frob/tickets/__init__.py::render_changed_block -->
<!-- frob:describes src/frob/tickets/__init__.py::compute_changed_lines -->
<!-- frob:describes src/frob/tickets/_store.py::ledger_lock -->
<!-- frob:describes src/frob/tickets/__init__.py::mutate_scope -->

```python
# frob/tickets/__init__.py
def load_queue(root: Path) -> Result[TicketQueue, TicketError]
    # Active store AND tickets-archive.md merged (id-collision checked) --
    # the resolution source for blocker/parent lookups and gate joins, so
    # an archived (done/dropped) ticket never reads as unknown.
def load_active(root: Path) -> Result[TicketQueue, TicketError]
    # Active store ONLY, not the archive -- what `frob ticket list`/`doable`
    # display against, so archived tickets never bloat them (T-0096).
def new_ticket(root: Path, spec: TicketSpec,
                collected: frozenset[str] | None = None) -> Result[Ticket, TicketError]
    # Allocates next id (T-####), writes file atomically. T-0398 D-08:
    # `collected`, when supplied, resolves spec.evidence the same way
    # add_evidence does (Err(UnknownEvidence) on a bogus id); `collected=None`
    # (default) preserves schema-only validation but now logs an explicit
    # UNRESOLVED warning instead of silently skipping the check.
def doable(queue: TicketQueue) -> tuple[Ticket, ...]
    # state in {queued, planned} and no open blockers, ordered oldest-first.
def transition(root: Path, ticket_id: str, to: TicketState, *,
                covers_scope: bool | None = None) -> Result[Ticket, TicketError]
    # Enforces the state machine; done additionally requires evidence
    # non-empty and a substantive Done report section (a bare heading with
    # nothing under it no longer counts, T-0398 D-03). `covers_scope`
    # (T-0398 D-02), when the caller supplies `False`, additionally
    # requires the ticket's evidence to bind to a touched/scope symbol
    # (Err(EvidenceScopeUnbound)) -- computed via `frob.gates.
    # evidence_covers_scope`, injected rather than computed here so
    # frob.tickets stays free of the frob.graph dependency that would pull
    # in (docs/rework.md cycle-avoidance); `covers_scope=None` (default)
    # skips the check.
def record_failure(root: Path, ticket_id: str, entry: FailureEntry) -> Result[Ticket, TicketError]
    # Appends to the failure log so no future session retries a dead end.
def attach(root: Path, ticket_id: str, source: AttachmentSource,
           caption: str) -> Result[Attachment, AttachError]
    # source is a file path or clipboard; stores under tickets/attachments/.
def add_evidence(root: Path, ticket_id: str, node_ids: Sequence[str],
                  collected: frozenset[str] | None = None,
                  passed: frozenset[str] | None = None) -> Result[Ticket, TicketError]
    # Validates node_ids against `collected` (frob.testing.collect_python_tests
    # node ids, supplied by the caller) and appends the resolvable ones;
    # rejects the whole batch as Err(UnknownEvidence) if any id is
    # unresolvable -- closes the COV003-after-close gap at write time.
    # T-0398 D-01: `passed` (the subset the caller has actually observed
    # PASS on a real run, e.g. via frob.testing.run_selected) is checked
    # the same way -- a non-cmd id absent from `passed` rejects the whole
    # batch as Err(EvidenceNotPassing), so a collected-but-currently-
    # FAILING test can never become evidence. `passed=None` (default)
    # skips this check.
def run_cmd_evidence(command: str) -> Result[str, TicketError]
    # T-0215: runs `command` through the shell and folds exit status + a
    # stdout digest into one evidence string (`cmd:<command> exit=0
    # sha256=<12-hex>`); Err(EvidenceCmdFailed) on nonzero exit or launch
    # failure.
def reverify_cmd_evidence(entry: str) -> Result[bool, TicketError]
    # T-0398 D-10: re-runs the command a `cmd:` evidence entry recorded and
    # confirms it still exits 0 with the SAME stdout sha256 -- Ok(True)/
    # Ok(False) report whether it reproduces; Err(MalformedEvidence) if
    # `entry` is not a well-formed cmd: entry. Deliberately opt-in, not
    # wired into COV003 by default (re-running an arbitrary recorded
    # command on every check has a real cost/non-idempotence tradeoff
    # `_evidence_valid_for_ticket` already documents choosing not to pay
    # unconditionally).
def add_cmd_evidence(root: Path, ticket_id: str, command: str) -> Result[Ticket, TicketError]
    # T-0215: kind-gated non-pytest evidence channel for tickets with no
    # pytest surface of their own -- only kind=docs may use it
    # (Err(EvidenceKindNotAllowed) otherwise); records `run_cmd_evidence`'s
    # entry via the same write path as add_evidence.
def migrate(root: Path) -> Result[int, TicketError]
    # Collapses legacy tickets/*.md files into the single tickets.md ledger.
def renumber(root: Path) -> Result[int, TicketError]
    # Reassigns EVERY ticket id to a contiguous T-0001.. sequence (whole-
    # ledger cleanup); superseded for the single-id case by renumber_one.
def renumber_one(root: Path, old_id: str, new_id: str, *,
                  dry_run: bool = False) -> Result[RenumberReport, TicketError]
    # Rewrites ONE ticket's id everywhere: its ledger section (active or
    # archive) plus every blocked_by/parent reference across BOTH stores,
    # plus every frob:ticket/frob:waive/frob:todo/frob:tests/frob:invariant/
    # frob:doc directive line across the tracked tree that names it.
    # `frob ticket renumber <old> <new>`'s implementation; --dry-run reports
    # the same plan without writing. See "Provisional ids" below.
def finalize_draft(root: Path, draft_id: str) -> Result[str, TicketError]
    # Assigns draft_id its final T-#### id against the CURRENT merged view
    # and rewrites everything via renumber_one; a no-op returning draft_id
    # unchanged if it is already final. The callable finalize step T-0176
    # (`frob ticket land`) will invoke at merge time.
def archive(root: Path) -> Result[int, TicketError]
    # Moves every done/dropped ticket from the active store into
    # tickets-archive.md verbatim (same section format); idempotent.
def set_done_report(root: Path, ticket_id: str, *, why: str,
                     base_ref: str = "main") -> Result[Ticket, TicketError]
    # T-0458: THE single write path for a ticket's Done report. `why` is
    # the ONLY thing the caller supplies -- Changed (compute_changed_lines,
    # git diff --stat vs base_ref) and Evidence (render_evidence_block,
    # from the ticket's own recorded evidence) are always auto-composed and
    # spliced into body's '## Done report' section via
    # replace_done_report_section (frob.tickets._models), so a caller never
    # parses or edits markdown, and can never hand-type a Changed/Evidence
    # list that drifts from what actually shipped. Held under ledger_lock
    # end to end. Example:
    #   set_done_report(root, "T-0458", why="implemented the thing")
    #   # -> Ok(Ticket(... body="## Done report\n\nimplemented the thing\n\n
    #   #     ### Changed\n```\nsrc/x.py | 3 ++-\n```\n\n### Evidence\n
    #   #     - `tests/x.py::test_y` (pytest node id, verified passing
    #   #     when recorded)\n"))
def compose_done_report(why: str, changed_lines: Sequence[str],
                         evidence: Sequence[str]) -> str
    # T-0458: pure composition -- why plus render_changed_block(changed_lines)
    # and render_evidence_block(evidence) folded into one '## Done report'
    # section string. set_done_report's only caller; exposed separately so
    # a caller that already has git/evidence data in hand can render
    # without touching the store.
def render_evidence_block(evidence: Sequence[str]) -> str
    # T-0458: renders a ticket's evidence tuple as-is -- no fresh
    # collection or test run needed, since every id in `evidence` was
    # ALREADY validated resolvable-and-passing (add_evidence's D-01 check)
    # or exit=0 (cmd: entries) at record time. "(no evidence recorded)" if
    # empty.
def render_changed_block(lines: Sequence[str]) -> str
    # T-0458: fences compute_changed_lines's output verbatim (git --stat
    # output is already human-readable columns). "(no changed files
    # detected)" if empty.
def compute_changed_lines(root: Path, base_ref: str = "main") -> tuple[str, ...]
    # T-0458: best-effort `git diff --stat <base_ref>...HEAD` lines for the
    # Changed section -- pulled from git, never hand-typed. Returns an
    # empty tuple (never raises) if root is not a git checkout or the diff
    # fails; the Changed block is auxiliary evidence, not a write
    # precondition.

# frob/tickets/clipboard.py
def clipboard_image() -> Result[bytes, ClipboardError]
    # PNG bytes from the platform clipboard, via the first working backend.
def clipboard_has_image() -> bool
    # Cheap probe used to decide whether to offer the interactive prompt.
```

## Scope-lease model (T-0453)

`frob ticket doable` does not just filter on blockers -- by default it also
excludes any queued/planned candidate whose declared `scope` overlaps an
IN-PROGRESS ticket's active scope-LEASE, so two agents dispatched straight
off `doable` can never collide on the same files. This replaces hand-
maintained collision blocklists a coordinator would otherwise have to build
and update on every dispatch.

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
  `frob.toml` (default 25) gets a `large_glob_warnings` nudge surfaced
  alongside `frob ticket doable` output -- narrow the scope to the specific
  files the ticket actually touches. This is a NUDGE, not a hard gate: it
  fixes over-hiding at the scope-DECLARATION level instead of ignoring
  broad directories in the overlap check itself.
- **Over-broad-lease demotion**: when a repo root is available (the CLI
  path always has one), a HOLDER's over-broad scope entries -- the exact
  same breadth test the warning uses -- are dropped before the overlap
  check, so one repo-wide in-progress lease (e.g. a `src/frob/**` coverage
  burn-down ticket) demotes to warn-only instead of zeroing out `doable`
  for every other ticket in the repo. A PRECISE entry on the same holder
  (e.g. `src/frob/gates/`) still hard-blocks a real collision under it.
  Callers with no repo root (`root=None`) get the strict, undemoted check.

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
when an in-progress ticket's scope changes, so it never drifts from the
ledger's own `state:`/`scope:` fields, which remain the sole source of
truth for anything the local `tickets.md` already knows about.

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

## Scope/lease change protocol (T-0455)

`frob ticket scope <id> --add GLOB... --remove GLOB... --reason TEXT`
formally expands or reduces a ticket's declared `scope` -- and, since the
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
  hand-edit of `tickets.md`.
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
- **Example** (the T-0446 new-subcommand scope gap, formalized): a ticket
  scoped to `src/frob/tickets/**` that needs to register a new CLI
  subcommand runs `frob ticket scope T-#### --add src/frob/__main__.py
  --reason "new subcommand registration"` instead of `frob:waive SCOPE001
  reason="... T-0176/T-0220 precedent"`.

## State machine

```
queued -> planned -> in-progress -> done
   |         |            |-> blocked -> in-progress
   |         |            |-> queued        (yield: agent gives it back)
   +---------+------------+-> dropped      (explicit, with reason in body)
```

Any other transition is `Err(InvalidTransition)`. `done` and `dropped` are
terminal. Cutting scope is `dropped` with a reason -- recorded, not deleted.

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

## `frob ticket land`

<!-- frob:describes src/frob/tickets/_land.py::land -->
<!-- frob:describes src/frob/tickets/_land.py::splice_ledger -->
<!-- frob:describes src/frob/tickets/_land.py::_assert_land_complete -->
<!-- frob:describes src/frob/tickets/_land.py::_worktree_full_changeset -->

The landing procedure used to be manual coordinator surgery repeated per
ticket: wip-commit in the worktree, merge main into it, a deletion-filter
check, squash-apply onto main, a ledger splice on conflict, close, a
conventional commit. `frob ticket land <id> --worktree <path> [--dry-run]`
(`frob.tickets.land`) does the whole chain atomically:

```python
# frob/tickets/_land.py
def land(root: Path, ticket_id: str, worktree: Path, *,
         dry_run: bool = False,
         collected: frozenset[str] | None = None,
         passed: frozenset[str] | None = None,
         covers_scope: bool | None = None) -> Result[LandReport, LandError]
    # T-0398 D-05: `collected`/`passed`/`covers_scope`, when supplied by a
    # caller with a fresh test-collection/run/graph-binding oracle computed
    # against the POST-MERGE worktree tree, re-verify the ticket's evidence
    # (resolution, pass, scope-binding) BEFORE finalize/close -- `land`
    # previously trusted whatever the worktree's pre-merge report claimed
    # and re-ran nothing. All three default to `None` (skip, unchanged
    # behavior) since computing them needs frob.testing/frob.graph access
    # frob.tickets deliberately does not have.
def splice_ledger(ours_text: str, theirs_text: str) -> Result[str, TicketError]
    # Merge two tickets.md texts at the TICKET-ID level (newest state per
    # id wins) instead of git's line-level textual merge. T-0398 D-09: the
    # winning side's evidence is UNIONED with the losing side's (never
    # dropped) on a same-id divergence.
```

Order of operations, and why it is this order:

1. **Refuse on a dirty `root`** (`git status --porcelain` non-empty) --
   `Err(DirtyMain)`, remedy: `git -C <root> status`, commit or stash.
2. **Validate close preconditions in the worktree FIRST** (evidence
   non-empty, a substantive `## Done report` section, T-0398 D-03) --
   `Err(NotCloseable)` here means NOTHING has been merged or committed
   anywhere yet. This ordering is the whole point: closing is the step
   most likely to be forgotten, and it is checked before any irreversible
   git operation, not after the merge has already landed. This is a
   PRE-merge check against the worktree's own report; see step 5.5 below
   for the T-0398 D-05 POST-merge re-verification.
3. **wip-commit** any uncommitted worktree changes (`wip: pre-land snapshot
   for <id>`) so nothing an agent forgot to commit is silently dropped by
   the merge that follows.
4. **Merge main into the worktree** (`git merge --no-commit --no-ff`,
   staged, not committed). Any conflict outside `tickets.md` aborts loudly
   (`Err(MergeConflict)`, remedy: resolve manually in the worktree, commit,
   retry). A `tickets.md` conflict is ALWAYS resolved via `splice_ledger`
   (see below), never git's line-level algorithm, then the merge is
   completed with a `merge <main> into worktree for landing <id>` commit.
5. **Deletion-filter check** (the stale-base guard): `git diff <main>
   --diff-filter=D --name-only` in the now-merged worktree -- every deleted
   path must match the ticket's `scope` globs, or land refuses loudly
   (`Err(UnownedDeletions)`, remedy: add the path(s) to scope if
   intentional, or `git checkout <main> -- <path>` in the worktree if
   accidental) and unwinds the merge (`git merge --abort`) first. This is
   what catches a worktree branched from a stale main base that ends up,
   relative to main's CURRENT tip, silently deleting a feature main already
   landed. T-0398 D-12: the deletion filter is STRICTER than an ordinary
   `scope_matches` check here -- a scope glob broad enough to be "the
   whole tree" or a bare top-level directory (`.`, `src/`) is never
   trusted to authorize a deletion (`_deletion_owned`), even though it
   would satisfy `scope_matches` for every other purpose; a more specific
   glob (`src/frob/tickets/`) is still trusted.
5.5. **Re-verify evidence against the POST-MERGE tree** (T-0398 D-05, only
   when the caller supplied `collected`/`passed`/`covers_scope`): reload
   the ticket from the worktree's now-merged ledger and re-check
   resolution/pass -- the ledger state about to be finalized may differ
   from what step 2 validated pre-merge (a splice can rewrite
   `ticket.evidence`). Runs BEFORE the `--dry-run` early return in step 6,
   so a clean dry run is still a real guarantee under D-05 too.
6. **`--dry-run` stops here**, unwinding the staged merge (`merge --abort`)
   -- everything above this point has ACTUALLY run (real merge, real
   splice, real deletion diff), so a clean dry run is a guarantee, not a
   guess. Nothing below this point (finalize/close/squash-apply/commit) is
   simulated, because nothing below it can fail for a reason the checks
   above didn't already catch.
7. **Finalize a draft id** (`finalize_draft`, T-0162's mechanism) if
   `ticket_id` is a `T-draft-*` id -- against the worktree's now-merged
   view, so the final id is allocated against current reality, not a stale
   pre-merge snapshot.
8. **Close** (`transition(..., DONE)`) in the worktree.
9. **Squash-apply onto `root`**: `git merge --squash --no-commit
   <worktree-branch>`. Any conflict outside `tickets.md` aborts loudly
   (`Err(SquashConflict)`, remedy: resolve manually, commit, retry) and
   resets `root` (`git reset --hard && git clean -fd`) back to exactly how
   it was found. `tickets.md` is again ALWAYS resolved via `splice_ledger`
   -- this is what makes the "main and the worktree each independently
   appended a new ticket near the same line" case a clean merge instead of
   a textual conflict requiring a human.
9.5. **Completeness assertion** (T-0463, BEFORE the commit in step 10): the
    worktree's finalized branch is diffed against `main` (`git diff
    --name-only <main>...HEAD` in the worktree) to get the COMPLETE
    changeset it introduces -- tracked edits, untracked new files, AND
    deletions all show up in this one call, because step 3's wip-commit
    already turned every untracked/deleted path into a tracked commit on
    the branch. This set is compared against what step 9 actually staged
    in `root` (`git diff --cached --name-only`); anything present in the
    worktree's changeset but missing from staging aborts the land loudly
    (`Err(IncompleteLand)`, the exact missing paths logged) and unwinds the
    squash (`git reset --hard && git clean -fd`) -- the commit in step 10
    never happens. This is the fix for the T-0448 incident: a manual
    coordinator land done via a raw `git diff HEAD` / patch-apply (NOT
    `frob ticket land`) only ever sees tracked deltas against the current
    commit, so it silently dropped an untracked `docs/modules/render.md`
    with no error at all. `frob ticket land`'s wip-commit + real `git
    merge --squash` design was already structurally immune to that
    specific failure mode; this step makes the immunity a checked
    invariant instead of an assumption, and is what actually catches any
    OTHER way a file could go missing (a git bug, a future refactor that
    reintroduces a diff-based step, etc.). The verified changeset is
    reported back as `LandReport.worktree_changeset`, and the actually
    landed paths as `LandReport.files_changed` -- on a real (non-dry-run)
    success the former is always a subset of the latter, by construction.
10. **Commit** with a conventional-commit message template
    (`<type>(tickets): land <final-id> <title>`, type derived from
    `ticket.kind`; `feature`->`feat`, `bug`/`security`/`ux`/`incident`->
    `fix`, `docs`->`docs`, `invariant`->`test`). ASCII only, no
    `Co-Authored-By` line, matching repo convention.

If close (step 8) fails or the final commit (step 10) fails, the merge
commit already landed in the WORKTREE's own branch history (never in
`root`/main) -- the log line names the exact undo (`git -C <worktree>
reset --hard HEAD~1`) alongside the retry instruction, so a failed landing
is always recoverable without touching main.

`splice_ledger` never trusts git's line-level merge for `tickets.md`:
it parses both ledger texts into id -> Ticket maps and unions them,
picking the "newer" version on a genuine same-id divergence -- state-machine
rank first (done/dropped > in-progress/blocked > planned > queued), then
presence of a substantive Done report, then the incoming side as the final
deterministic tiebreak. A ticket id present on only one side is always
kept. T-0398 D-09: whichever side wins the tiebreak has its evidence
UNIONED with the losing side's (deduplicated, winner's own ids first),
never dropped -- previously an evidence-count tiebreak picked ONE side's
evidence set wholesale, silently discarding the other side's ids when two
worktrees closed the same ticket with disjoint evidence.

## Git merge driver

<!-- frob:describes src/frob/app/ticket_runner.py::_merge_driver -->

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
git config merge.frob-ledger.driver "frob ticket merge-driver %O %A %B"
```

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

1. reads `%A` and `%B`'s text,
2. calls the SAME `splice_ledger(ours_text, theirs_text,
   archived_ids=...)` `frob ticket land` uses (never a separate
   reimplementation -- one splice algorithm, two call sites),
3. overwrites `%A` with the result and exits 0 (git records a clean,
   non-conflicted merge).

`%O` (the merge base) is accepted, since git always supplies it, but
unused: `splice_ledger` resolves same-id divergence via state-rank
(done/dropped > in-progress/blocked > planned > queued) and Done-report
presence over `ours`/`theirs` directly, not a 3-way base diff -- see
`splice_ledger`'s own docs above for why a base-aware 3-way diff is not
the right model for an append-mostly, id-keyed ledger.

If `splice_ledger` itself fails (a genuinely malformed `%A`/`%B`, not just
a same-id divergence -- that case always resolves), the driver leaves
`%A` untouched and exits 1: git then reports the ordinary conflict for a
human to resolve by hand, exactly as if no driver were registered. A
merge driver can never turn a real parse failure into a silently-wrong
splice.

## Clipboard capture

`frob ticket new` offers clipboard paste only when stdin is a TTY and
`clipboard_has_image()` is true; non-interactive callers (agents, CI) must
pass explicit file paths -- prompts never block automation.

`frob ticket attach <id>` with no path argument means "read from the
clipboard" -- but a non-interactive session (agent, CI) has no clipboard to
paste from. Before attempting any clipboard backend, the CLI checks
`sys.stdin.isatty()`; off a TTY it fails fast with `Err`-style remedy text
("pass an explicit file path: frob ticket attach <id> <path>") instead of
spawning a clipboard backend that can never produce an image (T-0098). This
check lives in `frob.app.ticket_runner._attach`, not `frob.tickets.attach`
-- the library function stays a pure "copy these bytes" primitive; the CLI
is what decides whether to offer or refuse the clipboard.

Backend probe order (first available wins):

| Backend | Platform | Probe |
|---|---|---|
| `wl-paste -t image/png` | Wayland | `WAYLAND_DISPLAY` set, binary on PATH |
| `xclip -selection clipboard -t image/png -o` | X11 | `DISPLAY` set, binary on PATH |
| `powershell.exe Get-Clipboard -Format Image` (via temp file) | WSL | `/proc/version` contains microsoft |
| `pngpaste -` / `osascript` fallback | macOS | `sys.platform == "darwin"` |

Every backend invocation and failure is logged; no backend -> 
`Err(ClipboardError.NoBackend)` with the probe report in the message.

## Data models

All pydantic `BaseModel`; `Ticket` is frozen (mutation = write + reload).

```python
class TicketState(StrEnum):
    QUEUED = "queued"; PLANNED = "planned"; IN_PROGRESS = "in-progress"
    BLOCKED = "blocked"; DONE = "done"; DROPPED = "dropped"

class TicketKind(StrEnum):
    FEATURE = "feature"; BUG = "bug"; SECURITY = "security"
    UX = "ux"; DOCS = "docs"; INVARIANT = "invariant"

class Origin(StrEnum):
    HUMAN = "human"; AGENT = "agent"; AUDITOR = "auditor"

class Stride(StrEnum):          # STRIDE threat category, kind=security only
    SPOOFING = "spoofing"; TAMPERING = "tampering"
    REPUDIATION = "repudiation"; INFO_DISCLOSURE = "info-disclosure"
    DENIAL_OF_SERVICE = "denial-of-service"
    ELEVATION_OF_PRIVILEGE = "elevation-of-privilege"

class Attachment(BaseModel):
    path: str                   # relative to tickets/
    caption: str
    sha256: str                 # integrity: gate flags missing/moved files

class FailureEntry(BaseModel):
    date: date
    attempt: int
    summary: str                # WHY it failed, one line minimum

class Ticket(BaseModel):
    id: str                     # ^T-\d{4}$
    title: str
    state: TicketState
    kind: TicketKind
    origin: Origin
    created: date
    blocked_by: tuple[str, ...]
    parent: str | None
    scope: tuple[str, ...]      # path globs and/or symrefs
    evidence: tuple[str, ...]   # pytest node ids or policy rule ids
    attachments: tuple[Attachment, ...]
    body: str                   # markdown after frontmatter, verbatim

class TicketSpec(BaseModel):    # input to new_ticket; id/created assigned
    title: str
    kind: TicketKind
    origin: Origin
    scope: tuple[str, ...] = ()
    blocked_by: tuple[str, ...] = ()
    parent: str | None = None
    body: str = ""

class TicketQueue(BaseModel):
    tickets: Mapping[str, Ticket]

class AttachmentSource(BaseModel):
    path: Path | None           # None means clipboard
```

## Error types

```python
class TicketError(ErrorSet):
    NotFound            = "No ticket with that id"
    DuplicateId         = "Ticket id already exists"
    MalformedFrontmatter = "Ticket file failed schema validation"
    InvalidTransition   = "State change not allowed by the state machine"
    MissingEvidence     = "done requires evidence and a Done report"
    BlockerOpen         = "Cannot start: blocked_by contains open tickets"
    WriteFailed         = "Atomic ticket write failed"
    UnknownEvidence     = "Evidence id does not resolve to a collected test"
    EvidenceKindNotAllowed = "cmd evidence is only allowed for docs-kind tickets"
    EvidenceCmdFailed   = "evidence command failed to launch or exited nonzero"

class ClipboardError(ErrorSet):
    NoBackend     = "No clipboard backend available on this platform"
    NoImage       = "Clipboard does not contain an image"
    BackendFailed = "Clipboard backend exited nonzero"

AttachError = TicketError | ClipboardError
```

## Storage internals

<!-- frob:describes src/frob/tickets/_store.py::slugify -->
<!-- frob:describes src/frob/tickets/_store.py::tickets_dir -->
<!-- frob:describes src/frob/tickets/_store.py::ledger_path -->
<!-- frob:describes src/frob/tickets/_store.py::archive_path -->
<!-- frob:describes src/frob/tickets/_store.py::load_archive -->
<!-- frob:describes src/frob/tickets/_store.py::write_archive -->
<!-- frob:describes src/frob/tickets/_store.py::attachments_dir -->
<!-- frob:describes src/frob/tickets/_store.py::_store_mode -->
<!-- frob:describes src/frob/tickets/_store.py::_serialize_ticket -->
<!-- frob:describes src/frob/tickets/_store.py::_parse_ticket_file -->
<!-- frob:describes src/frob/tickets/_store.py::load_all -->
<!-- frob:describes src/frob/tickets/_store.py::write_ticket -->
<!-- frob:describes src/frob/tickets/_store.py::write_all -->
<!-- frob:describes src/frob/tickets/_store.py::migrate_to_ledger -->
<!-- frob:describes src/frob/tickets/_store.py::atomic_write -->
<!-- frob:describes src/frob/tickets/_store.py::ledger_lock -->
<!-- frob:describes src/frob/tickets/_store.py::lock_path -->

`frob/tickets/_store.py` implements the single-file-ledger-vs-legacy-dir
backend switch described under Storage above; `frob/tickets/__init__.py`
(the Public API) is the only caller.

```python
# frob/tickets/_store.py
def slugify(title: str) -> str
    # Lowercase, hyphenate, strip non-alnum runs -- the tickets/T-####-slug.md
    # filename fragment for a ticket title.
def tickets_dir(root: Path) -> Path
    # The legacy tickets/ directory (also holds attachments in single mode).
def ledger_path(root: Path) -> Path
    # The single-file tickets.md ledger path at the repo root.
def archive_path(root: Path) -> Path
    # The tickets-archive.md path at the repo root (same ledger format).
def load_archive(root: Path) -> Result[dict[str, Ticket], TicketError]
    # Every ticket in tickets-archive.md (empty dict if it doesn't exist yet).
def write_archive(root: Path, tickets: dict[str, Ticket]) -> Result[None, TicketError]
    # Replaces tickets-archive.md wholesale (same ledger section format,
    # distinct header).
def attachments_dir(root: Path, ticket_id: str) -> Path
    # tickets/attachments/<id>/ for a given ticket (both storage modes).
def store_mode(root: Path) -> str
    # Which backend a repo uses: 'single' if tickets.md exists, 'dir' if
    # only legacy tickets/*.md files exist, else 'single' (fresh-repo default).
def serialize_ticket(ticket: Ticket) -> str
    # Renders a Ticket to legacy ---frontmatter + body (dir-mode file text).
def parse_ticket_file(path: Path) -> Result[Ticket, TicketError]
    # Splits a legacy ticket file into frontmatter + body and validates it.
def load_all(root: Path) -> Result[dict[str, Ticket], TicketError]
    # Every ticket in the repo as an id -> Ticket map, backend-agnostic.
def write_ticket(root: Path, ticket: Ticket) -> Result[None, TicketError]
    # Upserts one ticket into whichever backend the repo uses (atomic).
def write_all(root: Path, tickets: dict[str, Ticket]) -> Result[None, TicketError]
    # Replaces the ENTIRE store with `tickets` (used by renumber); single
    # mode rewrites the ledger wholesale, dir mode writes each file and
    # deletes any T-*.md whose id is no longer present.
def migrate_to_ledger(root: Path) -> Result[int, TicketError]
    # Collapses a legacy tickets/*.md layout into a single tickets.md ledger,
    # deleting the source files after a successful write.
def atomic_write(path: Path, content: str | bytes) -> Result[None, TicketError]
    # Writes via temp file + os.replace in the same directory (crash-safe);
    # the one write primitive both storage backends funnel through.
def lock_path(root: Path) -> Path
    # T-0458: the advisory lock file path (.frob/tickets.lock) ledger_lock
    # holds -- root / ".frob" / "tickets.lock".
def ledger_lock(root: Path) -> Iterator[None]
    # T-0458: exclusive, blocking, cross-process lock (fcntl.flock on
    # lock_path(root)) serializing EVERY ledger mutation -- write_ticket,
    # write_all, write_archive all acquire it around their own load-then-
    # write, and new_ticket wraps its id-allocation + write in one outer
    # hold so allocation and the claiming write can never be observed by a
    # concurrent writer in between (the T-0465 duplicate-id race this
    # closes). Re-entrant per thread (a nested `with ledger_lock(root):` in
    # the SAME thread is a no-op re-entry, not a deadlock) so a locked
    # primitive called from inside an already-locked caller is safe;
    # cross-thread/cross-process callers still block on the real OS lock.
    # Degrades to a documented, logged no-op on a platform without fcntl
    # (non-POSIX; a real cross-platform primitive is T-0458's named
    # phase-2 daemon-pipe follow-up). Example:
    #   with ledger_lock(root):
    #       ticket_id = _allocate_and_check_ticket_id(root)  # read max id
    #       write_ticket(root, ticket)                       # claim it
    #   # no concurrent new_ticket() call can observe the pre-write state
    #   # in between -- the whole allocate+claim sequence is atomic.
```

## Design decisions

- **Markdown + frontmatter, one file per ticket.** Mergeable, reviewable,
  editable by human and agent alike. SQLite/JSON store rejected: the queue
  is the human/AI collaboration surface and must diff cleanly.
- **Attachments live in the repo.** Mockups are small; `attach` warns above
  1 MB and re-encodes nothing. git-lfs rejected for alpha (setup friction
  beats storage cost at this scale). sha256 recorded so the coverage gate
  can flag missing or silently-replaced images.
- **Hard-fail on malformed tickets.** A best-effort queue would let a typo
  silently hide a ticket -- the exact failure mode this system exists to
  kill.
- **Failure log is append-only memory.** Cheap cross-session "tried X,
  failed because Y" -- the useful slice of the memory-layer market, for free.
- **Sequential ids with collision check** (`T-0042`). UUIDs rejected:
  unreadable in conversation and in `frob:ticket` directives.
- **Provisional draft ids off the default branch, finalized at land**
  (T-0162). Sequential allocation across independent checkouts/worktrees
  cannot be made collision-safe without either coordination (rejected --
  agents file tickets from worktrees constantly and must never need to ask
  a human "is T-0157 taken?") or a disjoint id space per checkout until
  merge. See "Decision record: T-0162" above for the full comparison.

## Dependencies

- `pydantic`, `typani`; stdlib `subprocess` (clipboard, T-0215 cmd
  evidence), `hashlib`, `date`.
- PyYAML (frontmatter) -- already transitively present; pinned direct.
- No dependency on `frob.graph` (gates join the two; see `docs/rework.md`).

## Integration points

- `frob.gates`: scope gate reads `scope`, coverage gate reads `evidence`
  and joins `frob:ticket`/`frob:todo` edge targets against the queue.
  `tickets_gate` (TICK001/TICK002, T-0162) checks the id-collision invariant
  -- see "Decision record: T-0162" above.
- CLI: `frob ticket new|list|show|doable|plan|start|requeue|sweep|migrate|
  renumber|attach|block|close|fail|evidence|done-report|archive`. `start`
  auto-plans a queued ticket (both legal steps); `requeue` is the reverse
  in-progress -> queued yield (T-0472); `sweep` re-records the pre-work
  sweep after a scope change; `migrate` collapses a legacy dir into the ledger;
  `renumber <old> <new> [--dry-run]` (T-0162) rewrites ONE ticket's id
  everywhere -- ledger plus every code directive reference -- the
  first-class replacement for the sed-by-hand that fixed the T-0157
  incident's ~100 stray waiver references; `renumber` with NO arguments
  keeps the older whole-ledger behavior (reassigns every id to a
  contiguous T-0001.. sequence, T-0012); `evidence <id> <pytest-node-id>...`
  validates each id against collected
  tests up front and appends to the structured evidence list (rejecting an
  unresolvable id with remedy text, instead of a typo silently surfacing
  later as COV003 after close); `archive` moves every done/dropped ticket
  from the active ledger into `tickets-archive.md`, verbatim.
- `new --evidence <id>...` and `close --evidence <id>...` (T-0106) route
  through the same `add_evidence` validation as the standalone `evidence`
  subcommand -- both are convenience flags, not a separate write path.
  `new --evidence` appends evidence to the just-created ticket after
  `new_ticket` succeeds; an unresolvable id there leaves the ticket
  created (creation already happened) but exits nonzero with no evidence
  attached. `close --evidence` applies evidence *before* the DONE
  transition and, on any unresolvable id, refuses the transition
  entirely -- a bad `--evidence` id can never close a ticket on
  unvalidated evidence.
- `evidence <id> [<pytest-node-id>...] [--evidence-cmd 'command']` and
  `close <id> [--evidence <id>...] [--evidence-cmd 'command']` (T-0215):
  the non-pytest evidence channel for docs-kind tickets that have no
  pytest surface of their own (pure doc/design work, where the old gate
  forced writing a drift-lock test purely to satisfy close). `--evidence-cmd`
  runs the given command, records its exit status and a stdout digest as
  one evidence entry, and is kind-gated -- `add_cmd_evidence` refuses with
  `Err(EvidenceKindNotAllowed)` for every kind except `docs`, so a
  bug/feature/security ticket can never close on a shell command's exit
  status alone; those kinds still require real pytest node ids via
  `--evidence`/`evidence`. A failing command (nonzero exit, or one that
  fails to launch) is `Err(EvidenceCmdFailed)` and never gets recorded.
- `done-report <id> (--why TEXT | --why-file PATH | stdin) [--base-ref REF]`
  (T-0458): atomically writes/updates a ticket's Done report via
  `set_done_report` -- the caller supplies ONLY the narrative why; the
  Changed section (`git diff --stat <base_ref>...HEAD`, default
  `base_ref=main`) and the Evidence section (rendered from the ticket's
  own recorded evidence ids) are always auto-composed, never hand-typed.
  `--why -` (or omitting both `--why`/`--why-file`) reads the narrative
  from stdin. This is now the only supported way to set a Done report --
  never hand-edit the `## Done report` section in `tickets.md` directly.
  Example:
  ```
  frob ticket done-report T-0458 --why "implemented the thing"
  # or, from a file:
  frob ticket done-report T-0458 --why-file /tmp/report-why.md --base-ref main
  ```
- Close-failure hints (T-0215): closing a `queued`/`planned` ticket fails
  `InvalidTransition` with a message naming the remedy (`frob ticket start
  <id>`); closing without evidence or a Done report fails
  `MissingEvidence` with a message naming where the Done report belongs
  (a `## Done report` heading under the ticket's own section in
  `tickets.md`). `frob ticket start` on an already-in-progress ticket is a
  hard error naming `frob ticket sweep <id>` as the refresh path, not a
  silent idempotent no-op -- `sweep` already exists as that mechanism, so a
  second entry point doing the same thing would just be duplication.
- **Instant start (T-0474)**: `frob ticket start` is just the state
  transition by default -- the pre-work sweep (dup scan + xref + scope
  digest) is launched as a DETACHED background process
  (`subprocess.Popen(..., start_new_session=True)`) rather than run
  synchronously, so `start` no longer blocks for however long the sweep
  takes on a large repo. `--foreground` opts back into the old, fully
  synchronous behavior (the sweep completes before `start` returns) --
  useful for a script that wants the sweep guaranteed recorded
  immediately. `frob ticket sweep <id>` is unaffected either way: it
  always runs synchronously, so PRE001 stays satisfiable on demand
  regardless of whether `start`'s own background launch has landed yet. A
  spawn failure (e.g. `subprocess.Popen` refused by a locked-down sandbox)
  falls back to running the sweep synchronously right there -- `start`
  never silently skips recording a sweep, only ever trades "instant" for
  "eventually".

Ticket kinds: feature, bug, security, ux, docs, invariant, incident.
- `--kind incident` seeds a blameless-postmortem body template (Summary,
  Timeline, Root cause, Action items -- each action item becomes a ticket).
- `--acceptance "given/when/then"` (repeatable) records criteria the
  reviewer agent verifies against the diff before close.
- `--threat` sets a STRIDE category (spoofing/tampering/repudiation/
  info-disclosure/denial-of-service/elevation-of-privilege) on a security
  ticket, so the security-auditor can organize sweeps by category.
- Agents: planner emits ticket trees; implementer starts/closes tickets and
  writes done-reports; auditors file tickets with `origin: auditor`.

## Agent workflow implications (T-0162)

Agents file tickets from worktrees constantly -- a single working session
can spawn several parallel worktrees, each filing its own tickets, with no
opportunity (and no need) to coordinate with sibling sessions. T-0162's
provisional-id mechanism is designed around that reality, not against it:

- **Filing from a worktree/feature branch is always safe, unconditionally.**
  `frob ticket new` off the default branch always mints a `T-draft-<hex>`
  id and never touches sequential allocation, so nothing an agent does in
  one worktree can collide with what any other agent or the human is doing
  in a sibling worktree, main, or a not-yet-fetched remote branch. No
  "check first," no "ask the human," no retry-on-conflict loop needed.
- **A draft id is a real, usable ticket id in the meantime.** It resolves in
  `frob ticket show`/`start`/`close`, participates in `blocked_by`/`parent`
  edges, and works in `frob:ticket`/`frob:waive`/`frob:todo` directives
  exactly like a final id -- an agent should use it immediately, not wait
  for finalization before referencing it in code or in the Done report.
- **Do not hand-renumber a draft id.** If a draft id looks awkward in
  conversation, do NOT sed it or hand-edit the ledger -- use
  `frob ticket renumber <draft-id> <new-id> [--dry-run]`, which is the only
  path guaranteed to rewrite every directive reference atomically. This is
  exactly the discipline that fixed the T-0157 incident's ~100 stray
  references; doing it by hand is how that incident happened in the first
  place.
- **Finalization is automatic through `frob ticket land`.** A draft id is
  finalized to its permanent sequential id only once it has actually
  landed on the default branch, via `finalize_draft` -- `frob ticket land`
  (T-0176) calls it automatically as part of its atomic merge/land step.
  An agent landing its own worktree's changes onto main by hand (not via
  `land`) should still call `frob ticket renumber <draft-id> <T-####>`
  right after the merge, before closing out; `frob check`'s TICK002 rule
  will refuse to pass silently if this is forgotten (draft ids are
  unwaivable on the default branch).
- **A draft id surviving a merge into the default branch is a hard-fail,
  not a warning.** `frob check` (TICK002) makes this loud on purpose --
  see "Why TICK001/TICK002 are unwaivable" above. Treat a TICK002 failure
  the same way as any other unwaivable gate failure: fix the root cause
  (finalize the draft), never suppress it.
