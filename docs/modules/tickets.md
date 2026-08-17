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

**T-1437: an id present in BOTH files is a self-healing collapse, not a
refusal.** Before T-1437, `archive` hard-refused with `Err(DuplicateId)`
the moment it found the SAME ticket id already in `tickets-archive.md`
while also being moved out of the active ledger -- a shape that could
arise from a stale ledger-driver splice (see the git-merge-driver
paragraph below) with no CLI path to repair; the only recovery was the
`docs/guides/agent-playbook.md` section 10b restore recipe. `archive` now
collapses that id to the archive's EXISTING copy (never overwritten) and
still drops it from the active ledger, returning the count of tickets
genuinely newly archived (the collapsed duplicate does not count).
`frob ticket archive` run again on a worktree that already has a stray
active/archive duplicate is therefore the repair step, not a dead end.

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
                               # T-1132: TicketSpec refuses an empty-string
                               # or non-T-####/T-draft-<hex> entry at
                               # `frob ticket new` construction time (the
                               # T-0380 incident); `frob ticket block <id>
                               # --by <other>` (the one CLI verb that
                               # appends to an EXISTING ticket's blocked_by)
                               # validates --by by hand for the same reason
                               # -- see is_valid_ticket_ref below and
                               # `frob doctor`'s malformed-edge scan for the
                               # read-side complement (an already-malformed
                               # entry in the ledger, from before this fix).
parent: T-0040                # hierarchy: planner decomposes goals into trees
scope:                        # blast radius for the scope gate
  - src/frob/tickets/**
  # frob:waive DOC006 reason="illustrative example ticket's scope list -- src/frob/app/ticket_runner.py became a package, but T-0042 here is a fabricated example ticket id, not a real one to keep current"
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

<!-- frob:describes src/frob/tickets/_archive.py::load_queue -->
<!-- frob:describes src/frob/tickets/_new_renumber.py::new_ticket -->
<!-- frob:describes src/frob/tickets/_doable.py::doable -->
<!-- frob:describes src/frob/tickets/_evidence.py::transition -->
<!-- frob:describes src/frob/tickets/_reporting.py::record_failure -->
<!-- frob:describes src/frob/tickets/_reporting_attachments.py::attach -->
<!-- frob:describes src/frob/tickets/_evidence.py::add_evidence -->
<!-- frob:describes src/frob/tickets/_evidence.py::run_cmd_evidence -->
<!-- frob:describes src/frob/tickets/_evidence.py::reverify_cmd_evidence -->
<!-- frob:describes src/frob/tickets/_evidence.py::add_cmd_evidence -->
<!-- frob:describes src/frob/tickets/clipboard.py::clipboard_image -->
<!-- frob:describes src/frob/tickets/clipboard.py::clipboard_has_image -->
<!-- frob:describes src/frob/tickets/_archive.py::migrate -->
<!-- frob:describes src/frob/tickets/_new_renumber.py::renumber -->
<!-- frob:describes src/frob/tickets/_new_renumber.py::renumber_one -->
<!-- frob:describes src/frob/tickets/_draft_finalize.py::finalize_draft -->
<!-- frob:describes src/frob/tickets/_archive.py::archive -->
<!-- frob:describes src/frob/tickets/_archive.py::load_active -->
<!-- frob:describes src/frob/tickets/_provisional.py::on_default_branch -->
<!-- frob:describes src/frob/tickets/_provisional.py::mint_draft_id -->
<!-- frob:describes src/frob/tickets/_doable.py::doable_blocked -->
<!-- frob:describes src/frob/tickets/_doable.py::leased_by -->
<!-- frob:describes src/frob/tickets/_doable.py::large_glob_warnings -->
<!-- frob:describes src/frob/tickets/_models.py::scope_overlap -->
<!-- frob:describes src/frob/tickets/_models.py::scope_overlap_globs -->
<!-- frob:describes src/frob/tickets/_reporting.py::set_done_report -->
<!-- frob:describes src/frob/tickets/_evidence.py::reverify_close_guard -->
<!-- frob:describes src/frob/tickets/_models.py::recover_done_report_why -->
<!-- frob:describes src/frob/tickets/_reporting.py::compose_done_report -->
<!-- frob:describes src/frob/tickets/_store.py::sanitize_narrative_for_ledger -->
<!-- frob:describes src/frob/tickets/_evidence.py::render_evidence_block -->
<!-- frob:describes src/frob/tickets/_evidence.py::replay_evidence_from_done_report -->
<!-- frob:describes src/frob/tickets/_evidence.py::render_changed_block -->
<!-- frob:describes src/frob/tickets/_evidence.py::compute_changed_lines -->
<!-- frob:describes src/frob/tickets/_evidence.py::base_ref_resolvable -->
<!-- frob:describes src/frob/tickets/_store.py::ledger_lock -->
<!-- frob:describes src/frob/tickets/_scope.py::mutate_scope -->
<!-- frob:describes src/frob/tickets/_setters.py::set_priority -->
<!-- frob:describes src/frob/tickets/__init__.py::_doable_sort_key -->
<!-- frob:describes src/frob/tickets/_setters.py::set_component -->
<!-- frob:describes src/frob/tickets/_setters.py::set_tier -->
<!-- frob:describes src/frob/tickets/_setters.py::set_runs_last -->
<!-- frob:describes src/frob/tickets/_setters.py::set_scope_breadth_ack -->
<!-- frob:describes src/frob/tickets/_reporting.py::mutate_labels -->
<!-- frob:describes src/frob/tickets/__init__.py::board_view -->
<!-- frob:describes src/frob/tickets/__init__.py::epic_rollup -->
<!-- frob:describes src/frob/tickets/_doable.py::has_live_lease -->
<!-- frob:describes src/frob/tickets/_doable.py::dispatch_stale_hours -->
<!-- frob:describes src/frob/tickets/_doable.py::undispatched_stale -->
<!-- frob:describes src/frob/tickets/_models.py::is_valid_ticket_ref -->
<!-- frob:describes src/frob/tickets/_doable.py::already_landed_markers -->
<!-- frob:describes src/frob/tickets/_doable.py::wave -->
<!-- frob:describes src/frob/tickets/_doable.py::WaveGroup -->
<!-- frob:describes src/frob/tickets/_doable.py::WaveResult -->
<!-- frob:describes src/frob/tickets/_doable.py::WaveRemainderReason -->
<!-- frob:describes src/frob/tickets/_land_git_ops.py::detect_duplicate_ticket_id_collisions -->

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
                collected: frozenset[str] | None = None,
                *, no_commit: bool = False) -> Result[Ticket, TicketError]
    # Allocates next id (T-####), writes file atomically. T-0398 D-08:
    # `collected`, when supplied, resolves spec.evidence the same way
    # add_evidence does (Err(UnknownEvidence) on a bogus id); `collected=None`
    # (default) preserves schema-only validation but now logs an explicit
    # UNRESOLVED warning instead of silently skipping the check. T-1758:
    # auto-commits the ledger write itself before returning (the write
    # BOUNDARY, not the CLI dispatch layer, now owns this guarantee) --
    # every caller, CLI or programmatic, gets a committed ledger with
    # nothing to remember; `no_commit=True` is the same opt-out
    # `commit_ticket_ledger_change` itself exposes, for a caller (the
    # `frob ticket new` CLI verb, to fold --evidence into one commit)
    # that wants to batch further ledger writes into a commit of its own.
def doable(queue: TicketQueue) -> tuple[Ticket, ...]
    # state in {queued, planned} and no open blockers, ordered by priority
    # (highest PRIORITY_RANK first, T-0411) then oldest-first within a tier.
def wave(queue: TicketQueue, root: Path | None = None, *, agents: int,
          ignore_lease: bool = False,
          breadth: tuple[int, tuple[str, ...]] | None = None) -> WaveResult
    # T-1738: partitions doable() into up to `agents` mutually scope-
    # DISJOINT WaveGroups -- the parallel analogue of doable's sequential
    # "what can ONE agent start right now" answer. Two tickets in the
    # SAME group may share scope (one agent works them in order, an
    # intra-group collision is not a race); two tickets in DIFFERENT
    # groups may never share scope, which is the property parallel
    # dispatch actually needs and that grouping by theme alone cannot
    # guarantee (the T-1699/T-1705, T-1679/T-1637 incidents this ticket's
    # own body cites). Packs doable()'s priority/age-ordered candidates
    # greedily, one at a time, into the first existing group whose scope
    # the candidate does not collide with (scope_overlap, the same
    # substrate doable's own lease filter uses); opens a fresh group (up
    # to `agents` total) only when no existing group can take it. A
    # candidate colliding with two or more ALREADY-separate groups is
    # unplaceable as scoped -- recorded in WaveResult.remainder (a
    # WaveRemainderReason naming the ticket, the first blocking group
    # index, the colliding ticket id, and the specific glob), never
    # dropped silently. `agents` is a hint, not a guarantee: returns
    # fewer, larger groups when the queue does not partition further
    # (a real, reportable finding in a repo where one doc path dominates
    # most tickets' scope), never pads a group with colliding work to hit
    # the requested count. Deterministic for a fixed queue state, since
    # doable()'s own ordering is deterministic and wave performs no
    # further reordering.
def set_priority(root: Path, ticket_id: str, priority: Priority) -> Result[Ticket, TicketError]
    # T-0411: `frob ticket priority <id> <level>` -- the accountable,
    # single-writer way to reprioritize a ticket instead of hand-editing
    # tickets.md frontmatter (same shape as mutate_scope/T-0455).
def transition(root: Path, ticket_id: str, to: TicketState, *,
                covers_scope: bool | None = None,
                reviewed: bool | None = None,
                mutation_evidence: bool | None = None,
                evidence_reverified: bool | None = None,
                own_obligations_clean: bool | None = None) -> Result[Ticket, TicketError]
    # Enforces the state machine; done additionally requires evidence
    # non-empty and a substantive Done report section (a bare heading with
    # nothing under it no longer counts, T-0398 D-03). `covers_scope`
    # (T-0398 D-02), when the caller supplies `False`, additionally
    # requires the ticket's evidence to bind to a touched/scope symbol
    # (Err(EvidenceScopeUnbound)) -- computed via `frob.gates.
    # evidence_covers_scope`, injected rather than computed here so
    # frob.tickets stays free of the frob.graph dependency that would pull
    # in (docs/rework.md cycle-avoidance); `covers_scope=None` (default)
    # skips the check. T-0572: done ALSO requires every acceptance
    # criterion to have a resolving evidence id -- see unbound_acceptance;
    # Err(AcceptanceUnbound) names which criteria are still unbound (in the
    # WARNING log line, not the bare error) if any remain. A ticket with an
    # empty `acceptance` list is unaffected (backward compat). T-0844:
    # `mutation_evidence`, when the caller supplies `False`, additionally
    # refuses on an unwaived ERROR-severity TEST016 confirmatory-only-
    # evidence finding (Err(EvidenceConfirmatoryOnly)) -- computed via
    # `frob.gates.mutation_evidence_violations`, injected for the same
    # cycle-avoidance reason as `covers_scope`; `mutation_evidence=None`
    # (default) skips the check. `frob ticket close` wires this the same
    # way `frob ticket land` already did (see "Mutation-evidence
    # obligation" below). T-0417 (round-2 audit N-02): `evidence_
    # reverified`, when the caller supplies `False`, additionally refuses
    # (Err(EvidenceNotPassing)) when a FRESH re-run of the ticket's own
    # non-cmd evidence against the CURRENT tree no longer passes --
    # closing must never trust the pass observation made once, back when
    # `frob ticket evidence` first recorded it. Computed via `frob.app.
    # ticket_runner._reverify_evidence_for_close`, the direct-close twin of
    # `land`'s own post-merge re-verify (`_reverify_evidence_post_merge`,
    # D-05); `evidence_reverified=None` (default) skips the check. T-1384:
    # `own_obligations_clean`, when the caller supplies `False`,
    # additionally refuses (Err(OwnObligationsUnclean)) while the ticket's
    # OWN diff leaves a new public symbol with no `frob:doc` edge, a new
    # public test class undeclared on its testsuite strata node, or a
    # changed public API with no REL001 bump -- the T-1377/T-1379/T-1381
    # residue class, where a `--ticket`-scoped close saw zero (those gate
    # families are repo-wide, not ticket-scoped) and the very next unscoped
    # `frob check` surfaced the closer's own findings as a surprise.
    # Computed the same cycle-avoidance way as `covers_scope`/
    # `mutation_evidence` above (the actual COV001/SELFAUDIT/REL001
    # evaluation needs `frob.gates`); `own_obligations_clean=None`
    # (default) skips the check -- the wiring that computes and injects a
    # real value from `frob ticket close`/`reverify` is a follow-up ticket,
    # not yet done as of this writing.
def unbound_acceptance(ticket: Ticket) -> tuple[AcceptanceCriterion, ...]
    # T-0572: acceptance criteria with no evidence id that both the
    # criterion itself lists AND still resolves against ticket.evidence --
    # the done-transition gate above. Always () for an empty acceptance
    # list. A criterion whose bound id was later dropped from
    # ticket.evidence reads as unbound again (the binding must hold NOW).
def record_failure(root: Path, ticket_id: str, entry: FailureEntry) -> Result[Ticket, TicketError]
    # Appends to the failure log so no future session retries a dead end.
    # T-1131: `record_failure` itself stays a pure append (no transition --
    # some callers log a historical failure retroactively on a ticket that
    # is not IN_PROGRESS). `frob ticket fail`'s CLI handler
    # (frob.app.ticket_runner._close_cmd._fail) is the one that ALSO
    # requeues (IN_PROGRESS -> QUEUED) whenever the ticket was IN_PROGRESS,
    # right after logging -- that transition is what actually releases the
    # cross-worktree lease (_sync_cross_worktree_lease only fires on a
    # transition call). Before T-1131, `frob ticket fail` never
    # transitioned at all, so a ticket fail-logged mid-flight stayed
    # IN_PROGRESS holding its lease forever (the T-1050 incident) -- see
    # `frob doctor`'s stale-ticket-lease scan (docs/guides/install.md
    # #stale-ticket-lease-scan-t-1131) for the read-side complement (a
    # ticket already stuck this way, from before this fix).
def drop_ticket(root: Path, ticket_id: str, reason: str, *,
                 absorbed_by: str | None = None) -> Result[Ticket, TicketError]
    # T-0579: appends a dated line under '## Drop reason' (same append-a-
    # section shape as record_failure's '## Failure log'), then transitions
    # to DROPPED so a held lease releases the normal way. Err(
    # DropReasonMissing) if `reason` is blank; `absorbed_by` is an
    # unvalidated cross-reference note, not a blocked_by-style edge.
    # T-2078: the transition's legality is now checked FIRST, against the
    # same state machine table `transition()` enforces -- Err(
    # InvalidTransition) with ZERO writes for a ticket already terminal
    # (`done`/`dropped`). The old order (write the drop-reason body, THEN
    # attempt the transition) let a terminal ticket's body get
    # destructively rewritten -- dropping its '## Done report' section --
    # before the transition refusal was ever seen, leaving the rewrite
    # sitting uncommitted in the working tree.
def attach(root: Path, ticket_id: str, source: AttachmentSource,
           caption: str) -> Result[Attachment, AttachError]
    # source is a file path or clipboard; stores under tickets/attachments/.
def add_evidence(root: Path, ticket_id: str, node_ids: Sequence[str],
                  collected: frozenset[str] | None = None,
                  passed: frozenset[str] | None = None,
                  accepts: Sequence[int] | None = None) -> Result[Ticket, TicketError]
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
    # T-0572: `accepts` is a list of 0-based ticket.acceptance indices --
    # node_ids are ALSO bound onto each named criterion's own `evidence`
    # tuple, in the same atomic write as the evidence-list append. An
    # out-of-range index rejects the whole batch as
    # Err(AcceptanceIndexOutOfRange) before anything is written.
    # `accepts=None` (default) binds nothing.
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
    # T-1125: also rewrites body PROSE citations of any renumbered id (a
    # Done report or description mentioning a sibling ticket that moved),
    # not just the structural id/blocked_by/parent fields -- see
    # renumber_one's note below, same mechanism.
def renumber_one(root: Path, old_id: str, new_id: str, *,
                  dry_run: bool = False) -> Result[RenumberReport, TicketError]
    # Rewrites ONE ticket's id everywhere: its ledger section (active or
    # archive) plus every blocked_by/parent reference across BOTH stores,
    # plus every frob:ticket/frob:waive/frob:todo/frob:tests/frob:invariant/
    # frob:doc directive line across the tracked tree that names it.
    # `frob ticket renumber <old> <new>`'s implementation; --dry-run reports
    # the same plan without writing. See "Provisional ids" below.
    # T-1125: ALSO rewrites every OTHER ticket's Done-report/description
    # body PROSE that cites old_id (whole-word, e.g. "Filed: T-draft-xxxx"
    # or a description naming a sibling ticket) to new_id, in the same
    # ledger_lock transaction -- previously only the structural fields
    # were rewritten, leaving prose citations permanently stale: either a
    # TICK006 phantom once a dead draft id no longer resolves, or (worse,
    # invisible to any gate) a citation of the WRONG real id if a hand-
    # guessed final id happened to already be taken. `RenumberReport.
    # occurrences` folds these prose-hit counts in alongside code-reference
    # hits. See `frob.tickets._new_renumber._rewrite_body_prose_references`.
    # T-1173: also migrates old_id's cross-worktree lease file (if any) to
    # new_id via `frob.tickets._leases.rename_lease`, AFTER the ledger
    # persist succeeds -- see "Cross-worktree lease side-channel (T-0473)"
    # above for why a draft-to-final rename needed this.
def finalize_draft(root: Path, draft_id: str) -> Result[str, TicketError]
    # Assigns draft_id its final T-#### id against the CURRENT merged view
    # and rewrites everything via renumber_one; a no-op returning draft_id
    # unchanged if it is already final. The callable finalize step T-0176
    # (`frob ticket land`) will invoke at merge time.
def archive(root: Path) -> Result[int, TicketError]
    # Moves every done/dropped ticket from the active store into
    # tickets-archive.md verbatim (same section format); idempotent.
def is_valid_ticket_ref(value: str) -> bool
    # T-1132: whether value is a well-formed ticket-id reference (T-####
    # or T-draft-<8 hex>) -- the same shape TicketSpec's blocked_by/parent
    # field validators enforce at construction time. Exposed for call
    # sites that mutate an EXISTING Ticket via model_copy (which bypasses
    # pydantic field validators entirely) and must therefore validate a
    # new edge by hand before writing -- see `frob ticket block`'s CLI
    # handler (frob.app.ticket_runner._lifecycle._block).
def set_done_report(root: Path, ticket_id: str, *, why: str,
                     base_ref: str = "main") -> Result[Ticket, TicketError]
    # T-0458: THE single write path for a ticket's Done report. `why` is
    # the ONLY thing the caller supplies -- Changed (compute_changed_lines,
    # git diff --stat vs base_ref) and Evidence (render_evidence_block,
    # from the ticket's own recorded evidence) are always auto-composed and
    # spliced into body's '## Done report' section via
    # replace_done_report_section (frob.tickets._models), so a caller never
    # parses or edits markdown, and can never hand-type a Changed/Evidence
    # list that drifts from what actually shipped. Example:
    #   set_done_report(root, "T-0458", why="implemented the thing")
    #   # -> Ok(Ticket(... body="## Done report\n\nimplemented the thing\n\n
    #   #     ### Changed\n```\nsrc/x.py | 3 ++-\n```\n\n### Evidence\n
    #   #     - `tests/x.py::test_y` (pytest node id, verified passing
    #   #     when recorded)\n"))
    # T-0887: `base_ref` is validated (base_ref_resolvable) FIRST -- an
    # unresolvable ref (in a real git checkout) returns
    # Err(TicketError.BaseRefUnresolvable) immediately instead of being
    # discovered minutes later via a silently-empty diff or a downstream
    # `frob check` spawn. Only the final load-compose-write is held under
    # ledger_lock end to end (T-0458 single-writer invariant); the
    # (potentially slow) run_tests/check_gates/check_gate_findings claims
    # capture runs BEFORE the lock is taken, since those are read-only and
    # previously serialized every other concurrent ticket mutation on this
    # ledger behind up to two 600s `frob check --ticket` subprocess spawns.
    # T-1254: in v2-mode repos this writes tickets/T-####/done-report.md
    # (write_done_report) instead of splicing into body -- see "v2 backend"
    # under Storage internals below.
def base_ref_resolvable(root: Path, base_ref: str) -> bool | None
    # T-0887: bounded git rev-parse check of whether base_ref resolves to a
    # real commit in root's clone. True/False when root is a real git
    # checkout; None when root is not a git checkout at all (a DIFFERENT,
    # unrelated failure -- preserves compute_changed_lines's long-standing
    # best-effort contract for non-git roots).
def compose_done_report(why: str, changed_lines: Sequence[str],
                         evidence: Sequence[str]) -> str
    # T-0458: pure composition -- why plus render_changed_block(changed_lines)
    # and render_evidence_block(evidence) folded into one '## Done report'
    # section string. set_done_report's only caller; exposed separately so
    # a caller that already has git/evidence data in hand can render
    # without touching the store.
    # T-1536: `why` is run through sanitize_narrative_for_ledger before
    # composing, so a narrative line that happens to be byte-identical to
    # another ticket's `<!-- ticket:T-#### -->` marker (e.g. quoting a
    # corrupt-ledger incident verbatim) can never forge a fake section
    # boundary the next time the ledger is parsed.
def sanitize_narrative_for_ledger(text: str) -> str
    # T-1536: defuses any line in caller-authored `text` that would
    # otherwise be byte-identical to a real `<!-- ticket:T-#### -->` ledger
    # marker (`<!--` -> `<! --`), so free-text narrative can never be
    # mistaken for a structural section boundary on a later parse. Used by
    # compose_done_report; text with no marker-lookalike line is returned
    # unchanged.
def render_evidence_block(evidence: Sequence[str]) -> str
    # T-0458: renders a ticket's evidence tuple as-is -- no fresh
    # collection or test run needed, since every id in `evidence` was
    # ALREADY validated resolvable-and-passing (add_evidence's D-01 check)
    # or exit=0 (cmd: entries) at record time. "(no evidence recorded)" if
    # empty.
def replay_evidence_from_done_report(root: Path, ticket_id: str) -> Result[Ticket, TicketError]
    # T-0357: recovers a ticket's structured evidence: field from its own
    # rendered '### Evidence' Done-report prose when the field is empty --
    # the coordinator-land bug where evidence recorded via add_evidence in a
    # worktree never reached main's ledger in a form transition(..., DONE)
    # recognizes (a hand `git merge --no-ff` that bypassed the T-0176/T-0479
    # ledger splice). No-op (Ok, no write) if evidence is already present;
    # Err(MissingEvidence) unchanged if nothing recoverable is found.
    # Recovered ids are NOT re-validated against a fresh collection/pass
    # run -- follow up with `frob check`'s COV003/TEST001 for that. Wired
    # automatically into transition(..., DONE) as a best-effort recovery
    # attempt before the ordinary MissingEvidence rejection.
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
def set_component(root: Path, ticket_id: str, component: str | None) -> Result[Ticket, TicketError]
    # T-0454: `frob ticket component <id> <name>` -- which module/area this
    # ticket belongs to (freeform, not an enum). `component=None` clears it
    # back to uncategorized. Same single-writer, ledger-locked pattern as
    # set_priority.
def set_tier(root: Path, ticket_id: str, tier: TicketTier) -> Result[Ticket, TicketError]
    # T-1069: `frob ticket tier <id> <epic|story|ticket>` -- reclassify an
    # already-created ticket's place in the epic -> story -> ticket
    # hierarchy (T-0715 landed the field and `new --tier` for set-at-create,
    # but no mutator for an existing ticket). Same single-writer,
    # ledger-locked pattern as set_priority/set_kind/set_component/
    # set_sprint. Does not re-validate or move `parent` links.
def set_runs_last(root: Path, ticket_id: str, runs_last: bool) -> Result[Ticket, TicketError]
    # T-1613: `frob ticket runs-last <id> <on|off>` -- flip the runs-last
    # marker: while True, `doable`/`start` structurally refuse to surface
    # or start this ticket while ANY OTHER non-runs-last ticket in the
    # ledger is non-terminal (queued/planned/in-progress/blocked). Two or
    # more runs-last tickets coexist and order among themselves via
    # ordinary blocked_by. Same single-writer, ledger-locked pattern as
    # set_priority/set_tier.
def mutate_labels(root: Path, ticket_id: str, *, add: Sequence[str] = (),
                   remove: Sequence[str] = ()) -> Result[Ticket, TicketError]
    # T-0454: `frob ticket label <id> --add TAG... --remove TAG...` --
    # freeform tags orthogonal to component, comma-split the same way scope
    # entries are (T-0241). No lease-conflict check (a label is not a
    # filesystem glob) and no audit trail the way mutate_scope keeps for
    # scope_changes -- Err(LabelChangeEmpty) if neither add nor remove
    # names anything.
def board_view(queue: TicketQueue, *, component: str | None = None,
                label: str | None = None) -> tuple[BoardColumn, ...]
    # T-0454: `frob ticket board` -- every ticket grouped into BOARD_STATES
    # columns (queued -> planned -> in-progress -> blocked -> done ->
    # dropped), each priority-then-age ordered (_doable_sort_key, T-0411).
    # Every column is always present, even empty. component/label narrow to
    # one area/tag; a ticket must match BOTH when both are given.
def epic_rollup(queue: TicketQueue, epic_id: str) -> Result[EpicRollup, TicketError]
    # T-0454: `frob ticket epic <id>` -- the full descendant subtree of
    # epic_id via the parent chain (any depth), a done/total count, and the
    # ids of any LEAF descendant (no children of its own) currently
    # BLOCKED. Err(NotFound) if epic_id itself does not resolve.
def brief_ticket(root: Path, ticket_id: str) -> Result[str, TicketError]
    # T-0568: `frob ticket brief <id>` -- the complete mission briefing text
    # (frob.tickets._brief.compose_brief): body+acceptance, scope+leases,
    # the agent-playbook's own hard-rule sections (parsed from its
    # headings), inferred verify commands, gate-baseline status, and the
    # REL/land rules. Err(NotFound) if ticket_id does not resolve.
def has_live_lease(ticket: Ticket, root: Path | None) -> bool
    # T-0752: whether `ticket` itself (not a scope collision with some
    # OTHER ticket -- that's leased_by's job) has a live lease against it
    # right now, via display_state's T-0716 overlay -- the in-flight/
    # dispatchable row split signal for `frob ticket doable`.
def dispatch_stale_hours(ticket: Ticket, *, today: date | None = None) -> float
    # T-0752: hours `ticket` has sat since `Ticket.created` (the only
    # timestamp the model carries; "last state change" degrades to
    # "filing", day-granular not wall-clock).
def undispatched_stale(tickets: Sequence[Ticket], root: Path, *,
                        today: date | None = None) -> tuple[tuple[Ticket, float, float], ...]
    # T-0752: (ticket, hours_elapsed, threshold_hours) for every CRITICAL/
    # HIGH ticket in `tickets` past its `[tickets] dispatch_stale_*_hours`
    # threshold (frob.toml) -- the single staleness-alarm judgment
    # `doable`'s row rendering and a future TICK-family gate both call.

# frob/tickets/clipboard.py
def clipboard_image() -> Result[bytes, ClipboardError]
    # PNG bytes from the platform clipboard, via the first working backend.
def clipboard_has_image() -> bool
    # Cheap probe used to decide whether to offer the interactive prompt.

# frob/tickets/__init__.py
def validate_evidence(entry: str) -> Result[str, TicketError]
    # One evidence string's schema: non-empty, single-line, bounded length,
    # not a 3+-segment `::`-separated shape no real pytest node id ever
    # takes (T-1706), normalizing a dotted Class.method suffix to the
    # pytest Class::method form (T-0293) first.
```


## Split files (T-1780)

This document held the whole `frob.tickets` reference in one 545KB/11252-line file (originally; the doc-only file you are reading is smaller) until T-1780: 35+ open tickets named it, so any one ticket's lease on `docs/modules/tickets.md` blocked every other ticket that also needed to touch its own unrelated section. Split along the document's own subject boundaries (parsed heading structure), not arbitrary size chunks, so a ticket touching landing no longer leases the section about evidence or the merge driver:

- [`docs/modules/tickets-lifecycle.md`](tickets-lifecycle.md) -- filing, duplicate refusal, the structured review channel, the scope-lease model, the cross-worktree lease side-channel, ledger auto-commits, `reconcile`, the intent journal, atomic ledger writes, the scope/lease change protocol, organization (components/labels/board/epics), the runs-last marker, `frob ticket brief`, the state machine, provisional ids, `frob ticket promote`, and the content-loss guard.
- [`docs/modules/tickets-landing.md`](tickets-landing.md) -- `frob ticket land` itself and everything on its critical path: `--plan`, the mutation-evidence obligation (TEST016) and its batch sweep, `--check-repro`, live-tracker citation, land hardening, sibling ledger edits, the land exclusivity lease, the root checkout write guard, liveness authority, orphaned-lease detection, verify-then-destroy, the worktree liveness scan, passenger-ticket disclosure, already-landed-on-main, cross-ticket leakage, orphaned evidence deletion, evidence-only scope, post-mutation reverification, auto-sync after land, `OutOfScopeWaiveDeletion`, the post-land unscoped error sweep, `frob check --land-parity`, and `frob ticket evidence --replace`.
- [`docs/modules/tickets-verify-sweep.md`](tickets-verify-sweep.md) -- the merge queue, the T-1686 landing-independent-of-verifying epic, the verification watermark, the coalescing verify worker and its resource budget, batch test selection, symbolic attribution, backpressure, the quarantine circuit breaker, the `frob verify` CLI, development profiles, rapid debt and the ratchet override, and the deferred post-land sweep.
- [`docs/modules/tickets-merge-driver.md`](tickets-merge-driver.md) -- the git merge driver for `tickets.md` and the `rapid-debt.jsonl` merge rule.
- [`docs/modules/tickets-data-storage.md`](tickets-data-storage.md) -- clipboard capture, data models, error types, storage internals (including the v2 migration/backend), the shared YAML loader, the worktree-lease guard, design decisions, dependencies, integration points, and the remaining organization primitives (tiers, sprints, `flow`, `accept`).

This file keeps the overview, storage summary, and public API reference -- the parts every ticket touching `frob.tickets` needs regardless of which subject it works in -- so the shared lease it carries stays small and general.
