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
<!-- frob:describes src/frob/tickets/__init__.py::record_failure -->
<!-- frob:describes src/frob/tickets/__init__.py::attach -->
<!-- frob:describes src/frob/tickets/_evidence.py::add_evidence -->
<!-- frob:describes src/frob/tickets/_evidence.py::run_cmd_evidence -->
<!-- frob:describes src/frob/tickets/_evidence.py::reverify_cmd_evidence -->
<!-- frob:describes src/frob/tickets/_evidence.py::add_cmd_evidence -->
<!-- frob:describes src/frob/tickets/clipboard.py::clipboard_image -->
<!-- frob:describes src/frob/tickets/clipboard.py::clipboard_has_image -->
<!-- frob:describes src/frob/tickets/_archive.py::migrate -->
<!-- frob:describes src/frob/tickets/_new_renumber.py::renumber -->
<!-- frob:describes src/frob/tickets/_new_renumber.py::renumber_one -->
<!-- frob:describes src/frob/tickets/_new_renumber.py::finalize_draft -->
<!-- frob:describes src/frob/tickets/_archive.py::archive -->
<!-- frob:describes src/frob/tickets/_archive.py::load_active -->
<!-- frob:describes src/frob/tickets/_provisional.py::on_default_branch -->
<!-- frob:describes src/frob/tickets/_provisional.py::mint_draft_id -->
<!-- frob:describes src/frob/tickets/_doable.py::doable_blocked -->
<!-- frob:describes src/frob/tickets/_doable.py::leased_by -->
<!-- frob:describes src/frob/tickets/_doable.py::large_glob_warnings -->
<!-- frob:describes src/frob/tickets/_models.py::scope_overlap -->
<!-- frob:describes src/frob/tickets/_models.py::scope_overlap_globs -->
<!-- frob:describes src/frob/tickets/__init__.py::set_done_report -->
<!-- frob:describes src/frob/tickets/_evidence.py::reverify_close_guard -->
<!-- frob:describes src/frob/tickets/_models.py::recover_done_report_why -->
<!-- frob:describes src/frob/tickets/__init__.py::compose_done_report -->
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
<!-- frob:describes src/frob/tickets/__init__.py::mutate_labels -->
<!-- frob:describes src/frob/tickets/__init__.py::board_view -->
<!-- frob:describes src/frob/tickets/__init__.py::epic_rollup -->
<!-- frob:describes src/frob/tickets/_doable.py::has_live_lease -->
<!-- frob:describes src/frob/tickets/_doable.py::dispatch_stale_hours -->
<!-- frob:describes src/frob/tickets/_doable.py::undispatched_stale -->
<!-- frob:describes src/frob/tickets/_models.py::is_valid_ticket_ref -->

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
    # state in {queued, planned} and no open blockers, ordered by priority
    # (highest PRIORITY_RANK first, T-0411) then oldest-first within a tier.
def set_priority(root: Path, ticket_id: str, priority: Priority) -> Result[Ticket, TicketError]
    # T-0411: `frob ticket priority <id> <level>` -- the accountable,
    # single-writer way to reprioritize a ticket instead of hand-editing
    # tickets.md frontmatter (same shape as mutate_scope/T-0455).
def transition(root: Path, ticket_id: str, to: TicketState, *,
                covers_scope: bool | None = None,
                reviewed: bool | None = None,
                mutation_evidence: bool | None = None,
                evidence_reverified: bool | None = None) -> Result[Ticket, TicketError]
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
    # D-05); `evidence_reverified=None` (default) skips the check.
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
```

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

```bash
frob ticket evidence T-0042 tests/test_foo.py::test_stronger  # bind new/strengthened evidence
frob ticket reverify T-0042                                   # re-run close verification, refresh recap
```

`reverify` re-runs the EXACT SAME checks `close` runs at close time, with
**no state transition either way** on success or failure:

- the four injected guards `_close_guards_for_ticket` computes for
  `close` (D-02 `covers_scope`, T-0571 `reviewed` when `--strict` +
  `require_review_for_close` are both set, T-0844 `mutation_evidence`,
  T-0417 `evidence_reverified` -- a fresh re-run of the ticket's own
  recorded evidence against the CURRENT tree), and
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
the same way `frob.tickets._land._commit_finalize_writes` already owns
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

## Stale-worktree-cut warning (T-1059)

T-1030 root-caused a recurring incident (fa606fe8, b3589c3e): dispatched
worktrees can be cut from a stale base -- the dispatch harness's
`EnterWorktree` tool defaults to branching from `origin/<default-branch>`
rather than local `HEAD`, and this repo's `origin/main` regularly lags
local `main` by dozens to hundreds of commits across a session. The
playbook's warm-up step (`docs/guides/agent-playbook.md#1-worktree-warm-
up`) is the manual fix; this is the mechanical detector that catches it at
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
`docs/modules/gates.md#tick011-t-1129` for TICK011's own design.
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
<!-- frob:describes src/frob/tickets/_land.py::_apply_release_bump -->
<!-- frob:describes src/frob/tickets/_land.py::_maybe_rebuild_natives -->
<!-- frob:describes src/frob/app/ticket_runner/_land_cmd.py::_apply_release_bump_for_land -->
<!-- frob:describes src/frob/app/ticket_runner/_land_cmd.py::_write_release_bump -->
<!-- frob:describes src/frob/app/ticket_runner/__init__.py::_root_release_manifest -->
<!-- frob:describes src/frob/app/ticket_runner/_land_cmd.py::_land_rebuild_natives_fn -->

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
         covers_scope: bool | None = None,
         bump_version: Callable[[Path, Ticket, str], Result[str | None, LandError]] | None = None,
         rebuild_natives: Callable[[Path], bool] | None = None,
         sync_gate_rules: Callable[[Path, str], Result[tuple[str, ...] | None, LandError]] | None = None) -> Result[LandReport, LandError]
    # T-0398 D-05: `collected`/`passed`/`covers_scope`, when supplied by a
    # caller with a fresh test-collection/run/graph-binding oracle computed
    # against the POST-MERGE worktree tree, re-verify the ticket's evidence
    # (resolution, pass, scope-binding) BEFORE finalize/close -- `land`
    # previously trusted whatever the worktree's pre-merge report claimed
    # and re-ran nothing. All three default to `None` (skip, unchanged
    # behavior) since computing them needs frob.testing/frob.graph access
    # frob.tickets deliberately does not have.
    # T-0338: `bump_version(root, ticket, final_id)` and `rebuild_natives
    # (root)`, when supplied, fold the REL001 version-bump/stamp and
    # native-rebuild-trigger coordinator steps into this same land -- both
    # invoked AFTER the squash-apply is staged (so their writes land in the
    # SAME commit) but BEFORE the T-0463 completeness assertion and final
    # commit. Both default to `None` (skip) for the same cycle-avoidance
    # reason as collected/passed/covers_scope; `frob ticket land` supplies
    # both by default.
    # T-1011: `sync_gate_rules(root, pre_land_tip)`, when supplied, runs
    # right after `bump_version` (same staged-but-uncommitted point) and
    # decides for itself, by diffing the landing diff, whether
    # `_KNOWN_GATE_RULES` changed; if so it auto-files any missing
    # `check-coverage.yaml` row (REG010) into the SAME land commit, ending
    # the manual `frob registry audit --sync-gate-rules` re-sync
    # docs/audits/coordination-churn.md disclosed drifting twice in one
    # drive. Defaults to `None` (skip) for the same cycle-avoidance reason;
    # `frob ticket land` supplies it by default
    # (`ticket_runner._land_sync_gate_rules_fn`).
def splice_ledger(ours_text: str, theirs_text: str, *,
                   base_text: str | None = None) -> Result[str, TicketError]
    # Merge two tickets.md texts at the TICKET-ID level (newest state per
    # id wins) instead of git's line-level textual merge. T-0398 D-09: the
    # winning side's evidence is UNIONED with the losing side's (never
    # dropped) on a same-id divergence.
    # T-1154: `base_text` (the true 3-way merge-base's ledger text, when
    # the caller has one) sharpens a same-id divergence: whichever side is
    # byte-identical to `base_text` made no deliberate edit and has no
    # claim on the id, so the side that DID change wins outright, before
    # ever falling back to the state-rank/richness tiebreak above. This is
    # the fix for the wrong-side-merge corruption class (3rd occurrence):
    # a worktree's untouched, merely-stale copy of a ticket main had since
    # content-edited (e.g. an evidence-path migration inside an already-
    # `done` block) used to tie on rank/richness and arbitrarily win.
    # `frob ticket land`'s own `tickets-archive.md` splice
    # (`_splice_and_stage_archive`) threads this through from the true
    # `git merge-base`; `None` (the default) degrades to the pre-T-1154
    # behavior unchanged.
```

Order of operations, and why it is this order:

0. **Resolve `root` from `worktree` itself when they resolve to the
   IDENTICAL path** (T-1003, docs/audits/coordination-churn.md#4): `root`
   defaults to the CLI invoker's cwd (`ticket_runner.py`'s `_land`), so
   running `frob ticket land <id> --worktree <path>` from a shell that
   never `cd`ed out of the worktree first makes `root` resolve to
   `worktree` for free -- the "chained cd" ritual every land used to
   require. `git -C <worktree> rev-parse --git-common-dir` (git's own,
   cwd-independent answer to "where is this clone's primary checkout")
   resolves the true `root` transparently whenever it differs from
   `worktree` -- a real linked worktree, the common case. When it comes
   back equal to `worktree` (no linked worktree exists at all --
   `--worktree` was pointed at the primary checkout itself), `root` is
   left unchanged and the T-0795 `_refuse_if_root_is_worktree` guard in
   step 1 still refuses exactly as before; this step never weakens that
   guard, only retires the manual-cd case it used to also (mis-)catch.
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
   the merge that follows. T-1003: `worktree`'s own `uv.lock` frob-
   version-only flap (the same T-0793 shape step 1's `root`-side restore
   already tolerates -- a prior `uv run`/`uv lock` against a pyproject a
   sibling land already bumped, with nothing else in the tree touched) is
   auto-restored HERE first, before the dirty check -- otherwise the flap
   would get silently wip-committed as noise and squash-applied into the
   landing commit in step 9, needing the same manual `git checkout --
   uv.lock` ritual land already killed on the `root` side.
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
9.6. **REL001 version bump** (T-0338, only when `bump_version` was
    supplied, runs right after step 9's squash and BEFORE the step 9.5
    completeness assertion): `bump_version(root, ticket, final_id)`
    computes the semver class the just-squashed public API demands
    (`frob.release.diff_class`/`required_version` against the tracked
    `.frob-release.json` manifest), and if the declared `pyproject.toml`
    version does not already cover it, rewrites `version = "..."`,
    prepends a minimal `## [<version>] - unreleased` CHANGELOG.md entry
    naming the ticket, and `frob release stamp`s the new manifest --
    staging all three files so they land in the SAME commit as the
    squash-apply. `Ok(None)` (no manifest yet, or no bump needed) is a
    no-op; `Err(LandError.ReleaseBumpFailed)` unwinds the squash (`git
    reset --hard && git clean -fd`) exactly like any other land failure --
    a silently-skipped bump would let a landed API change slip past
    REL001 undetected. Reported back as `LandReport.release_bumped_to`.

    **T-0992 monotonicity assertion**: `_apply_release_bump` independently
    reads main's own pre-land `pyproject.toml` version via `git show
    <pre_land_tip>:pyproject.toml` (a git-object read, immune to whatever
    the squash-apply's working-tree mutation did to the on-disk file --
    `pyproject.toml` is not scope-protected, so a ticket's own worktree can
    carry it through the squash) BEFORE invoking `bump_version`, and
    hard-refuses (same unwind-and-`Err(ReleaseBumpFailed)` path) unless the
    callback's returned version is strictly greater than that captured
    baseline. This is a caller-independent backstop: twice in one day a
    `bump_version` implementation computed its "next version" from a
    stale, worktree-carried input and clobbered a higher version already
    on main (T-0976, T-0989) -- this assertion makes that class of bug a
    loud land failure instead of a silent regression, sibling to T-0959's
    archive-splice integrity check and T-0740's ledger integrity check.

    **T-1007 producer fix**: `ticket_runner._apply_release_bump_for_land`
    (the library's own `bump_version` callback, wired via
    `_land_bump_version_fn`) used to derive its bump BASELINE from
    `frob.release.load_manifest(root)` -- an on-disk read of `.frob-
    release.json` AFTER the squash-apply, exactly the working-tree
    mutation the T-0992 assertion above exists to be immune to. A stale,
    out-of-scope worktree copy of `.frob-release.json` riding the squash
    silently under-computed the required bump every time, tripping the
    T-0992 refusal on the FIRST land attempt and forcing a manual merge +
    reland round trip (the recurring churn item T-1007 was filed
    against). `_root_release_manifest` (T-1007) now reads `.frob-
    release.json` via `git show HEAD:.frob-release.json` -- root's own
    committed pre-land state, never the worktree-carried working-tree
    copy -- making the T-0992 guard a never-fires invariant for this
    callback instead of a per-land speed bump.

    **T-1078 quartet-atomicity backstop**: after a successful, monotonic
    bump, `_apply_release_bump` force-resyncs `.frob-release.json`'s
    `version` field to the callback's reported version via
    `frob.release.set_manifest_version` and stages it in this SAME step
    -- regardless of whether `bump_version`'s own implementation wrote
    (or correctly wrote) the manifest itself. This is the fix for the
    incident where a land's REL001 bump updated `pyproject.toml`/
    `CHANGELOG.md` but silently left the manifest on its old version:
    every subsequent land then re-derived an already-taken "next
    version" from the stale manifest and refused on the T-0992
    monotonicity guard, blocking three lands in a row until a
    coordinator hand-reconciled the manifest and ran `frob release
    sync`. The refusal diagnostic for that guard also now detects this
    exact desync independently (comparing `.frob-release.json`'s version
    against `pyproject.toml`'s version, both read at `pre_land_tip` via
    `_read_root_manifest_version`/`_read_root_pyproject_version`) and,
    when it is the actual cause of a monotonicity refusal, names the
    incoherent quartet explicitly and prescribes `frob release sync`
    instead of the bare "not strictly greater than main's pre-land
    version" message.
9.7. **Native rebuild trigger** (T-0338, only when `rebuild_natives` was
    supplied AND the landed changeset touches a native source tree --
    `frob-core/` or `strata-core/`): `rebuild_natives(root)` runs `make
    core` in `root`. Best-effort: a `False`/failed rebuild is logged as a
    warning (alongside the existing T-0248 stale-native warning, which
    still fires unconditionally) but never unwinds or blocks the land --
    a native rebuild is cheap to re-run by hand. Reported back as
    `LandReport.natives_rebuilt`.
9.75. **TICK005-backed regression sweep** (T-0631, immediately after step
    9's splice, BEFORE the completeness assertion): `land()`'s own
    `_tick005_land_regressions(root_pre_text, spliced_text, archived_ids)`
    (`_land.py`) compares `root`'s ledger text from just before this
    land's splice against the text just staged by it, and refuses
    (`Err(LandError.TerminalStateRegression)`, unwinding the squash via
    `_verified_reset_root` exactly like a `SquashConflict`) if any ticket
    that was terminal (DONE/DROPPED) pre-splice is neither terminal nor
    archived post-splice. This mirrors `frob check`'s `TICK005` gate
    (`_tick005_merge_state_regression`, T-0537's hand-resolved-conflict
    resurrection incident) but runs it directly around THIS land's own
    squash-splice instead of relying on a later `frob check` catching it
    on some unrelated future merge commit -- `_land_squash_apply`'s own
    squash-apply is always a single-parent commit, so the gate's `HEAD^2`
    precondition (a genuine two-parent merge) can never fire for a land
    at all, the exact gap this closes. The two implementations are
    deliberately NOT shared code: `frob.gates` depends on `frob.tickets`,
    never the reverse (docs/rework.md cycle-avoidance), so `_land.py`
    reimplements the same terminal-state-regression semantics against its
    own pre/post ledger texts rather than importing the gate.
9.8. **Stacked-sibling absorption check** (T-1001, docs/audits/coordination-
    churn.md#2, immediately before step 10's commit): when one worktree
    carries several tickets, the first land's squash-apply absorbs every
    sibling's files and ledger state -- each subsequent land then stages
    an EMPTY squash in step 9, and an unconditional `git commit` would
    exit 1 with no stderr, surfacing as an unexplained `CommitFailed`.
    `_land_squash_apply` checks whether anything is actually staged
    (`git diff --cached --name-only`) right before attempting the commit;
    if not, it VERIFIES (never assumes) genuine absorption -- `final_id`
    must already be `done` in `root`'s current ledger, AND every file in
    the ticket's own `scope` must already match content-for-content
    between the worktree's finalized HEAD and `root`'s current HEAD (a
    direct cross-checkout `git diff`, since a worktree shares its object
    store with its primary checkout). Both holding returns a clean
    success naming the ALREADY-EXISTING absorbing commit
    (`LandReport.commit_sha`, unchanged) with `LandReport.ledger_spliced
    =False` as the signal nothing new was committed this call (the
    frozen `LandReport` model has no dedicated field for this). Either
    check failing falls through to the ordinary step 10 commit attempt
    and its unmodified, honest `CommitFailed` error -- an empty stage for
    some OTHER, unexplained reason is never silently reported as success.
10. **Commit** with a conventional-commit message template
    (`<type>(tickets): land <final-id> <title>`, type derived from
    `ticket.kind`; `feature`->`feat`, `bug`/`security`/`ux`/`incident`->
    `fix`, `docs`->`docs`, `invariant`->`test`). ASCII only, no
    `Co-Authored-By` line, matching repo convention.
11. **`--push`** (T-0631, CLI-only, opt-in): once `frob ticket land`'s
    entire chain above has actually succeeded -- step 10's commit exists
    and every check before it passed, never on a `--dry-run` (nothing
    durable was committed to push) and never after a failed land (there is
    nothing new to push) -- `frob ticket land <id> --worktree <path>
    --push` runs `git -C <root> push origin <branch>` for `root`'s current
    branch (`ticket_runner._push_after_land`). A push failure (a refused
    spawn under `FROB_DISABLE_EXEC=1`, or a non-zero `git push` exit) logs
    the exact remedy (`git -C <root> push origin <branch>` by hand) and
    exits the process non-zero, but does NOT unwind the already-landed
    commit -- by this point the land itself is done and there is nothing
    left to undo, only a later, separate step (the push) that failed.

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

## Mutation-evidence obligation (TEST016, T-0755)

<!-- frob:describes src/frob/tickets/_mutation_evidence.py::check_ticket_mutation_evidence -->
<!-- frob:describes src/frob/gates/_mutation_evidence.py::mutation_evidence_violations -->
<!-- frob:describes src/frob/tickets/_land.py::_check_mutation_evidence -->

Several real rejects (T-0611, T-0571, T-0682, T-0574, T-0710) shared one
root cause: the implementer's own recorded evidence tests PASSED before
the fix even existed, because they were written CONFIRMATORY ("assert the
thing I just built does the thing") instead of ADVERSARIAL ("prove a
mutant of this logic gets caught"). A confirmatory test that would pass on
both the pre-change and post-change code proves nothing about the change
it claims to cover.

`frob.tickets._mutation_evidence.check_ticket_mutation_evidence(root,
ticket, base_ref)` closes this with a bounded, diff-scoped mutation pass
that reuses `frob.mutate` (`generate_mutants`/`run_mutations`) as its ONLY
mutation engine -- there is no second one:

1. `_evidence_test_ids(ticket)` -- the subset of `ticket.evidence` shaped
   like a pytest node id (`path::name`); `cmd:` evidence and anything else
   is excluded (nothing `frob.mutate`'s `test_argv` can re-run).
2. `_touched_python_files(root, ticket, base_ref)` -- `.py` files the
   ticket's own `scope` covers that differ from `base_ref` in the working
   tree (`frob.gitio.working_diff`, the one diff seam every other caller
   in this repo already uses). Test files themselves (`test_*.py`,
   `*_test.py`, anything under a `tests/` path segment) are excluded --
   mutating a test file and re-running THAT SAME file as the kill oracle
   is a self-referential no-op; the boundary this check exists to
   interrogate is test-vs-logic, not test-vs-itself.
3. For up to 3 touched files (`_MAX_FILES`), mutate up to 8 points each
   (`_MAX_MUTANTS_PER_FILE`, `run_mutations`' new `max_mutants` cap, taken
   in source order so the run is deterministic) and re-run the ticket's
   own evidence test ids as the kill command, each mutant capped at 90s
   (`_TIMEOUT_S`). Mutation points are restricted to the file's OWN
   CHANGED LINES (`run_mutations`' `line_ranges`, fed from the diff's
   per-file hunk spans) -- a file-wide selection previously let an
   unrelated pre-existing line supply every mutant for a tiny diff,
   flagging evidence that had nothing to say about code the ticket never
   touched. A file where every mutant SURVIVED (0 killed, total > 0)
   becomes a `ConfirmatoryFinding` naming the file and the evidence ids
   that failed to distinguish it.

No test evidence recorded, no in-scope touched Python file, or a touched
file with zero mutable points within its changed lines (a docstring-only
change, an unmutable one-line diff) are all `Ok(())` -- "nothing to
check," not a finding. A refused mutant spawn
under the exec kill switch (`FROB_DISABLE_EXEC=1`, T-0803's own posture)
is `Err(MutationEvidenceError.ExecDisabled)`, never silently reported as a
clean pass.

`frob.gates.mutation_evidence_violations(root, ticket, base_ref)` turns
any `ConfirmatoryFinding`s into `TEST016` `Violation`s: WARN severity by
default, promoted to ERROR for `security`/`bug`-kind tickets (the exact
kinds the root-cause incidents above came from). This is a plain per-
ticket `kind` check, not `frob.gates._ratchet`'s baseline-pool mechanism
-- no retroactive concern applies, because the obligation only ever runs
at THIS ticket's own close/land time, never re-scanning an already-closed
ticket's evidence, so landing this rule cannot turn a past close red.

**Wired into `frob ticket land`** (`_land.py::_check_mutation_evidence`,
called from `_land_precheck` right after `current_branch` resolves, before
any git mutation): a `security`/`bug`-kind ticket with an ERROR-severity
TEST016 finding refuses the land (`LandError.EvidenceConfirmatoryOnly`);
every other kind's WARN finding is logged and does not block. `frob
ticket land --skip-mutation-evidence` (AppConfig
`ticket_skip_mutation_evidence`, default off) is the documented escape
hatch for a genuine false positive: the check still runs and logs its
findings at WARNING, it just cannot refuse the land. Deliberately
NOT part of `frob.check`'s `test_gate`/`_ALL_GATES` snapshot pipeline
(`frob.check` is out of this ticket's scope): every other TEST rule is a
pure function of the graph snapshot, safe to run on every `frob check`
invocation; this rule spawns real bounded subprocesses per ticket, which
would violate the "must not slow the default `frob check` path for
tickets that never opt in" guard if it ran unconditionally there.

**Also wired into `frob ticket close` (T-0844)**, the direct non-land
close path: `frob.app.ticket_runner._close` computes the same
`mutation_evidence_violations` check against the CURRENT checkout (there
is no separate worktree/base_ref split on this path, so it runs against
`root` with `current_branch(root)` as the diff base -- see
`_close_mutation_evidence_for_ticket`) and passes the ERROR/no-ERROR
verdict to `transition(..., mutation_evidence=...)`, which
`_done_transition_guard` enforces the same way `_check_mutation_evidence`
does at land (`Err(TicketError.EvidenceConfirmatoryOnly)`). `frob ticket
close --skip-mutation-evidence` (AppConfig
`ticket_close_skip_mutation_evidence`, default off) is the close-path
twin of land's escape hatch: the check still runs and logs its findings,
it just cannot refuse the close. A security/bug-kind ticket can no longer
dodge this obligation by closing directly instead of landing.

## Live-tracker citation preflight (T-0854)

<!-- frob:describes src/frob/tickets/_live_tracker.py::live_tracker_citations -->

The T-0605-orphaned-41-rows incident class: closing/landing T-0605
instantly turned 41 `docs/design/registry/patterns.yaml` rows with
`disposition: "deferred:T-0605"` into main-wide REG003 errors, discovered
only on the NEXT `frob check`, one close too late. WAIVE006 already models
the identical hazard for `frob:waive ... ticket=<id>` bindings, but
neither check ran AT CLOSE/LAND TIME for the ticket about to disappear.

`frob.tickets._live_tracker.live_tracker_citations(root, ticket_id, *,
own_scope=())` is a plain `git grep` (not a full registry/graph parse --
the ticket's own PERF guard: "a targeted grep-shaped scan, not a full
registry parse per close") for every site that still cites `ticket_id` as
its live tracker: a registry `deferred:`/`tracked_by:` disposition
(`duplicate_of:` is excluded -- it never claimed the target still had open
work), or a waiver `ticket=`/`ticket "..."` attribute (both the
`frob:waive` comment grammar and the `.strata` `waive` clause grammar). A
provisional draft id is always clear (WAIVE006/WAIVE007's own `T-draft-*`
exemption, same rationale: land's draft-finalize step rewrites every
draft-id reference to the final id in the same commit). `own_scope` (the
closing/landing ticket's own declared `scope`) excludes citations inside
files the ticket itself owns -- a self-citing waiver lands/closes in the
SAME commit as the citation, never orphaned; the T-0605 incident class is
specifically an unrelated file citing a ticket that closes out from under
it.

**Wired into `frob ticket land`** (`_land.py::_check_live_tracker_
citations`, called from `_land_precheck` right after the scope preflight,
before any git mutation): any citation refuses the land
(`LandError.LiveTrackerCited`), scanned against the worktree's own tree
(what is about to be merged). **Also wired into `frob ticket close`**
(the direct non-land path): `_done_transition_guard` runs the SAME check,
unconditionally (no injection needed -- unlike `covers_scope`/`reviewed`/
`mutation_evidence`, this needs no external context beyond `root` and the
ticket itself, so every caller gets it for free), refusing on
`TicketError.LiveTrackerCited`. Neither path has a skip flag: the ticket's
own plan does not call for one, and the remedy (file a successor ticket
and re-point the citing rows, or re-point them in this same change) is
always mechanical.

## Land hardening (T-0577)

Three gaps found in one real landing session, closed together:

- **Registry yaml reference rewrite at draft finalize.** `finalize_draft`'s
  rename primitive (`renumber_one`) rewrote `frob:` directive lines and the
  ledger, but a registry yaml's `disposition: "deferred:<ticket>"` /
  `"duplicate_of:<ticket>"` value (docs/design/registry/*.yaml's grammar,
  `frob.registry._models.parse_disposition`) is a ticket-id REFERENCE that
  lives in YAML data, not a source comment -- it was left pointing at the
  now-dead draft id, breaking REG003 until a human hand-swapped it (a real
  incident: T-0388's compliance.yaml). `_rewrite_registry_references`
  (`frob.tickets.__init__`) rewrites these too, independent of the
  `frob:` directive-line matcher, whenever `renumber_one` runs.
- **Sibling Done-report preservation on splice.** `_splice_only_ticket`
  (T-0479) deliberately takes every ticket id OTHER than the one being
  landed from main untouched, to prevent a worktree's stale, requeued
  sibling state from resurrecting on main (T-0475). That guard has a real
  cost in a multi-ticket worktree: landing one ticket first silently
  erased a SIBLING ticket's already-written Done report (in-progress,
  review-gated, awaiting its own `land`) whenever main's copy of that
  sibling was still a bare `queued`/`planned` block -- a real incident
  (landing T-0386 regressed T-0387/T-0388 to queued, Done reports gone).
  `_preserve_sibling_done_reports` closes this without reopening T-0479:
  for each sibling id, the worktree's copy wins ONLY when it carries a
  substantive Done report main's copy lacks -- a stale advanced state with
  NO Done report on either side (the T-0479/T-0475 case) is untouched,
  main's side still wins.
- **Land-call serialization (`_land_lock`).** The entire `land()` body
  (precheck through the squash-commit) now runs under a dedicated,
  cross-process `flock` on `<root>/.frob/land.lock` -- a SEPARATE file from
  `frob.tickets._store.ledger_lock`'s `.frob/tickets.lock` (reusing that
  exact path was tried first: a worktree's own committed
  `.frob/tickets.lock`, picked up by `land`'s `git add -A` wip-commit/
  finalize-commit steps, collides by identical relative path with the
  untracked lock file `root`'s own lock would create, and git's
  squash-merge refuses outright rather than picking a side). A second
  `land()` against the SAME `root` blocks at the lock acquire instead of
  racing this one -- the fix for 6 REL001 version-number collisions from
  parallel branches in one session (two lands could previously both read
  the same pre-bump manifest version and each compute the same "next"
  version). `.frob/land.lock` is expected to be `.gitignore`d like every
  other `.frob/` path; `_porcelain_dirty` ignores anything under `.frob/`
  when deciding whether `root`/a worktree is "dirty" for exactly this
  reason.
- **Raw ticket-branch merges refused.** `frob.scaffold.
  install_worktree_lease_hook`'s `pre-merge-commit` hook (T-0431) now ALSO
  carries a second guard (`_FORBID_RAW_TICKET_MERGE_SCRIPT`): it refuses a
  real merge commit whose incoming side is a `worktree-agent-*` branch,
  from ANY shell -- including a coordinator's, which the T-0431 FROB_AGENT
  check deliberately exempts. Detects the incoming branch via
  `$GIT_REFLOG_ACTION` (git sets this to `merge <branch>` in every hook's
  environment; `.git/MERGE_HEAD` was tried first and observed, empirically,
  to no longer be readable by the time `pre-merge-commit` fires on a
  plain conflict-free merge under this git version/backend). `frob ticket
  land`'s OWN internal git calls never trip this hook in the first place --
  both its worktree-into-main merge (`--no-commit` then a later plain
  `git commit`) and its squash-apply (`git merge --squash`) suppress the
  automatic merge commit `pre-merge-commit` fires for; `FROB_LAND_INTERNAL=1`
  is offered anyway as an explicit, documented manual override, never set
  by `land` itself since it never needs it.

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

class Priority(StrEnum):        # T-0411: importance, independent of age
    LOW = "low"; MEDIUM = "medium"; HIGH = "high"; CRITICAL = "critical"

# PRIORITY_RANK: dict[Priority, int] -- LOW=0 .. CRITICAL=3, `doable`'s sort key

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

class AcceptanceCriterion(BaseModel):   # T-0572
    text: str                   # given/when/then prose
    evidence: tuple[str, ...] = ()   # evidence id(s) demonstrating this criterion

class TicketTier(StrEnum):      # T-0715: epic -> story -> ticket organization
    EPIC = "epic"; STORY = "story"; TICKET = "ticket"   # default TICKET

class Ticket(BaseModel):
    id: str                     # ^T-\d{4}$
    title: str
    state: TicketState
    kind: TicketKind
    origin: Origin
    created: date
    priority: Priority = Priority.MEDIUM   # T-0411: importance, doable's primary sort key
    blocked_by: tuple[str, ...]
    parent: str | None
    tier: TicketTier = TicketTier.TICKET   # T-0715: epic|story|ticket, default ticket
    sprint: str | None = None   # T-0715: free-form commitment label, e.g. "2026-W30"
    scope: tuple[str, ...]      # path globs and/or symrefs
    evidence: tuple[str, ...]   # pytest node ids or policy rule ids
    attachments: tuple[Attachment, ...]
    acceptance: tuple[AcceptanceCriterion, ...] = ()   # T-0572: each item bound to evidence
    component: str | None = None   # T-0454: which module/area (freeform)
    labels: tuple[str, ...] = ()   # T-0454: freeform tags, orthogonal to component
    body: str                   # markdown after frontmatter, verbatim

class TicketSpec(BaseModel):    # input to new_ticket; id/created assigned
    title: str
    kind: TicketKind
    origin: Origin
    priority: Priority = Priority.MEDIUM   # `frob ticket new --priority low|medium|high|critical`
    scope: tuple[str, ...] = ()
    blocked_by: tuple[str, ...] = ()
    parent: str | None = None
    tier: TicketTier = TicketTier.TICKET   # T-0715
    sprint: str | None = None   # T-0715
    acceptance: tuple[AcceptanceCriterion, ...] = ()   # `frob ticket new --acceptance TEXT` (repeatable)
    component: str | None = None   # `frob ticket new --component NAME`
    labels: tuple[str, ...] = ()   # `frob ticket new --label TAG` (repeatable)
    body: str = ""

class TicketQueue(BaseModel):
    tickets: Mapping[str, Ticket]
```

### Tiers: epic -> story -> ticket (T-0715)

`Ticket.tier` (`TicketTier`: `epic`/`story`/`ticket`, default `ticket`)
formalizes the dev-team organization already implicit in the `parent`
graph: an epic parents stories, a story parents leaf tickets. Two
structural rules follow mechanically from the tier, no separate
enforcement path per caller:

- `doable` (`frob ticket doable`) only ever surfaces `tier=ticket`
  tickets -- an epic/story is pure organization, never a directly
  dispatchable unit of work, even if it happens to carry no
  `blocked_by` of its own.
- `transition(..., TicketState.DONE)` (`frob ticket close`) refuses an
  `epic`/`story` ticket while any descendant (via the `parent` chain, any
  depth) is still open (`TicketError.OpenDescendant`) -- `epic_rollup`'s
  own parent-chain BFS is mirrored by a private `_open_descendant_ids`
  helper for this cheap open/closed check.

`frob ticket new --tier epic|story|ticket` sets it at creation.
`frob ticket tier <id> <epic|story|ticket>` (`set_tier`, T-1069) sets it
on an already-created ticket -- same single-writer, ledger-locked shape
as `frob ticket priority`/`kind`/`component`; the two structural rules
above key off whatever `tier` a ticket currently carries, so they apply
to the new value on the very next read, and `parent` links are not
re-validated or moved. Every pre-T-0715 ledger row has no `tier:` field
at all and loads as `tier=ticket` (a plain leaf), unaffected.
Mechanically backfilling existing `EPIC`-titled tickets to `tier: epic`
is a separate child ticket of T-0715 (T-0936, a one-time ledger
migration, not a code change) that this verb unblocks.

### Sprints (T-0715)

`Ticket.sprint` is a free-form commitment label (`"2026-W30"`,
`"sprint-14"`); `None` means uncommitted/backlog.

- `frob ticket new --sprint LABEL` sets it at creation.
- `frob ticket sprint assign <id> <label>` (`set_sprint`) sets/clears it
  on an existing ticket -- same single-writer, ledger-locked shape as
  `frob ticket component`.
- `frob ticket sprint show <label>` (`sprint_view`) lists every ticket
  committed to `label`, a `TicketState -> count` rollup, and `closed`
  (the done-count "velocity" number the mandate asked for) -- all
  derived from the tickets' current `state`, no separate tracked
  counter (the mandate's "no new storage" constraint).
- `frob ticket doable --sprint LABEL` restricts the doable queue to one
  sprint's commitment (a plain post-filter over `doable()`'s own result).
- `frob ticket doable --by-parent` groups the doable list by `parent`
  instead of one flat list -- a story's remaining leaves display
  together (the "pop-the-whole-stack, not just the top" concern).

**Velocity/burndown mined from git history (T-0938):** `sprint_view.
closed` above answers "how many are done right now" -- a snapshot of
CURRENT ledger state, not history. `frob.tickets.sprint_velocity(root,
queue, sprint)` answers the harder question the mandate also asked for:
"closed per sprint across the last N commits", a real burndown timeline.

Derivation source, decided honestly (no new storage was added):
`tickets.md` retains no transition-history field of its own, only each
ticket's CURRENT `state` -- so `sprint_velocity` mines it from `tickets.
md`'s own git history instead. It walks every commit that ever touched
the ledger (oldest-first, `git log --format=%H%x1f%aI -- tickets.md`),
reads each commit's `tickets.md` blob ONCE, and for every ticket
currently committed to the sprint checks whether that ticket's `state:`
value in this commit is `done` and differs from its previously observed
state -- each such flip is one `SprintTransition` (`ticket_id`, `sha`,
`committed_at`, `from_state`, `to_state`). A `git log -G<anchor>`
pickaxe restriction (mine only commits whose diff touches a ticket's
`<!-- ticket:ID -->` anchor line) was tried first and rejected: the
anchor line itself never changes across a state edit -- only the
`state:` line inside its block does -- so `-G` on the anchor
structurally misses every transition after a ticket's own creation
commit. The full walk is genuinely the correct approach here, not an
unoptimized shortcut.

This is real history, not a snapshot: unlike `sprint_view.closed`, a
ticket that was done and later reopened shows up as TWO transitions, and
every closure carries a real commit + timestamp usable as a burndown
chart's x-axis. `SprintVelocityReport` also reports `closed` (`len(
transitions)`), `remaining` (current non-done count), and `total`, for a
single-call summary shape that mirrors `SprintReport`'s.

Known, disclosed gaps of this derivation (accepted tradeoffs of "no new
storage", not bugs): (1) a ticket's CURRENT `sprint` label selects which
tickets to mine -- `tickets.md` does not retain sprint-REASSIGNMENT
history, so a ticket closed under a different sprint label before being
reassigned will not appear in either sprint's velocity; (2) if `tickets.
md` was ever squash-merged or hand-edited such that a `done` transition
never appears as its own commit, that transition is invisible to this
mining (git history is a lower bound on real-world transitions, not a
guarantee of completeness).

A CLI surface (`frob ticket sprint velocity <label>`, argparse + runner
wiring in `src/frob/__main__.py`/`src/frob/app/ticket_runner/`) is a
separate child ticket of T-0938 -- this ticket's own scope
(`src/frob/tickets/**`) is the derivation function and its models only.

### `frob ticket flow` (T-1100)

A simple queue-growth-vs-completion-rate report, reusing T-0938's mining
rather than adding a second one: `frob.tickets.ticket_flow(root, queue,
*, today=None)` builds one `TicketFlowRow` per calendar day from the
EARLIEST observed filing (`Ticket.created`, across the WHOLE queue, not
one sprint) or landing (`_mine_done_transitions` over every ticket id,
not `sprint_velocity`'s sprint-filtered subset) event through `today`
(defaults to `date.today()`, injectable for deterministic tests) --
zero-filled, never sparse, so a trailing-window average always covers a
real fixed-size span rather than silently skipping quiet days.

Each row is `(day, filed, landed)` plus a `net = filed - landed` property
(positive grows the queue, negative shrinks it). `TicketFlowReport` adds
the CURRENT open-ticket count (a live snapshot, not mined), the
trailing-3-day average net rate, and an `eta_days` property: `open_count
/ -trailing_net_rate` when the rate is genuinely NEGATIVE (net-shrinking),
`None` otherwise (a flat or growing queue has no meaningful burn-down
ETA) -- `frob ticket flow`'s render layer labels a `None` ETA as "cannot
estimate", never silently omits the line.

`frob ticket flow [--json]` (`_flow` in `src/frob/app/ticket_runner/
_mutate.py`) loads the active queue and prints exactly one table (day /
filed / landed / net) plus the open count, trailing rate, and ETA line --
"keep it genuinely simple" per the user request this closes. Shares
every known, disclosed gap `sprint_velocity`'s own docstring already
names (git history as a lower bound on real transitions, not a
guarantee of completeness), since it reuses the exact same
`_mine_done_transitions` mining, just unfiltered by sprint and bucketed
by day instead of listed as a flat transition sequence.

**T-1142 fix (archived tickets undercounted both sides):** the ACTIVE-
only `queue` `_flow` passes in (`load_active`) undercounted `landed` AND
`filed` for any ticket already moved out of `tickets.md` into `tickets-
archive.md` by `frob ticket archive` -- its id was simply absent from
`queue.tickets`, so `_mine_done_transitions` was never even asked to look
for its done-transition commit (which is still readable in `tickets.md`'s
own FULL git history, from before the archive-sweep commit removed the
ticket -- no separate `tickets-archive.md` mining is needed for the
landed side), and its `created` date was missing from the filed side the
same way. First real run (2026-07-28) showed `landed=0` for two days the
zero-drive record shows ~50 lands each, both followed by an archive
sweep. `ticket_flow` now unconditionally merges `tickets-archive.md`'s
own tickets (`load_archive`, best-effort -- a load failure degrades to
an empty archive view rather than blocking the whole report) into BOTH
the filed-by-day source and the landed-mining id set, regardless of what
view of the active queue the caller passed in -- so the CLI's
`load_active` call site needed no change at all. `open_count` still only
ever counts the caller's own `queue` (an archived ticket is always
done/dropped, never a member of `_OPEN_STATES`, so merging the archive in
cannot change that count either way).

### `--body-file`/`--acceptance-file` (T-0737)

`frob ticket new --body-file PATH` and `frob ticket new --acceptance-file
PATH` read the ticket body / acceptance criteria verbatim from a file
instead of the shell -- same rationale and precedent as `done-report
--why-file` (T-0458) and `scope --reason-file` above: long, multi-sentence,
or backticked/quoted/`$`-laden prose passed inline through bash risks
partial command substitution before frob ever sees it.

- `--body-file PATH` is mutually exclusive with `--body TEXT` (giving both
  exits 1); the file's contents become the ticket body verbatim (the
  ledger writer still strips a single leading/trailing run of blank lines
  from any body, file-sourced or not -- that normalization is unrelated to
  this flag and applies identically either way).
- `--acceptance-file PATH` is mutually exclusive with repeated
  `--acceptance TEXT` flags (giving both exits 1). PATH's contents are
  split into criteria as follows: if the file contains at least one blank
  line, each blank-line-separated block becomes one criterion (so a
  multi-sentence GIVEN/WHEN/THEN criterion may still wrap across several
  lines within its own block); otherwise (no blank line anywhere in the
  file) it degrades to one criterion per non-empty line. Each criterion is
  stripped of leading/trailing whitespace.
- Both are implemented in `frob.app.ticket_runner._resolve_new_body` /
  `_resolve_new_acceptance` / `_parse_acceptance_file` -- pure CLI-layer
  resolution, no change to `TicketSpec` or `new_ticket` itself.

### `frob ticket accept` (T-1029)

`frob ticket new --acceptance` was, until this ticket, the ONLY way to
attach an acceptance criterion to a ticket at all -- a ticket that needed
one added AFTER filing (T-0894's agent hit exactly this closing a
new-gate-rule ticket, per the before-fails/after-passes criterion that
gate's close check demands) had no CLI path and had to hand-edit
`tickets.md`, the single-writer violation `frob.tickets` otherwise
structurally prevents everywhere else.

`frob.tickets.add_acceptance(root, ticket_id, criteria)` appends each of
`criteria` as a fresh, UNBOUND `AcceptanceCriterion` (`evidence=()`) to the
ticket's EXISTING `acceptance` tuple -- it never touches or reorders what
is already there, only adds. Blank entries are dropped after `.strip()`
(matching `mutate_labels`'s comma-split posture); if nothing survives that
filter, `Err(TicketError.AcceptanceChangeEmpty)` -- the same "don't call
this for nothing" discipline `mutate_scope`/`mutate_labels` already
enforce, never a silent no-op write. Held under `ledger_lock` end to end
(T-0458 single-writer invariant), same as every other mutation here.

`frob ticket accept <id> --criterion TEXT... | --criterion-file PATH`
forwards to `add_acceptance` with nothing else re-derived at the CLI layer
(`frob.app.ticket_runner._mutate._accept`, same "this command does
nothing but forward" pattern as `_scope`/`_label`).
`--criterion-file PATH` reads criteria verbatim from a file using the
EXACT same blank-line-separated-block parser `--acceptance-file` already
uses (`_new._parse_acceptance_file`, T-0737, reused rather than
duplicated) -- mutually exclusive with repeated `--criterion TEXT` flags,
giving both exits 1.

```python

class AttachmentSource(BaseModel):
    path: Path | None           # None means clipboard

# T-0454: `frob ticket board`'s fixed column order
BOARD_STATES: tuple[TicketState, ...]  # QUEUED, PLANNED, IN_PROGRESS, BLOCKED, DONE, DROPPED

class BoardColumn(BaseModel):   # T-0454
    state: TicketState
    tickets: tuple[Ticket, ...] = ()   # priority-then-age ordered (_doable_sort_key)

class EpicRollup(BaseModel):    # T-0454
    epic: Ticket
    descendants: tuple[Ticket, ...] = ()   # every descendant via `parent`, any depth
    done: int = 0
    total: int = 0
    blocked_leaves: tuple[str, ...] = ()   # leaf (childless) descendants currently BLOCKED
    percent_complete: float          # property: done/total*100, or 0.0 if total==0

class SprintReport(BaseModel):  # T-0715: `frob ticket sprint show <label>`
    sprint: str
    tickets: tuple[Ticket, ...] = ()   # every ticket carrying this sprint label
    rollup: Mapping[TicketState, int] = {}   # state -> count
    closed: int = 0                  # done-count "velocity", derived from current state

class SprintTransition(BaseModel):  # T-0938: one mined `state: done` flip
    ticket_id: str
    sha: str
    committed_at: datetime
    from_state: str | None
    to_state: str

class SprintVelocityReport(BaseModel):  # T-0938: `sprint_velocity`'s history-derived summary
    sprint: str
    transitions: tuple[SprintTransition, ...] = ()   # oldest-first, a burndown timeline
    closed: int = 0        # len(transitions) -- history-derived, unlike SprintReport.closed
    remaining: int = 0     # current non-done count
    total: int = 0
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
    LabelChangeEmpty    = "label change requires at least one --add or --remove label"
    # T-1179: land-time ticket-scoped splice id/title-mismatch refusal --
    # see "Provisional ids" above for the incident this defense-in-depth
    # guard closes.
    IdTitleMismatch     = "landing block's id already exists on main under a different title"

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
<!-- frob:describes src/frob/tickets/_store.py::iter_raw_ledger_frontmatter -->

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
def ledger_lock(root: Path) -> Iterator[None]
    # T-0458: exclusive, blocking, cross-process lock (fcntl.flock on
    # _lock_path(root)) serializing EVERY ledger mutation -- write_ticket,
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
def iter_raw_ledger_frontmatter(text: str) -> list[tuple[str, dict]]
    # T-1132: every <!-- ticket:ID --> section's RAW (unvalidated)
    # frontmatter dict, tolerating one malformed YAML block by skipping
    # just that section (logged) rather than failing the whole scan --
    # unlike _parse_ledger, which is strict end to end. This is the read-
    # side complement `frob doctor`'s malformed-edge scan
    # (scan_malformed_ticket_edges) needs: Ticket.model_validate
    # deliberately does NOT reject a malformed blocked_by/parent entry, so
    # a strict loader cannot be doctor's data source for finding one
    # without risking the entire shared ledger's load failing the moment
    # a single bad edge exists anywhere in it.
```

## Worktree-lease guard (T-0431)

<!-- frob:describes src/frob/tickets/_worktree_guard.py::enforce_worktree_lease -->

**Incident:** a dispatched worktree agent's shell ran `git merge main`,
`make core`, and `frob ticket new` (minting T-0427) directly against the
SHARED main checkout instead of its own worktree -- the harness's Edit
tool scopes FILE edits to a worktree, but a stray bash command is not
caught by anything. This is the "hard to be careless" guard for the
dispatch layer: repo damage from a stray cwd should require deliberately
clearing a lease, not just happen.

```python
# frob/tickets/_worktree_guard.py
FROB_WORKTREE_ENV = "FROB_WORKTREE"

def enforce_worktree_lease(root: Path) -> Result[None, TicketError]
    # Err(WorktreeLeaseViolation) if FROB_WORKTREE is set AND root's actual
    # git top-level (repo_root, worktree-correct) does not match it.
    # FROB_WORKTREE unset (coordinator-run commands, or any environment
    # that never opted in) is Ok(None): unrestricted.
```

`FROB_WORKTREE=<abs path>` is a dispatcher-set env var naming the ONE
worktree an agent's shell is authorized to mutate frob's tracked ticket
state in. Every mutating `frob.tickets` entry point calls
`enforce_worktree_lease(root)` as its first statement and returns
`Err(WorktreeLeaseViolation)` immediately if it fails, before touching
the ledger at all: `new_ticket`, `transition` (covers start/close/
requeue/block/fail -- every state change goes through one place),
`add_evidence`, `add_cmd_evidence`, `set_done_report`, `record_failure`,
`attach`, `archive`, `renumber`, `renumber_one`. `frob.gates`'
`stamp_baseline`/`stamp_coverage` (`--stamp-baseline`/`--stamp-coverage`)
carry the same guard, mapped to `GateError.WorktreeLeaseViolation` --
these also write tracked repo state (`.frob/baseline`,
`.frob/coverage-stamp`) an agent could otherwise stamp against the wrong
checkout. Read-only commands (`check --ticket`, `show`, `list`, `doable`)
never call this guard and remain unrestricted anywhere.

**A coordinator process is unaffected by design**: landing worktree
changes onto main, or any other coordinator-run mutation, runs with no
`FROB_WORKTREE` set, so `enforce_worktree_lease` is `Ok(None)` -- a no-op.
The guard's whole job is catching an AGENT shell that wandered outside
its assigned worktree, not restricting the coordinator's own legitimate
cross-checkout work.

T-0973: `enforce_worktree_lease`'s `FROB_WORKTREE_ENV` read carries a
`frob:waive SEC110 reason="..."` -- it is a worktree-lease path marker,
not a secret.

**Git hook (defense in depth).**
`frob.scaffold.install_worktree_lease_hook(root, *, force=False)`
(docs/commands/scaffold.md) installs `pre-commit` and `pre-merge-commit`
hooks into `root`'s real hooks directory (`git rev-parse --git-path
hooks`, worktree-correct) that abort loudly whenever `FROB_AGENT` is set
non-empty in the shell running the commit -- catching a stray raw `git
commit`/`git merge` an agent shell ran directly, independent of whether
it went through `frob.tickets` at all. `FROB_AGENT` is a SEPARATE env var
from `FROB_WORKTREE` (an agent-context marker, not a specific worktree
path) since the hook only needs to know "is this shell an agent," not
which worktree it should have been in -- the git hook fires from
whichever checkout the raw git command happened to run in. Refuses to
overwrite an existing hook file without `force=True`.

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
- CLI: `frob ticket new|list|show|doable|brief|plan|start|requeue|sweep|
  migrate|renumber|attach|block|close|fail|drop|evidence|done-report|
  archive|sprint`. `sprint assign <id> <label>`/`sprint show <label>`
  (T-0715) set/read a ticket's sprint commitment -- see "Tiers"/"Sprints"
  below. `brief <id>` (T-0568) prints the full mission briefing (see
  "`frob ticket brief` (T-0568)" above). `start`
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
  later as COV003 after close); `drop <id> --reason TEXT [--absorbed-by
  T-####]` (T-0579) transitions to DROPPED with a dated reason line under
  `## Drop reason`, replacing the pre-T-0579 hand-edit workflow (see "State
  machine" above); `archive` moves every done/dropped ticket
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
  T-0754: the CLI also captures a `### Captured claims` section -- a test
  count from ACTUALLY RUNNING the ticket's own non-`cmd:` evidence ids
  (`_run_tests_count_fn`, reusing D-01's real-run verification) and a
  `(errors, warnings, waived)` gate-state COUNT from a fresh `python -m
  frob check --ticket <id>` spawn (`_check_gates_summary_fn`, parsed from
  the `gate-summary` line's own leading integers) -- never typed by the
  agent, and deliberately never that line's raw text: its trailing
  `[archgate=7.99s, ...]` per-gate timing blob differs on every single
  invocation even against an unchanged tree, which is what a strict
  string-equality land re-verification against it looked like at first
  (T-0754 review round 2's FATAL finding -- it refused every land,
  including this ticket's own; fixed by capturing the counts, never the
  line). This closes the "the Done report is the ONLY pipeline artifact
  that is unverified free prose" gap (T-0572's 142-reported-as-145
  incident, T-0710/T-0724's undisclosed gate state): evidence ids resolve,
  scope binds, the diff is real, but test-count and gate-state CLAIMS used
  to be retyped from memory. `frob ticket land` re-runs the same two
  captures against the post-merge tree (`land`'s `passed`/`check_gates`
  callables -> `_reverify_done_report_claims_post_merge` -- the test-count
  half is DERIVED from `passed`'s own D-05 run, no second collect+run) and
  refuses the land (`LandError.ClaimDivergence`) if the real test count or
  `gate_errors` no longer match -- `gate_warnings`/`gate_waived` are
  recorded for a human reader but never gate the land, since a repo-global
  warning/waived count legitimately drifts on a busy shared branch for
  reasons unrelated to this ticket's own work. This is the general form of
  D-05's evidence re-verification applied to the claims themselves, not
  just the evidence ids. A Done report with no Captured claims section
  (predates T-0754, or the library `set_done_report`/`land` callers that
  omit the capture callables) is unaffected: there is nothing recorded to
  diverge from, so it lands exactly as before. `parse_claims_from_done_
  report` is anchored to the `### Captured claims` heading itself -- a
  free-prose narrative line elsewhere in the Done report that happens to
  match the claim shape can never masquerade as a captured, re-verified
  claim.
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
