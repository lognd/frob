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
`_write_ticket_unchecked` (`frob.tickets._store`, private -- test-fixture-
only, never a production write path) skips the content-loss check
ENTIRELY, no warning at all, and says so plainly at the call site instead
of `write_ticket` itself needing a weaker default to accommodate it. Every
fixture that previously relied on the old warn-and-proceed default (the
`splice_ledger` merge-preference tests in `tests/test_ticket_land.py`, the
`TICK005` land-regression simulation tests) now calls `_write_ticket_
unchecked` explicitly. `strict_no_content_loss=False` still exists as an
explicit, disclosed opt-out (same warn-and-proceed behavior as before) for
a caller with a specific reason to want it, but no production call site in
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

## `frob ticket land`

<!-- frob:describes src/frob/tickets/_land.py::land -->
<!-- frob:describes src/frob/tickets/_land_ledger_merge.py::splice_ledger -->
<!-- frob:describes src/frob/tickets/_land_squash.py::_assert_land_complete -->
<!-- frob:describes src/frob/tickets/_land_squash.py::_worktree_full_changeset -->
<!-- frob:describes src/frob/tickets/_land_release.py::_apply_release_bump -->
<!-- frob:describes src/frob/tickets/_land_release.py::_maybe_rebuild_natives -->
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
         sync_gate_rules: Callable[[Path, str], Result[tuple[str, ...] | None, LandError]] | None = None,
         check_gate_claims: Callable[[Ticket], bool | None] | None = None) -> Result[LandReport, LandError]
    # T-1410: `check_gate_claims(ticket)`, when supplied, re-verifies every
    # acceptance criterion shaped "0 <RULE> findings under <glob>"
    # (frob.tickets._evidence._gate_claim_criteria) against the POST-MERGE
    # worktree tree and refuses the land (ClaimDivergence, reused rather
    # than adding a new LandError variant) when it returns False -- the
    # T-1276 defect this closes: a criterion phrased this way used to be
    # satisfiable by ANY bound evidence id, and T-1276 itself closed done
    # and landed (LAND-PROOF verified) against 116 live TEST005 findings
    # under its own criterion's glob, because nothing ever computed this.
    # Defaults to `None` (skip) for the same cycle-avoidance reason as
    # collected/passed/covers_scope; `frob ticket land` supplies it by
    # default (`ticket_runner._land_gate_claims_fn`, which reuses
    # `_close_gate_claims_for_ticket`'s exact computation against the
    # worktree).
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
    # T-1358: `_apply_release_bump` (called from inside `land` for the
    # `bump_version` step) now runs an UNCONDITIONAL final coherence check
    # (`_ensure_release_quartet_coherent`) comparing pyproject.toml's
    # on-disk version against `.frob-release.json`'s on-disk version,
    # regardless of what `bump_version` itself reported back -- closing a
    # gap the T-1078 resync left open: that resync only fires inside the
    # `bumped.danger_ok is not None` branch, so a callback that reports
    # `Ok(None)` (or a manifest write that silently failed) could still
    # leave the quartet desynced (the real T-1340 incident: pyproject.toml
    # bumped 0.289.0 -> 0.290.0 on main, `.frob-release.json` left at
    # 0.289.0, blocking every subsequent land on the T-0992 monotonicity
    # guard until a coordinator hand-reconciled). The new check force-
    # resyncs the manifest to pyproject.toml's value whenever the two
    # on-disk files disagree, as the very last step before `_apply_release_
    # bump` returns.
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
2.5. **Refuse on an out-of-scope, undeclared uncommitted `frob:waive`
   deletion** (T-1323): before ANY git mutation -- strictly before the
   wip-commit in step 3 that would otherwise fold a dirty worktree's
   edits into the merge unattributed -- `_check_uncommitted_waive_
   deletions` diffs the worktree's UNCOMMITTED state against `HEAD` for
   any deleted `frob:waive` comment line. A deletion whose file is
   neither covered by the ticket's `scope` nor named (file or rule) in
   its Done report refuses loudly (`Err(OutOfScopeWaiveDeletion)`,
   remedy: add the file to scope or name it/the rule in the Done report
   if intentional, `git checkout -- <file>` in the worktree if
   accidental). This is the 2026-07-29 incident's own laundering path: a
   wip-snapshot commit is not supposed to be a way to smuggle
   unattributed repo-wide edits onto main, and nothing before this check
   ever inspected what a wip-commit was about to capture. See
   docs/modules/gates.md's Tier-A section for the companion `WAIVE004`
   auto-fix guard this incident also produced.
2.6. **Tier-A auto-fix crash recovery** (T-1348). Before `land()` (the
   function documented by this numbered list) is ever called, `frob
   ticket land`'s CLI layer (`_absorb_pre_land_fixes`, T-1175) already ran
   `frob fmt`, `frob sys sync-interface`, and every Tier-A `--fix` handler
   (`apply_tier_a_fixes`, `src/frob/gates/_fix_engine.py`) directly against
   the worktree, on disk, with NO commit of any kind yet -- this step's
   own wip-commit (step 3 below) is the FIRST commit that captures any of
   it. A `frob ticket land` process killed during that window (a real
   incident, T-1338: a timeout mid-Tier-A left
   `src/frob/gates/_debt_deprecated.py` GARBLED, a half-applied rewrite,
   and the obvious `git checkout -- <file>` recovery then silently
   destroyed an unrelated uncommitted test in a DIFFERENT file) used to
   leave the tree in a state that was neither the pre-fix nor the
   post-fix original. T-1348 closes this two ways, entirely inside
   `apply_tier_a_fixes` and its handlers (`src/frob/gates/_fix_engine.py`)
   -- `_land.py`'s own step 3 wip-commit timing is UNCHANGED, since moving
   it earlier would require reordering `_absorb_pre_land_fixes` and
   `land()` at their call site (`src/frob/app/ticket_runner/_land_cmd.py`,
   a different ticket's scope):
   - Every Tier-A handler that rewrites a file in place now does so via
     `_write_text` (temp file + `fsync` + `os.replace` in the same
     directory, reusing `frob.tickets._store.atomic_write`'s existing
     T-0456 primitive) instead of a bare `path.write_text(...)`. A kill at
     ANY point up to and including the moment before the `os.replace`
     swap leaves the ORIGINAL file's bytes on disk, untouched -- there is
     no window in which the tracked path itself is half-written.
   - `apply_tier_a_fixes` writes `.frob/land-autofix-manifest.json`
     (`write_autofix_manifest`) after EVERY handler completes, not once at
     the end, listing every distinct file path any handler has rewritten
     SO FAR in the current run; it is cleared (`clear_autofix_manifest`)
     only once the whole pass finishes successfully. A process killed
     partway through the handler loop leaves this manifest naming exactly
     what Tier-A actually touched up to that point -- a recovering agent
     diffs `git status --porcelain` against the manifest's `rewritten_
     paths` list instead of a blanket `git checkout --` that cannot tell
     "Tier-A garbled this" from "my own uncommitted work is in this
     other file", the exact ambiguity that caused the T-1338 data loss.
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

    **T-1760 recompute-not-carry fix**: none of `pyproject.toml`/
    `CHANGELOG.md`/`.frob-release.json` is protected by `ticket.scope`,
    so `git merge --squash` can resolve a change to any of them CLEANLY
    (no conflict object at all -- `_auto_resolve_out_of_scope_conflicts`
    only ever fires on a genuine git conflict) by taking the worktree's
    side, if the worktree's own copy differs from root's current HEAD in
    a way git's 3-way merge does not treat as contested. When that
    happens, root's working tree can already hold a REGRESSED version/
    manifest before `_apply_release_bump` ever runs -- and, critically,
    the T-0992 monotonicity guard above only ever validates a bump
    `bump_version` itself REPORTS (`bumped.danger_ok is not None`); a
    `bump_version` callback that legitimately reports `Ok(None)` (this
    land's own diff needs no new bump) left that regression completely
    uncontested, since `_ensure_release_quartet_coherent`'s own check
    only compares the two ALREADY-regressed files to EACH OTHER, which a
    self-consistent stale pair passes trivially. Measured on main across
    four consecutive lands (T-1692/T-1754/T-1755/T-1756): the version
    oscillated 0.366.0 -> 0.365.0 -> 0.366.0 -> 0.365.0, with the
    REL001 baseline manifest regressing right along with it -- silently,
    since the version string going backwards was the only visible
    symptom.

    `_reset_release_artifacts_to_pre_land` now runs UNCONDITIONALLY, as
    the very first step of `_apply_release_bump`, before `bump_version` is
    even invoked: `git checkout <pre_land_tip> -- pyproject.toml
    CHANGELOG.md .frob-release.json` discards whatever the squash carried
    for these three files and resets them to root's own true, last-
    committed state. This is RECOMPUTE, NOT CARRY -- the bump is a
    function of (root's manifest, the landing API) and is now always
    evaluated from root's own pre-land state, never from anything a
    worktree happened to bring along, closing the regression class at its
    source rather than only detecting it after the fact. `_assert_no_
    monotonicity_regression` runs as an unconditional final check
    afterward (even on the `Ok(None)` branch) as belt-and-braces defense
    in depth, comparing the working tree's final versions against
    `pre_bump_version`/`pre_manifest_version` via `_version_not_regressed`
    (the `>=` sibling of `_release_bump_is_monotonic`'s strict `>`, since
    "unchanged" is the CORRECT outcome on a no-bump-needed land) --
    refusing and unwinding the squash if it ever fires, which after the
    reset above should never happen in practice.
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

## Frob ticket land --plan (T-1269)

<!-- frob:describes src/frob/tickets/_land.py::land_plan -->

`frob ticket land <id>` requires a closeable WORKED ticket (evidence +
Done report, `_validate_closeable`) -- a design-phase worktree that only
carries docs plus ledger changes (a planning pass that filed several draft
tickets but closed none of them) has no such ticket to land under. Before
T-1269, landing one of these required manual coordinator surgery: a
guarded plain `git merge` (`FROB_LAND_INTERNAL=1`) plus a hand-assigned
`frob ticket renumber <draft> <next-id>` call PER incoming draft --
observed costing 15 hand-assigned renumbers across 4 batches landing four
planner worktrees in one drive.

`frob ticket land --plan --worktree PATH [--dry-run]`
(`frob.tickets.land_plan`) does the whole chain atomically instead:

1. Refuse if `root`/`--worktree` are the same path, or `root` has any
   uncommitted change (the same two `land()` preflight checks, reused
   verbatim).
2. Merge `--worktree`'s branch onto `root`'s current branch (`git merge
   --no-ff` -- never a squash; there is no single worked ticket to squash
   under, unlike `land`'s own per-ticket path). Any `tickets.md` conflict
   splices via the registered git merge driver
   (`docs/modules/tickets.md#git-merge-driver`) the same way an ordinary
   `git merge`/`pull` already would -- `land_plan` performs no ledger
   surgery of its own. A real conflict `git merge --abort`s (nothing was
   committed yet) and refuses with `LandError.MergeConflict`.
3. Finalize EVERY draft id (`is_draft_id`) now present in `root`'s merged
   ledger to the next free real id, one `finalize_draft` call each
   (T-0162's existing allocator-locked next-id computation -- never a
   hand-assigned id), then commit the rewrite in one
   `chore(tickets): land --plan finalize ...` commit.
4. Optionally re-check the TICK gate via an injected `check_ticks()`
   callable (`frob ticket land --plan`'s CLI supplies `frob check --only
   tickets`, cycle-avoidance-consistent with `land`'s own `check_gates`/
   `covers_scope`/etc. -- `frob.tickets` cannot import `frob.gates`
   directly, docs/rework.md) -- a non-clean result refuses with
   `LandError.PlanTickGateDirty`.

On ANY failure after the merge (step 3's finalize, or step 4's TICK
re-check), `root` is `git reset --hard`ed back to its pre-merge tip -- no
half-merged ledger, no partially-renumbered draft survives. `dry_run=True`
runs the merge and finalize exactly as a real call would, then always
`git reset --hard`s back regardless of outcome, returning the
`LandPlanReport` of what WOULD have happened. The whole chain runs under
`root`'s `_land_lock` (T-0577, the same cross-process lock `land()` uses),
so a concurrent `land()`/`land_plan()` call against the SAME `root` blocks
at the lock acquire instead of racing this one.

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
   own evidence test ids as the kill command, each mutant capped at 30s
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

**The sweep has a real wall-clock budget (T-1727).** Before this,
`_MAX_FILES * _MAX_MUTANTS_PER_FILE * _TIMEOUT_S` (up to 720s) was a
worst-case ceiling nobody actually enforced as a deadline -- a bound
evidence test that itself spawns real subprocesses (a watchdog test,
say) could push the true wall-clock well past a caller's own foreground
timeout, and the sweep had no way to stop early or say so: the
documented incident is ten consecutive 540s `frob ticket close` timeouts
(~90 minutes) that produced no result at all, with the agent's only
visible escape being to unbind its own slowest (and most adversarial)
tests. `check_ticket_mutation_evidence`'s `sweep_budget_s` (default:
`_sweep_budget_s()`, itself `FROB_MUTATION_SWEEP_BUDGET_S`-overridable,
90s out of the box) is a SINGLE deadline shared across the whole
sweep -- every file, every mutant -- computed once at the top of the
call and threaded down through `run_mutations`'
`deadline_monotonic`/`_run_mutants`'s per-mutant check. A file whose
mutants could not all be attempted before the deadline, or one never
even started because an earlier file already spent the whole budget, is
reported as `ConfirmatoryFinding(unmeasured=True, ...)` -- a DIFFERENT
outcome from a genuine confirmatory-only finding (`unmeasured=False`,
the pre-existing shape): nothing was proven weak, nothing was run long
enough to prove anything at all. `frob.gates._mutation_evidence
._test016_unmeasured_message` gives this its own wording so a human or
agent reading the finding never mistakes "could not measure" for
"measured and failing" (T-1703's exact lesson, same shape as a budget-
truncated `frob check` misread as clean). `_run_mutants` also logs one
INFO line per mutant attempted (`mutant N/M of <file>`), so a long sweep
is visibly progressing rather than indistinguishable from a hang --
requirement 3 of T-1727, directly answering "is this still working or
did it wedge?" the ten-timeout incident could never answer.
Deliberately NOT fixed by raising the timeout: the cost is
multiplicative in mutants x test time, so a bigger constant only
postpones the same wall -- the fix is an internal deadline that reports
an honest partial result, not a bigger one that still eventually runs
out with nothing to show.

**Bind-time cost projection (T-1727 requirement 2).**
`frob.tickets._evidence._warn_bind_time_mutation_sweep_cost`, called
from `add_evidence` right after a successful write, projects the SAME
close-time sweep cost the deadline above enforces -- one bounded timing
run of the ticket's full bound evidence-id set (capped at `_TIMEOUT_S`,
the same per-mutant budget the real sweep uses) times the planned mutant
count for the ticket's diff-touched files (a cheap, subprocess-free
`generate_mutants` count) -- and logs a WARNING naming the bound test
ids and the projected seconds when that projection exceeds the sweep
budget. This moves the discovery point from close time (an hour of work
later, when unbinding the slow-but-honest test is the only escape an
agent can see, T-1733's own incentive problem) to bind time (seconds
after `frob ticket evidence`, while rebinding/splitting/speeding up the
test is still cheap). Best-effort and advisory only: any failure (no
touched files yet, exec disabled, an unresolvable diff) degrades to a
silent no-warn, and it never affects the evidence write it runs after.

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
any git mutation): as of T-1518, only a `security`-kind ticket runs the
mutation subprocess SYNCHRONOUSLY here and can still refuse the land on
an ERROR-severity TEST016 finding (`LandError.EvidenceConfirmatoryOnly`).
Every other kind's TEST016 obligation (including `bug`-kind, previously
also synchronous+blocking) is deferred: `_check_mutation_evidence`
enqueues a `frob.tickets._mutation_sweep_queue.SweepEntry` instead of
running the mutation subprocess inline, and does NOT block the land for
it -- see "Batch mutation-evidence sweep (TEST016, T-1518)" below.
BUG002 (`bug_repro_violations`) is unaffected by this change and stays
synchronous+ERROR-always for bug/security kind on every land, deferred
kind or not -- it is cheap (re-runs already-bound evidence against a
single prior commit, no mutation subprocess) and proves a different
property. `frob ticket land --skip-mutation-evidence` (AppConfig
`ticket_skip_mutation_evidence`, default off) is the documented escape
hatch for the still-synchronous `security`-kind path: the check still
runs and logs its findings at WARNING, it just cannot refuse the land.
Deliberately NOT part of `frob.check`'s `test_gate`/`_ALL_GATES` snapshot
pipeline (`frob.check` is out of this ticket's scope): every other TEST
rule is a pure function of the graph snapshot, safe to run on every `frob
check` invocation; this rule spawns real bounded subprocesses per ticket,
which would violate the "must not slow the default `frob check` path for
tickets that never opt in" guard if it ran unconditionally there.

### Batch mutation-evidence sweep (TEST016, T-1518)

<!-- frob:describes src/frob/tickets/_mutation_sweep_queue.py::enqueue_pending_sweep -->
<!-- frob:describes src/frob/tickets/_mutation_sweep_queue.py::run_pending_sweep -->

TEST016's mutation subprocess is the single most expensive, least
incremental land stage (2026-08-04 dev-cycle review) -- its marginal
per-ticket value is test-strength validation, not main-correctness, so
running it synchronously on every land does not pay for itself except for
`security`-kind tickets. `frob.tickets._mutation_sweep_queue` moves the
rest of that work off the per-land critical path onto a batch/nightly
cadence:

- **Enqueue.** `_check_mutation_evidence` calls `enqueue_pending_sweep(
  worktree, ticket.id, base_ref, ticket.kind)` for any kind outside
  `SYNC_BLOCKING_KINDS` (`{security}`) instead of running the mutation
  subprocess inline. This appends a `pending` `SweepEntry` to
  `.frob/mutation-sweep-queue.json`, guarded by the same `fcntl`-advisory-
  lock discipline `frob.tickets._land_queue` (T-1345) already established
  for `.frob/land-queue.json` -- a separate file, a separate lock, same
  pattern.
- **Batch run.** `run_pending_sweep(root)` processes every `pending`
  entry: re-runs `check_ticket_mutation_evidence` against `root`'s
  current tree and the entry's recorded `base_ref`, then marks the entry
  `swept`. Never mutates the original ticket's state and never blocks
  anything retroactively. A `bug`-kind entry (the one deferred kind that
  used to promote TEST016 to ERROR) whose batch run still finds
  confirmatory-only evidence files a NEW `bug`-kind ticket
  (`origin=agent`) naming the offending land, so the finding re-enters
  the normal doable-ticket queue instead of vanishing into a log line.
  Every other kind's confirmatory-only finding is logged at WARNING only,
  matching `mutation_evidence_violations`' own WARN severity for those
  kinds.
- **Cadence.** `frob ticket land --drain` (T-1444's merge-queue drainer)
  calls `run_pending_sweep` automatically after draining every queued
  land -- the natural batch boundary the ticket body names. A standalone
  `frob ticket land --run-mutation-sweep` CLI flag (AppConfig
  `ticket_land_run_mutation_sweep`) runs the same batch pass without
  `--drain`, for a deployment (e.g. a nightly cron) that never calls
  `--drain` at all.
- **Visibility.** `pending_sweep_count(root)` returns how many entries
  are currently `pending`, for a caller that wants queue depth without
  mutating anything.

**Also wired into `frob ticket close` (T-0844)**, the direct non-land
close path: `frob.app.ticket_runner._close` computes the same
`mutation_evidence_violations` check against the CURRENT checkout (there
is no separate worktree/base_ref split on this path, so it runs against
`root` as both the tree scanned and the diff base's own checkout -- see
`_close_mutation_evidence_for_ticket`) and passes the ERROR/no-ERROR
verdict to `transition(..., mutation_evidence=...)`, which
`_done_transition_guard` enforces the same way `_check_mutation_evidence`
does at land (`Err(TicketError.EvidenceConfirmatoryOnly)`). `frob ticket
close --skip-mutation-evidence` (AppConfig
`ticket_close_skip_mutation_evidence`, default off) is the close-path
twin of land's escape hatch: the check still runs and logs its findings,
it just cannot refuse the close. A security/bug-kind ticket can no longer
dodge this obligation by closing directly instead of landing.

**T-1438 fix: the diff/repro base is the merge-base with `main`, not
`current_branch(root)`.** The base ref this check diffs/repros against
used to be `current_branch(root)` -- in a dispatched worktree agent's
normal flow that resolves to the WORKTREE'S OWN branch, which by close
time already carries the ticket's own fix commit at its tip. BUG002's
`_bug_repro_outcome_at_ref` then ran `git worktree add --detach <scratch>
<that-branch>`, checking out the FIX itself rather than the pre-fix
parent, so the designated repro test trivially "passed at parent" for
every single bug-kind ticket closed this way -- forcing
`--skip-mutation-evidence` on every bug-kind close, not just genuine false
positives. `_close_mutation_evidence_for_ticket` now resolves
`frob.gitio._merge_base(root, base_ref)` (`base_ref` defaults to `"main"`,
threaded from `cfg.ticket_base_ref`) and diffs/repros against THAT commit
instead -- the ticket's true starting point, mirroring the same
merge-base computation `working_diff` already performs internally.
`frob ticket land`'s own precheck (`_land_precheck` /
`_resolve_main_branch_for_land`) does NOT share this defect: there,
`root` is the actual main checkout being landed INTO (not the worktree
being landed), so `current_branch(root)` correctly resolves to `main`
itself, not to the ticket's own branch.

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
`frob:waive` comment grammar and the `.strata` `waive` clause grammar),
OR (T-1559) a waiver `follow_up=` attribute -- WIRE001/WIRE002's own
binding, the SAME "this ticket is still cited as live tracker" hazard
for a different waiver family. T-1559's own incident: T-1490/T-1488
landed and closed on 2026-08-05 while 16 `frob:waive WIRE001 ...
follow_up="T-1490"`-shaped directives still bound them; WIRE002 (only
enforced at `frob check` time, not at close/land) caught it one check
too late, turning main red with 16 orphan errors nobody was warned about
at close time -- the exact T-0605 shape this preflight already existed
to close for `ticket=`, now folded into the same scan/pattern rather
than a parallel mechanism. A
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

**Left-anchored patterns, and the ledger excluded from the waiver grep
(T-1633).** The waiver alternatives (`ticket=`/`ticket "..."`/
`follow_up=`) originally had a right-hand word boundary but no left-hand
one, so `ticket=T-0605` matched as a SUBSTRING of any longer identifier
ending that way -- `active_ticket=T-0605` in ordinary Done-report prose
read as a citation and refused a land twice (2026-08-06, T-1582) before
the id in question was even the citing pattern's actual target.
`_WAIVER_TICKET_PATTERN` is now left-anchored with an explicit
leading-character alternation, `(^|[^A-Za-z0-9_.-])`, rather than a
lookbehind -- the pattern is handed to `git grep -E` (POSIX ERE), which
has no lookbehind support at all. Separately, the waiver grep now
EXCLUDES `tickets.md`/`tickets-archive.md`/`tickets/**`
(`_WAIVER_PATHSPEC`) entirely: a real `frob:waive ... ticket=`/
`follow_up=` directive is a source-code comment and never legitimately
appears in the ledger, where every occurrence is narrative -- a Done
report quoting the very pattern that misfired, or an incident write-up
describing this class of bug (the ticket text you are reading right now
is exactly that shape, and an earlier revision of it WAS itself flagged
and refused the land describing the fix -- a self-demonstrating
instance of the underlying problem). The registry-disposition grep is
unaffected -- a registry YAML row is structured data, not narrative
prose, so no analogous exclusion applies there.

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
  main's side still wins. **T-1721 replaced this Done-report-only special
  case with a general base-aware comparison** -- see "Sibling ledger
  edits, carried forward or refused (T-1721)" below; it did not generalize
  on its own, see that section for why.
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

## Sibling ledger edits, carried forward or refused (T-1721)

The T-0577 Done-report preservation above closed ONE shape of the
T-0479-scoping cost (a sibling's Done report silently erased); a
different shape of the SAME cost went unnoticed for a full session
afterward: `_splice_only_ticket`'s blanket "every sibling id comes from
main untouched" default also silently discards a worktree's genuine
EDIT to a sibling ticket's OWN section whenever that edit does not
happen to change Done-report presence -- an evidence-list rebind (e.g.
`frob ticket evidence <other-id> --replace OLD NEW`, made in the same
worktree while landing a DIFFERENT ticket) is invisible to
`_preserve_sibling_done_reports`'s narrower check.

**Field incident.** T-1637 (a DONE, unrelated ticket) needed its
evidence rebound after T-1679 renamed the tests it cited. The rebind was
made correctly, in the same worktree, and verified locally -- and then
silently vanished, THREE separate times in a row, regardless of which
ticket's land was carrying it (T-1679's own land, a dedicated follow-up
ticket T-1714 filed specifically to re-fix it, and T-1706 after that) --
because `_splice_only_ticket` never even considered T-1637's section for
anything but a wholesale main-wins overwrite. The pattern was diagnosed
as structural only after the third silent loss.

**Why T-1154's fix did not cover this.** T-1154 already threaded a true
merge-base 3-way comparison into the TICKETS-ARCHIVE.MD splice for
exactly this class of problem -- but that fix's own docstring explicitly
reasoned tickets.md's OWN scoped splice "does not need this" because
"`ticket_id`-scoping (T-0479) already makes every sibling id come from
`main_text` untouched". That is a true description of T-0479's
mechanism and a wrong justification: the untouched-by-default behavior
IS the bug, not a reason base-awareness is unnecessary. T-0577's own fix
generalized only as far as the ONE incident shape it was built to close
(Done-report presence), not to arbitrary sibling content changes.

**Fix.** `_carry_forward_or_refuse_sibling_edits`
(`frob.tickets._land_ledger_merge`) replaces the narrow Done-report-only
check with a full base-aware 3-way comparison, when a `base_text`
snapshot (the true merge-base's `tickets.md`, resolved via the same
`_true_merge_base` + `_read_text_at_ref` pattern T-1154 already
established for the archive file) is available -- now threaded into
BOTH `_splice_and_stage` call sites: the pre-squash `_merge_main_into_
worktree` stage and the FINAL `_squash_and_splice_ledger` stage that
actually lands on main. For each sibling id, comparing main's current
copy, the worktree's copy, and the common base's copy:

- worktree unchanged since base: main's copy stands (the ordinary,
  already-correct T-0479 case).
- worktree changed, main unchanged since base: the worktree made a real,
  isolated edit main never touched -- carried forward. This is the
  T-1637 shape.
- both sides changed but converged to the same content: nothing to do.
- both sides changed to DIFFERENT content: neither side is stale -- both
  made a real, independent edit since the same base. This is the case
  the OLD `_newer` richness heuristic (T-0682/T-0764: state-rank, then
  Done-report/evidence/acceptance richness, never raw content) could not
  actually answer -- a same-rank, same-richness divergence fell through
  to an arbitrary positional tiebreak that silently discarded whichever
  side lost. Per the explicit design constraint driving this fix:
  silently choosing is the bug, not WHICH side gets chosen. Refused
  instead (`Err(TicketError.SiblingLedgerEditConflict)` /
  `LandError.SiblingLedgerEditConflict` at the land layer), naming the
  conflicting id, so an operator resolves the real conflict by hand (or
  lands the sibling ticket on its own first) instead of a land quietly
  deciding it for them.

`base_text=None` (git could not resolve the true merge-base, or its
ledger text failed to parse) degrades to the pre-T-1721
`_preserve_sibling_done_reports` heuristic exactly as before -- never a
hard failure just because the sharper comparison was unavailable this
once.

## Land exclusivity lease (T-1619)

`_land_lock`'s `flock` (T-0577, "Land hardening" above) only ever
serialized `land()` against ANOTHER `land()` call -- it said nothing to
any OTHER ledger-writing verb. Real incident, 2026-08-05: `frob ticket new`
auto-commits the ledger (T-1130); running it while a land was staging
moved `root`'s tip mid-run, and `_verified_reset_root`'s drift guard
(T-0907) correctly refused to unwind rather than risk destroying the
concurrent commit -- but that left the land's staged REL001 bump (four
files) dangling with no disclosure of what, specifically, was left
behind. It happened three times in one session to an operator actively
trying to avoid it.

Two fixes, both scoped to this repo's actual ledger-commit choke point
(`frob.tickets._leases._add_and_commit_tickets_md` -- the single function
`commit_ticket_ledger_change`/`commit_start_transition` both funnel
through, so `new`/`close`/`drop`/`fail`/`requeue`/`block`/`start`/
`evidence`/`done-report` are all covered by one guard, not nine separate
ones):

- **`refuse_if_land_in_progress(root)`** (`frob.tickets._leases`) probes
  `root`'s `LAND_LOCK_REL` (`.frob/land.lock`, the SAME file `_land_lock`
  holds -- the path constant now lives in `_leases`, and
  `frob.tickets._land` imports it, so both sides of the check share one
  literal, never two independently-defined copies that could drift) with
  a non-blocking `flock` acquire-then-release attempt. Failing to acquire
  means a land is genuinely alive holding it right now; succeeding (or
  finding no lock file at all) means it is safe to proceed.
  `_add_and_commit_tickets_md` calls this before ever running `git add`,
  so a refusal touches nothing -- the caller's own working-tree write (a
  freshly filed ticket, a `--evidence` addition) stays uncommitted for a
  later retry, but no commit races the land's.

  Crash-safety comes from the primitive itself, not a second liveness
  layer: POSIX `flock` is released by the kernel the instant its holding
  process exits, by any means including `SIGKILL` -- there is no "dead
  holder, lock still held" state to probe for, unlike a plain on-disk
  lease file (`_probe_worktree_liveness`'s confirmed_absent/ambiguous
  split exists precisely because a directory does not vanish just because
  its creating process died; a kernel-held advisory lock has no such
  gap). A killed land's lock is free for the very next probe, no TTL, no
  polling, no timeout to tune.

  `land()` itself writes the lock's holder metadata with `ticket_id` now
  included (`_land_lock_holder_metadata`), so a refused caller's log line
  names the actual landing ticket ("a land is in progress for T-1619 ...")
  rather than a bare pid.

- **Refusal message on the drift-guard's leftover state.** T-0907's
  `_verified_reset_root` drift refusal (the exact path the incident above
  hit) now runs `git status --porcelain` before logging and lists every
  path it is leaving staged/uncommitted, instead of only pointing at
  "inspect by hand". With the exclusivity lease above closing the actual
  race, this refusal should no longer be reachable via a concurrent
  ledger write -- it remains as defense for any OTHER process that
  mutates `root` while holding no lock at all (manual coordinator
  surgery outside `frob ticket` entirely, which no lease can see).

**Belt-and-braces process scan.** The repo owner's own coordinator-side
shell wrapper additionally refused a ledger write whenever a `frob ticket
land` PROCESS was alive against `root`, even before it had acquired
`land.lock` -- folded into `frob` itself rather than staying a wrapper only
one operator ran (agents and CI bypassed it entirely). `refuse_if_land_
in_progress` now also calls `_scan_for_live_land_process(root)`
(`/proc`-based, Linux-only, degrading to a silent no-op finding on any
other platform or scan failure) after the flock probe finds no held lock:
it looks for a process whose argv contains the literal tokens `"ticket"`
and `"land"` and whose `/proc/<pid>/cwd` resolves to `root` -- the exact
shape a real `frob ticket land <id> --worktree <path>` invocation produces,
run from the primary checkout's own directory per playbook convention.
This closes the narrow window between a land process starting and its
first `_land_lock` acquisition, and the fallback path for a platform where
`fcntl` degrades to a no-op (the flock check never engages there at all).
A finding refuses exactly like a held flock does, naming the ticket id
parsed from the process's own argv (a `T-####`-shaped token) when one
was found.

## Root checkout write guard (T-1779)

T-1619 (above) closed the ledger-COMMIT race between `land()` and every
OTHER ledger-writing verb -- but `refuse_if_land_in_progress` only ran
inside `_add_and_commit_tickets_md`, the commit-time choke point. A
mutating verb's HANDLER runs first and already writes its change to the
working tree (`write_ticket` is a plain filesystem write with no guard of
its own) before that commit-time check ever gets a chance to refuse
anything; `renumber`/`promote` write across many tracked files with no
commit step at all (T-1615 deliberately excludes them from the uniform
auto-commit, since each owns its own multi-file transaction), so the
commit-time check never even ran for them. A real 2026-08-06/07 session
hit five shapes of this same underlying gap -- root itself, not any
agent's worktree, has no guard against a coordinator's own git commands
racing a land -- one of which corrupted a closed ticket's state (T-1678
read `done` on main with its code absent, because `frob ticket close` ran
for it between a land's pre-land snapshot and its staging step).

**Gap 1 -- every mutating verb, not just the closeout family, and BEFORE
the write, not merely before the commit.**
`frob.app.ticket_runner._refuse_if_land_in_progress_for_dispatch` runs
BEFORE `handler(root, cfg)`, wrapping the single dispatch call site in
`run()` (the same T-1615 "one choke point, no per-verb code" shape
`_auto_commit_ledger_after_dispatch` already established) -- so this
closes for every verb added to `_ticket_dispatch_table()` in the future
too, with nothing new to remember per verb.

**Incident 6 (observed live, after the first five, T-1779 follow-up)**
sharpened WHERE this refusal has to run: the pre-T-1779 guard lived only
in `_add_and_commit_tickets_md`, so `frob ticket runs-last <id> on`'s
handler ran to completion -- writing `runs_last=True` to the ticket file
-- and only the SUBSEQUENT auto-commit refused with `LandInProgress`. A
"successful write, refused commit" is a PARTIAL write, not a clean
refusal, and is the same corruption class T-1678 already paid for
(incident 5). Refusing before `handler()` runs at all, not merely before
its commit, is what actually closes this -- `test_refused_verb_never_
writes_the_ticket_file_at_all` (`tests/test_ticket_leases.py::
TestDispatchLandGuard`) asserts the ticket's on-disk field is UNCHANGED
after a refused attempt, not merely uncommitted.

Incident 6's OTHER half is a different bug entirely, already ticketed:
`frob ticket new` itself left `tickets/T-1780/` on disk, UNTRACKED, with
no commit step of its own -- `new_ticket` (and `write_ticket`/other
`frob.tickets` mutators called directly) is a pure library call with no
auto-commit; T-1615's uniform auto-commit wraps the CLI DISPATCH layer,
not the library call underneath it. That untracked directory later
DirtyMain-refused an unrelated agent's land. This is T-1758's scope
(`src/frob/tickets/_new_renumber.py`/`_leases.py`/`_store.py`), not
T-1779's -- the two are two halves of one fix (this ticket stops a
verb's WRITE from racing a land already in progress; T-1758 stops a
verb's write from becoming root dirt that blocks a LATER land), and
leaving either one unlanded leaves the other's protection incomplete.

Two explicit sets decide who is exempt from the T-1779 pre-dispatch
guard:

- `_LAND_SAFE_READ_ONLY_VERBS` (`list`/`show`/`doable`/`board`/`epic`/
  `brief`/`flow`) -- verbs that never write anything, so a coordinator
  can still inspect state while a land runs. Deliberately a SHORT
  allowlist rather than an exclusion set: the default posture for any
  verb not proven read-only here is GUARDED, so a future mutating verb
  that forgets to add itself to an exclusion list still runs safely by
  default (it is merely less convenient during a land, never unsafe).
- `_LAND_LOCK_EXEMPT_VERBS` (`land`/`merge-driver`/`sweep-async`) --
  exempt for a reason OTHER than being read-only: `land` is the process
  HOLDING the lock (`_land_lock` already refuses a second concurrent
  land at the OS `flock` level, so gating it here too would be
  redundant, not unsafe, but the exclusion is kept explicit);
  `merge-driver` is invoked BY git as a subprocess of a land that is
  ALREADY holding the lock, and a fresh `open()` in that child process
  would not observe itself as the same holder, so gating it here would
  make a land deadlock against its own merge callback; `sweep-async`
  (T-1699) deliberately races the lock on its own terms.

**Gap 2 -- refuse to START a land on top of someone else's staged
content.** Already closed, not new code: `_land_precheck` (the first
thing `_land_locked` runs, before ANY of land's own staging) already
calls `_refuse_if_main_dirty`, and `describe_root_dirt`'s T-1740 staged-
path callout already names exactly this shape ("N STAGED (likely a
prior land's leftover index, T-1740)"). Verified directly against
incident 3 above: a staged `git rm -r agents skills` left in root DID
refuse the next land with `DirtyMain`, naming the staged paths -- the
guard worked as designed; the incident's cost was the wasted diagnosis
time from three agents who could not see root, not a guard failure. No
new refusal was added for this gap.

**Gap 3 -- a safe path easier to reach than raw `git worktree remove`.**
`git worktree remove` itself cannot be guarded (it is not this repo's
code), so the fix is a safe ALTERNATIVE that is easier to reach than the
raw command, not a wrapper around it. `frob.tickets._leases.
remove_worktree(root, path, *, dry_run=False, force=False)` (T-1779) is
the single-worktree twin of `sweep_worktrees` (T-0836/T-1739): it reuses
`_sweep_verdict_for_worktree` directly for exactly ONE candidate, so the
same liveness-first-and-unconditional gate (`kept:live` if a process is
cwd'd into the worktree), the same clean/lease/age gates, and the same
`force` escape hatch apply unchanged -- one candidate through
`sweep_worktrees`'s own per-candidate loop body, not a re-derived
mechanism. `Err(NotARegisteredWorktree)` if the target path is not one
of `root`'s own git-registered `.claude/worktrees/` agent worktrees, the
same restriction the bulk sweep already enforces.

`frob worktree remove PATH [--dry-run] [--force]` (`frob.app.
worktree_runner`) is the CLI surface -- same subcommand family as `frob
worktree sweep`, one new `argparse` subparser, no new dispatch mechanism.

**Gap 4 -- land-lock visibility without `pgrep` (partial).** The only
way to check "is a land running against root right now" today is
`.frob/land.lock`'s existence plus whether its `flock` is currently
held -- `ls -la .frob/land.lock` shows the file exists (the repo has
landed at least once) but not whether it is CURRENTLY held; a reliable
answer needs a non-blocking `flock` probe, which
`frob.tickets._leases.refuse_if_land_in_progress` already performs and
which any of the guarded verbs above will now report if attempted. A
dedicated `frob doctor`-style one-line surface for this (so a
coordinator can check before touching root without a probe command that
also has other side effects) is not built in this pass -- filed as a
natural, small follow-up rather than half-built here.

## Verify-then-destroy: `frob ticket land --retire-on-proof` (T-1619)

Real incident, same session as the lease gap above: an operator ran `frob
ticket land <id> --worktree <path>` and then `git worktree remove
<path>` as two separate commands. The land had actually FAILED; the
`git worktree remove` ran anyway, destroying a worktree holding 38
verified waiver-deletion commits -- recoverable only because git happened
to keep the dangling commit in its object store. `--finish` (T-1175,
above) already closes this for the CLI's own combined invocation (the
worktree removal is gated on `_print_land_proof`'s `verified` bool and
`_land`'s own `sys.exit(1)` on a failed `land()` never reaches the
finish/retire tail at all) -- but `--finish` only ever removed the
worktree CHECKOUT, leaving its branch (and every commit only reachable
through it) in place, so an operator who also wanted the branch gone was
back to a manual, unguarded `git branch -D` themselves.

`--retire-on-proof` is `--finish` plus branch deletion, sharing the exact
same `verified` gate (`_finish_land_after_success`):

1. `_print_land_proof` computes `verified` (commit is-ancestor-of-main AND
   the ticket's state on main is done/dropped) -- unchanged from `--finish`.
2. If `not verified`: refuse (`sys.exit(1)`), touching neither the
   worktree nor its branch. Identical posture to `--finish`'s own refusal,
   now shared code path (`wants_finish = ticket_land_finish or
   ticket_land_retire_on_proof`).
3. If `verified`: `_worktree_branch_name(root, worktree)` reads the
   worktree's checked-out branch name from `git worktree list --porcelain`
   BEFORE `_finish_worktree` removes the checkout (branch deletion itself
   does not need the worktree to still exist, but capturing the name
   first avoids any ordering ambiguity), then `_finish_worktree` removes
   the worktree exactly as `--finish` does, then `_delete_worktree_branch`
   runs `git branch -D <branch>` -- logged at ERROR with the exact manual
   recovery command on failure, never silent.

Because `_land`'s own top-level `sys.exit(1)` on a failed `land()` call
(`if result.is_err: ...; sys.exit(1)`) returns BEFORE `_finish_land_after_
success` is ever invoked, there is no code path from a failed land to
either the worktree or its branch being touched when `--retire-on-proof`
is passed -- the unsafe two-step sequence the incident hit is no longer
expressible as a single command.

Test coverage: `tests/test_ticket_leases.py::TestRefuseIfLandInProgress`
covers the no-lock-file pass-through, the held-lock refusal (and that the
refusal names the landing ticket), the belt-and-braces process-scan
refusal with no lock file at all, the SIGKILL-then-immediately-free
crash-safety case, and an end-to-end proof that a `land()` call holding
`_land_lock` makes a concurrent `frob ticket new` fail without moving
`root`'s tip or committing the racing ticket.
`tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish`
covers `--retire-on-proof`'s branch deletion on a real verified land, the
`None`-branch no-op, and the refuse-and-touch-nothing path on an
unverified proof.

## Worktree liveness scan (T-1715, T-1739)

`--finish`/`--retire-on-proof`'s `verified` gate (above) proves the LAND
succeeded. It proves nothing about whether the WORKTREE being removed is
still in use -- and dispatch briefs tell an agent to run `frob ticket land
<id> --worktree <their own path>` from the root checkout, so the natural,
documented invocation is the one that deletes the caller's own sandbox.
Real incident, 2026-08-06: `--finish` did exactly what its contract said
and removed a just-landed worktree that the calling agent's own process
was still cwd'd into -- every subsequent tool call failed with "the
isolation worktree appears to have been removed", the agent could not
create a replacement (worktree creation is reserved to whatever spawned
it), and it had to be abandoned and re-dispatched, losing its accumulated
context. `frob worktree sweep` (T-0836, "Coordinator worktree cleanup" in
the playbook) has the identical hazard at fleet scale: its keep-criteria
(lease/dirty/age) are all PROXIES for liveness, not liveness itself, and a
2026-08-07 dry-run during a four-agent drive caught them exactly inverted
-- the one worktree kept belonged to a retired agent holding a stale
lease, the three worktrees marked for removal belonged to agents that
were actively running (one mid-implementation on a critical ticket). The
sharpest edge: `dirty` under-covers precisely because a well-behaved agent
COMMITS its work-in-progress as stall insurance (this repo's own
guidance) -- following the guidance makes a worktree look MORE removable,
not less.

Both incidents share one fix mechanism rather than each growing a new
heuristic: `scan_for_live_worktree_process(path)`
(`frob.tickets._leases`) generalizes T-1619's `_scan_for_live_land_process`
`/proc` walk (see "Land exclusivity lease" above) to answer "is ANY live
process cwd'd into `path`", not just a `frob ticket land` process cwd'd
into the primary checkout. Same degrade-to-no-finding contract: `/proc`
unavailable, an unreadable pid, or simply no match all return `None`,
never a refusal by themselves. `refuse_if_worktree_in_use(root, worktree)`
combines that scan with the existing lease machinery
(`read_all_leases`/`is_lease_ttl_expired`, factored into a shared
`_live_lease_for_worktree` helper) into one `Result`:
`Err(WorktreeInUseError.LiveProcess)` names the pid and its argv;
`Err(WorktreeInUseError.LiveLease)` names the pinning ticket id and when
the lease was recorded. Both are logged at ERROR before returning, so a
refusal always names what it is refusing to remove and why -- "could not
finish" with no cause named is the exact DirtyMain-class mistake
(playbook section, T-1698/T-1699) this repo has already paid for once.

**`--finish`/`--retire-on-proof`** (`_finish_worktree`,
`frob.app.ticket_runner._land_cmd`): calls `refuse_if_worktree_in_use`
immediately before `git worktree remove`, after the existing `verified`
LAND-PROOF gate has already passed. A refusal here `sys.exit(1)`s WITHOUT
unwinding anything -- the land itself already fully succeeded, only the
cleanup step is refused, and the worktree branch remains the recovery
path exactly as it did before `--finish` existed. `frob ticket land <id>
--worktree PATH --finish --force` overrides the refusal, for a worktree
independently confirmed genuinely wedged (the process scan cannot always
prove a pid is dead); `--force` has no effect on anything except this
guard.

**`frob worktree sweep`** (`sweep_worktrees`/`_sweep_verdict_for_worktree`,
`frob.tickets._leases`; CLI in `frob.app.worktree_runner`): the liveness
scan runs FIRST, before the pre-existing dirty/lease/age gates, and
produces a new `kept:live` verdict naming the pid
(`kept:live(pid <N>) <path>`) -- unconditionally, regardless of whether
the worktree is clean, leased, or old, which is exactly the property the
2026-08-07 incident needed and the old three-gate design did not have.
`frob worktree sweep --force` overrides the `kept:live` gate specifically
(dirty/age are unaffected by `--force`); refuse-by-default is the point
of the flag existing at all, so reach for it narrowly, worktree by
worktree, not as a blanket unblock for a whole sweep.

Both call sites share `scan_for_live_worktree_process` and
`_live_lease_for_worktree` directly -- there is intentionally only one
process-liveness scanner and one lease-liveness judgment in
`frob.tickets._leases`, not a third or fourth heuristic layered
alongside lease/dirty/age. "Could not determine liveness" is never
reachable as "prove it is dead": both underlying checks degrade to
`None`/no-match on any uncertainty, and a `None`/no-match result is
always treated as "not proven in use" -- never as "proven not in use" --
by the two call sites, not by the checks manufacturing false confidence
themselves.

Regression coverage (`tests/unit/test_land_finish_guard.py`,
`tests/test_worktree_guard.py`) specifically covers the exact shape that
would have killed three agents: a worktree that is CLEAN, holds NO lease,
has a RECENT HEAD commit, and has a live process cwd'd into it -- asserts
it is kept/refused and that the pid is named, not just that some
generically-stale worktree is caught.

Related, separately ticketed rather than folded in here: T-1739 also
surfaced a lease/state disagreement (a stale lease naming one ticket as
the `doable --show-blocked` holder while the ledger has a different
ticket queued) -- that is a distinct defect in `doable`'s own attribution
logic, not a liveness question, and is tracked as its own ticket (see
T-1743) rather than folded into the scan this section documents.

## Passenger-ticket disclosure (T-1618)

`frob ticket land <id> --worktree W` merges `W`'s BRANCH, not just the
commits belonging to `<id>`. `_check_cross_ticket_leakage` (T-1355/T-1639,
above) already refuses on a scope-glob-plus-ledger-record-diff heuristic
when a sibling ticket is `IN_PROGRESS` -- but it explicitly EXEMPTS any
sibling already `DONE`/`DROPPED` (`_find_leaked_tickets`'s `effective_
state in (DONE, DROPPED): continue`), on the assumption that a closed
ticket's scope claim is "spent". Real incident, 2026-08-05: worktree
w24-waive-family held five tickets; T-1579's WAIVE004 self-heal escape
was judged unsafe and reverted IN THE WORKTREE, but landing a DIFFERENT
sibling (T-1581) still carried T-1579's code onto main, where it deleted
55 live `frob:waive` directives across five gate families before anyone
noticed. Whatever state T-1579's own ledger record ended up in, its CODE
never actually left the branch -- exactly the shape the DONE/DROPPED
exemption cannot see, because it never looks at the diff's own content at
all, only at scope declarations and ledger state.

`_check_passenger_tickets` (`frob.tickets._land`) is a deliberately
DIFFERENT, complementary signal: it scans the branch's FULL diff (`git
diff base_ref...HEAD`, not `--name-only`) for `frob:ticket <id>` directive
additions (`+`-prefixed lines only, never context) naming any ticket OTHER
than the one landing. This asks a narrower, more precise question than
scope-matching -- whose fingerprint is on the code actually riding along,
full stop -- and does not consult any sibling's ledger state at all, so a
DROPPED sibling whose code is still physically present is caught exactly
as readily as an IN_PROGRESS one. Wired into `_land_precheck_remaining_
checks` alongside the existing leakage check, sharing the SAME `--allow-
cross-ticket` escape hatch (`frob ticket land --allow-cross-ticket`) --
one flag an operator already knows, not a second differently-named
override. A refusal (`LandError.PassengerTickets`) lists every passenger
id found; an acknowledged override logs the same list at WARNING before
proceeding. Nothing about the land is silent either way -- the T-1618
incident's own root complaint ("nothing in the output said T-1579 was
going to main") no longer has a code path where that holds.

The tradeoff, disclosed rather than hidden: this can flag a hunk that
merely MOVED a pre-existing `frob:ticket <id>` directive (e.g. a function
carrying one got relocated by an unrelated refactor, so git represents it
as delete+re-add) as if it were a fresh addition. That is a real, known
false-positive shape -- but it is arguably still an honest signal ("this
diff touches code attributed to another ticket"), and the escape hatch
exists precisely for a deliberately joint landing; the alternative
(missing a genuine passenger silently, the actual incident) is strictly
worse.

## Already-landed-on-main: first-class outcome (T-1618)

The second, benign-but-confusing half of the same incident: once one
ticket's land has carried a sibling's code onto main (the passenger check
above stops this going forward, but does nothing for a worktree that
already leaked before this fix existed), that sibling's own later `frob
ticket land` finds nothing left to contribute -- its scope's diff against
main is empty. Before this fix, that fell through into whatever the
normal land path does with an empty changeset: BUG002 finds the repro
test already passing at the parent, TEST016 finds an empty diff with no
mutants to kill. Both gates are technically CORRECT; the ticket is simply
already done. The operator diagnosed and routed around this by hand three
times in one session (verify content on main, `frob ticket close
--skip-mutation-evidence`).

`_check_already_landed` (`frob.tickets._land`) recognizes the shape
directly: when `worktree` is CLEAN (`_porcelain_dirty` -- see below for
why this matters), the ticket's own declared scope (excluding the ledger
path, which changes on every land regardless) has zero hits in
`_branch_changed_files(worktree, base_ref)`, AND (T-1675) the ticket's own
ledger record read directly off `base_ref` (`_ledger_ticket_at_ref`)
already shows `state: done` there, it refuses with `LandError.
AlreadyLandedOnMain` and a message naming the exact manual recipe the
incident's operator worked out by hand: verify the content against
`base_ref`, then `frob ticket close <id>` directly. This function still
does NOT verify the content's correctness itself -- `frob.tickets` cannot
run `base_ref`'s tests or gates (docs/rework.md's cycle-avoidance rule:
that needs `frob.gates`/`frob.testing`, which this package does not
import) -- so a `AlreadyLandedOnMain` refusal remains a strong,
well-targeted HINT, not a full proof; the operator's own verification step
is still real work, just no longer undirected work.

**The signal problem, and its fix (T-1675).** "No diff in the declared
scope" alone was being asked to answer "was this already landed?", and it
could not: an empty scope-diff is equally consistent with *the work is
already on main*, *the work landed outside its declared scope globs*, and
*this ticket legitimately changed only docs or the ledger*. That was
absence-of-evidence read as evidence-of-absence, and it forced this check
off by default -- it never ran for a real land, so the defect class it
targets still reached main. T-1675 closed the gap by requiring a SECOND,
positive signal alongside the empty diff: the ticket's own ledger record,
read directly off `base_ref`, must already claim `state: done` there. A
ticket that has not yet landed cannot already be `done` on `base_ref` --
only `frob ticket close`/`land`'s own squash-apply ever write that state
-- so this is genuine positive evidence the content made it to main, not
an inference from silence. A docs-only, ledger-only, or scope-mismatched
ticket landing for the FIRST time still gets `Ok(None)` here: its scope-
diff may be empty, but its own record on `base_ref` is not yet `done`,
so the refusal correctly does not fire.

**On by default, no opt-in flag (T-1675).** An early draft (T-1618) wired
the empty-diff signal alone into `_land_precheck` unconditionally and it
regressed 20 existing tests across this repo's own `test_ticket_land.py`
suite -- an empty scope-diff turns out to be the ORDINARY shape of a large
legitimate class (a docs-only ticket, a ledger-only/Done-report-only
ticket, a test fixture that declares a scope without ever writing a file
under it). That forced the check behind a now-removed `land` opt-in flag
(formerly `--check-already-landed`). The positive on-main-state
requirement above is what makes an unconditional default safe now: every
member of that false-positive class is landing for the first time, so its
own record on `base_ref` cannot already show `done` -- the flag and its
CLI switch are gone; the check always runs. `_porcelain_dirty` still gates
it: this check runs in `_land_precheck`, BEFORE `land`'s own wip-commit
stage folds uncommitted work into a real commit, so a DIRTY worktree's
empty COMMITTED diff would otherwise look identical to "already landed"
even though the real work simply has not been committed yet -- the check
is skipped entirely whenever the worktree is dirty, deferring to whatever
the rest of the land pipeline does with that uncommitted work.

**Why `CrossTicketLeakage` did not fire for the T-1579 case** (the
ticket's own explicit question): two independent reasons, both closed by
the passenger-ticket work above rather than by changing the leakage check
itself (T-1639's IN_PROGRESS-only refinement was its own deliberate,
already-considered fix for a different false-positive class and must not
regress). First, `_find_leaked_tickets` exempts any sibling whose
EFFECTIVE state is DONE/DROPPED outright -- if T-1579's in-worktree
"revert" updated its OWN ticket record to a terminal state (even without
fully reverting the code), the leakage check would treat it as settled
and never re-examine its files at all. Second, even for a non-exempt
sibling, the leakage check's signal is `changed_paths` from `--name-only`,
a net diff -- if the revert's own commit brought a FILE back to byte-
identical content relative to `base_ref`, that file simply stops
appearing as changed at all, regardless of the sibling ticket's ledger
state, so a scope hit against it can vanish even though other, un-reverted
files the same ticket touched (per the incident, the 55 `frob:waive`
deletions landed in files across arch/strata/perf/graph/vet, not
necessarily the exact file that was "reverted") remain. Both gaps trace
to the same root property: `_check_cross_ticket_leakage` was built to
answer "does a scope declaration overlap a change", never "whose
`frob:ticket` fingerprint is physically in this diff" -- the latter is
what `_check_passenger_tickets` answers instead, deliberately not by
patching the former's heuristics to try to cover both questions.

## Cross-ticket leakage only refuses on an IN_PROGRESS sibling (T-1639)

<!-- frob:describes src/frob/tickets/_land.py::_find_leaked_tickets -->
<!-- frob:describes src/frob/tickets/_land.py::_check_cross_ticket_leakage -->

`_check_cross_ticket_leakage` (T-1355) refuses a land whose branch touches
files covered by a DIFFERENT ticket's declared `scope`, when that other
ticket is `IN_PROGRESS` on `root`'s ledger -- the incident class where
landing one ticket out of a multi-ticket series worktree silently carries
a sibling's still-open work onto main.

T-1639: before this fix, "still open" meant "not `DONE`/`DROPPED`" --
which also matched `QUEUED`/`PLANNED`/`BLOCKED`. Filing a ticket with a
generously broad scope (this repo's own convention: declare scope early
and wide so nothing is silently out of bounds) reserved that scope
against every OTHER land immediately, before a single commit existed for
it -- measured 2026-08-06: a freshly filed, unstarted ticket (T-1637)
blocked an unrelated land (T-1636) over 12 files that only overlapped by
declaration, forcing `--allow-cross-ticket` as a reflex habit.

The fix reuses the same line `frob.tickets._leases` already draws for
worktree leases: a lease (and now a CrossTicketLeakage refusal) exists
only for a ticket that is actually being worked, never one merely filed.
`_find_leaked_tickets` still computes every scope-overlap hit exactly as
before (including the T-1370 same-worktree exemption and the T-1390
"sibling's own ledger record never moved" exemption), but only a hit
against an `IN_PROGRESS` sibling lands in the `leaked` map that
`_report_leaked_tickets` refuses on. A hit against a `QUEUED`/`PLANNED`/
`BLOCKED` sibling is still logged (at INFO, naming the ticket and its
state) so the overlap is disclosed, not silently dropped -- it just no
longer blocks. This does not weaken the T-1618 case the check exists for
(a shared series worktree carrying a sibling's COMMITTED work onto main):
that case always involves a sibling that was actually started, so it is
always `IN_PROGRESS` by the time it could leak anything.

## Post-land unscoped error sweep (T-1456)

<!-- frob:describes src/frob/app/ticket_runner/_land_cmd.py::_unscoped_error_findings -->
<!-- frob:describes src/frob/app/ticket_runner/_land_cmd.py::_apply_root_tier_a_fixes -->
<!-- frob:describes src/frob/app/ticket_runner/_land_cmd.py::_post_land_unscoped_error_sweep -->

Every wave of a busy drive left small unscoped residue on main a
`--ticket`-scoped land verification could not see: a waiver that did not
travel with a relocated block of prose (INV006/PII012 on a file split), a
format drift, a stale registry denominator, a SELFAUDIT interface
attribute for a store block. Each was invisible to `land`'s own T-0754/
T-1410 claim-divergence machinery -- which compares SCOPED (`--ticket`)
counts/identities -- and only surfaced in the coordinator's next full,
unscoped `frob check`, forcing a hand-fix cycle between lands.

`frob ticket land`'s CLI layer (`_land`, `_land_cmd.py`) now brackets the
real `land()` call with an UNSCOPED, `--budget`-bounded (default 90s)
error-identity sweep of `root`:

1. **Before `land()` runs** (real, non-dry-run lands only): capture
   `root`'s current `HEAD` (`pre_land_sha`) and an unscoped `(rule_id,
   file)` error-finding set (`_unscoped_error_findings`, no `--ticket`
   filter -- deliberately the opposite of `_check_gate_findings_fn`'s
   scoped set) as the baseline. Either capture failing (a spawn refusal,
   an unparsable run) degrades to `None`, never a guessed empty set.
2. **After `land()` returns `Ok`** (the squash-apply commit has already
   landed on `root`): `_post_land_unscoped_error_sweep` re-runs the same
   unscoped scan and diffs it against the baseline. `new_findings = fresh
   - baseline` is the residue THIS land's squash-apply introduced that no
   `--ticket`-scoped check could have caught.
3. **No new findings**: silent no-op, the common case.
4. **New findings, Tier-A auto-fixable**: `_apply_root_tier_a_fixes` runs
   the T-1138 deterministic auto-fix handlers against `root`'s whole tree
   (unscoped, unlike the pre-land `_tier_a_pre_land_step`'s touched-set
   scoping) and commits the result as a follow-up `fix(land): <id>
   post-land Tier-A cleanup (...)` commit if it resolves every new
   finding.
5. **New findings NOT resolved by auto-fix**: refuse. `root` is hard-reset
   back to `pre_land_sha` (`git reset --hard`), the exact finding list is
   logged, and the CLI exits non-zero -- a landing that would have
   regressed main's error floor never reaches it, and a reset FAILURE is
   itself logged loudly (manual repair, rather than a silently landed
   regression) instead of assumed to have succeeded.

Either side of the comparison coming back unmeasurable (`None`) skips the
sweep entirely rather than comparing a real set against a guess -- the
same unmeasured-is-not-zero posture `_check_gates_summary_fn`/
`_check_gate_findings_fn` (T-0832/T-0846) already use for the scoped
claim-divergence check this complements, not replaces.

## `frob check --land-parity` (T-1535)

<!-- frob:describes src/frob/app/ticket_runner/_land_cmd.py::land_parity_findings -->
<!-- frob:describes src/frob/app/check_runner.py::_run_land_parity -->

Every blind repair round on 2026-08-04/05 traced back to worktree-check
vs. land-sweep divergence (module docstring's motivating incidents for
the post-land sweep above apply equally in the OTHER direction: a
worktree agent's own scoped verification passing while the same tree
would refuse at land). `land_parity_findings` (called by `frob check
--land-parity`, `_run_land_parity`) runs the EXACT same evaluation the
pre-commit/post-land sweeps above run against the CURRENT worktree tree
with no baseline diff: `_unscoped_error_findings` (this section's own
spawn+parse function, reused verbatim) with `FROB_NO_GATE_CACHE=1`
forced into the SPAWNED check's environment (never this process's own
`os.environ` -- the caller's `env=` param on `_unscoped_error_findings`,
T-1535, exists for exactly this), then `_drop_checkpoint_exempt_findings`
(this section's own T-1524 exemption function, reused verbatim) applied
unconditionally.

`None` (unmeasurable) exits 1 with a loud "could not evaluate" message,
never a false-clean pass; an empty set exits 0; a non-empty set prints
every `(rule, file)` finding and exits 1 -- see
`docs/guides/agent-playbook.md#6g-run-frob-check---land-parity-before-writing-your-done-report-t-1535`
for the per-dispatch usage recipe. Reusing both functions verbatim (never
a second hand-copied parser or exemption list) is what makes this a
PARITY check rather than an approximation: `tests/test_ticket_work_and_
land_finish.py::TestLandParityFindings.test_parity_with_the_land_sweeps_own_exemption_function`
pins that `land_parity_findings`'s output on a fixed raw finding set is
byte-identical to calling `_drop_checkpoint_exempt_findings` directly
against that same set.

## `frob ticket evidence --replace` (T-1537)

<!-- frob:describes src/frob/tickets/_evidence.py::replace_evidence -->

A renamed or parametrized test that was already bound as ticket evidence
used to orphan the binding -- `frob ticket land` would refuse ("evidence
no longer resolves post-merge") with no CLI remedy; the coordinator had
to hand-edit via `write_ticket` directly, twice, on 2026-08-04 (the T-1520
parametrization incident this ticket closes). `frob ticket evidence <id>
--replace OLD-NODE-ID NEW-NODE-ID` rebinds one evidence id everywhere it
appears -- the flat `ticket.evidence` list AND every acceptance
criterion's own `evidence` tuple -- in a SINGLE atomic `write_ticket`
call (`replace_evidence`, the same single-writer path every other
evidence mutation already uses, never a second ad hoc write; the append
and the acceptance rebind can never be split across two writes, mirroring
`_append_evidence_and_write`'s own "no partial state" guarantee).

`NEW-NODE-ID` is held to the exact same bar a fresh `--evidence` id is:
schema-validated, resolved against the collected pytest/rust node id set,
and required to have actually PASSED on the CLI's own verification run
(the same `_verify_ids_passing` oracle `_apply_evidence` uses) -- a
`--replace` can never let an unresolved or currently-failing id sneak in
just because it is nominally a rename rather than an addition.
`OLD-NODE-ID` must be present in EITHER the flat evidence list or at
least one acceptance criterion's evidence -- `Err(EvidenceReplaceNotFound)`
otherwise, a typo'd source id is never a silent no-op. `OLD-NODE-ID ==
NEW-NODE-ID` (after the same dot-to-`::` normalization every evidence id
goes through) is itself a no-op SUCCESS -- nothing to replace is not a
failure.

`--replace` composes with the positional node-id list and `--evidence-cmd`
in one `frob ticket evidence` invocation (all three modes can fire in the
same call; the command only refuses when NONE of the three is given).

<!-- frob:waive DOC006 reason="the prose itself discloses 'frob refactor rename' as a separate, not-yet-built ticket -- it names a future command, not a live one" -->
Disclosed follow-up (this ticket's own body): `frob refactor rename`
detecting a bound-evidence reference and offering the `--replace` rebind
automatically is a separate, not-yet-built ticket -- this ships the CLI
primitive that follow-up would call, not the detection.

### `--archived` (T-1561)

<!-- frob:describes src/frob/tickets/_store.py::write_archived_ticket -->

`--replace`'s load/write path (`_load_one`/`write_ticket`) only ever
sees ACTIVE storage -- an already-archived ticket resolves to
`Err(NotFound)`, even though COV003 still scans `tickets-archive.md`/
`tickets/archive/**` for stale evidence bindings on it. This is the
2026-08-05 incident T-1561 closes: COV003 fired on archived T-1269/
T-1495 after their bound tests were renamed by wave-4 unwind-semantics
work, `evidence --replace` answered `NotFound`, and the coordinator
worked around it with a raw string swap directly in
`tickets-archive.md` -- exactly the hand-edit-the-ledger hazard the
`frob ticket` CLI exists to make unnecessary.

`frob ticket evidence <id> --replace OLD NEW --archived` retargets both
halves at archive storage: `ticket_id` is loaded via `load_archive`
instead of `_load_one`, and the rebound ticket is written back via
`write_archived_ticket` (the archive-side analog of `write_ticket`)
instead of `write_ticket` -- so the repair lands in the archive, never
resurrecting the ticket into active storage as a side effect.
`write_archived_ticket` mirrors `write_ticket`'s own per-mode shape: v2
mode writes under `tickets/archive/T-####/ticket.md` via the per-ticket
`ticket_lock`; single mode splices into `tickets-archive.md`'s raw text
(`_splice_ticket_section`) under the SAME T-1536 post-splice integrity
check (`_post_splice_integrity_check`) `write_ticket` already holds for
the active ledger, so a repair can never itself corrupt a sibling
archived ticket.

```python
# frob/tickets/_store.py
def write_archived_ticket(root: Path, ticket: Ticket) -> Result[None, TicketError]
    # Upsert ONE ticket into ARCHIVE storage -- the archive-side analog
    # of write_ticket, which only ever writes to ACTIVE storage.
```

## Merge queue (T-1345, first portion)

<!-- frob:describes src/frob/tickets/_land_queue.py::QueueEntry -->
<!-- frob:describes src/frob/tickets/_land_queue.py::QueueError -->
<!-- frob:describes src/frob/tickets/_land_queue.py::enqueue -->
<!-- frob:describes src/frob/tickets/_land_queue.py::drain_next -->
<!-- frob:describes src/frob/tickets/_land_queue.py::queue_status -->
<!-- frob:describes src/frob/tickets/_land_queue.py::file_lock -->
<!-- frob:describes src/frob/app/ticket_runner/_land_cmd.py::_land_enqueue -->
<!-- frob:describes src/frob/app/ticket_runner/_land_cmd.py::_land_drain -->
<!-- frob:describes src/frob/app/ticket_runner/_land_cmd.py::_land_core -->

`frob.tickets._land_queue` formalizes the coordinator-lands-serially
discipline `docs/guides/agent-playbook.md` already documents as process
into checkable tooling: `enqueue(root, ticket_id, worktree, branch)`
appends a `queued` entry to `.frob/land-queue.json` and returns
immediately (a caller never blocks waiting for `land()` to actually run);
`drain_next(root, land_fn)` pops the oldest `queued` entry (FIFO) and runs
it through a caller-supplied `land_fn` (normally a thin wrapper around
`land()` itself), recording the outcome (`landed` + commit sha, or
`failed` + the `LandError` value) back onto the entry rather than
dropping it. `queue_status(root)` is a read-only snapshot of the full
queue, any status, for a caller that wants to show state.

**CLI surface (T-1444, the follow-up T-1345 disclosed):**

- `frob ticket land <id> --worktree <path> --queue` -- enqueue instead of
  landing immediately (`_land_enqueue`); prints the assigned queue
  position and returns right away.
- `frob ticket land --drain` -- serially process every `queued` entry,
  one process, one invocation (`_land_drain`), not a long-running poll
  loop; call it repeatedly (a scheduler, a coordinator loop) to keep
  draining. Needs neither `<id>` nor `--worktree` -- both are no longer
  argparse-`required`, enforced instead in the app layer for every OTHER
  mode (`_require_land_args`/`_land_plan_cmd`'s own check).
- `_land_core` is the shared merge-check-splice-close-commit-sweep chain
  both a direct `frob ticket land <id>` call and `_land_drain`'s per-entry
  `land_fn` run -- the SAME `LAND-PROOF:` line prints on every real,
  non-dry-run success either way (T-1345's own acceptance criterion,
  "preserve the existing LAND-PROOF contract"). Unlike the old inline
  `_land` body, `_land_core` never calls `sys.exit`: a post-land
  unscoped-error-sweep revert returns
  `LandError.PostLandUnscopedSweepFailed` instead, so `_land_drain` can
  attribute a mid-batch failure to the one ticket that caused it
  (dequeued, logged, NOT retried -- `drain_next`'s own policy, unchanged)
  and continue draining the rest of the queue.

**Deferred (disclosed, not silently dropped -- see T-1444's Done report
for the real follow-up ticket id):** `_land_core`'s pre-/post-land
unscoped-error sweep and baseline capture still run PER TICKET inside
`_land_drain`'s loop, exactly as a direct `frob ticket land <id>` call
would -- this ticket's acceptance criterion also asked for "one baseline
capture + one full sweep per drain of N tickets" (shared across the whole
batch) and "sublinear total verification wall-clock", neither of which
this increment implements. Every entry's own delta validation is real and
attribution is preserved; the batch-level sharing optimization is the
scoped-out remainder.

**Policy decisions, recorded here per the ticket's own design questions:**

- **Where the queue lives.** `.frob/land-queue.json`, guarded by a
  dedicated `fcntl` flock (`.frob/land-queue.lock`) -- same posture as
  `_land._land_lock`'s `.frob/land.lock`, a deliberately separate file so
  the two concerns (serializing the actual git-heavy `land()` body vs.
  serializing queue-file bookkeeping) never share a lock. A crashed
  drainer leaves the file exactly as it was at its last successful write;
  the next `drain_next` call simply resumes.
- **A queued branch that no longer merges cleanly.** Rejected back to the
  agent: `drain_next` marks the entry `failed` with the `LandError`
  recorded and dequeues it (no longer a `drain_next` candidate), but never
  removes it from the JSON history and never auto-rebases-and-retries.
  Auto-retry risks landing a diff the agent never actually re-verified --
  the same class of gap `docs/guides/agent-playbook.md` section 9's
  deletion-filter rule exists to catch for a stale-base merge.
- **Concurrency.** The queue-file lock is held only across the
  pop-and-mark-landing step and the record-outcome step, NOT across the
  `land_fn` call itself -- `land_fn`'s own `_land_lock` already serializes
  the expensive part. Running exactly one drainer process per `root` is
  an operational invariant this module documents but does not itself
  enforce; a second concurrent drainer would be safe (the queue lock
  prevents two drainers popping the same entry) but wasteful (both
  contend on `_land_lock` for nothing).
- **LAND-PROOF.** `drain_next` returns the updated `QueueEntry` (carrying
  `commit_sha` on success), and `land_fn`'s own `Result[LandReport,
  LandError]` is available to whatever wrapper the caller supplies -- a
  future CLI drainer verb can print the same `LAND-PROOF:` line `frob
  ticket land` already does today, from the `LandReport` its `land_fn`
  closure captured. This module does not print anything itself (no CLI
  surface in this scope), so the contract is preserved by construction:
  nothing here bypasses or reimplements `land()`'s own reporting.

## Verification watermark (T-1687, foundation of the T-1686 epic)

<!-- frob:describes src/frob/verify/_watermark.py::SCHEMA_VERSION -->
<!-- frob:describes src/frob/verify/_watermark.py::VerifyQueueEntry -->
<!-- frob:describes src/frob/verify/_watermark.py::Watermark -->
<!-- frob:describes src/frob/verify/_watermark.py::WatermarkError -->
<!-- frob:describes src/frob/verify/_watermark.py::record_intent -->
<!-- frob:describes src/frob/verify/_watermark.py::queue_status -->
<!-- frob:describes src/frob/verify/_watermark.py::load_watermark -->
<!-- frob:describes src/frob/verify/_watermark.py::advance_watermark -->
<!-- frob:describes src/frob/verify/_watermark.py::compact_queue -->

T-1686's epic makes landing independent of synchronously verifying in
every profile: a check must stay on the critical path only if its
failure damages someone OTHER than the author (ledger integrity,
LAND-PROOF, lease/lock discipline); everything else (coverage floors, doc
drift, arch thresholds, ...) can defer to a batch verification pass. That
requires a durable record of what has and has not been verified yet,
independent of whatever worker eventually drains it -- the frob.verify
package is that record, and `frob.verify._watermark` (T-1687) is its
whole content today: no daemon, no worker, no CLI verb. Landing the
record first, standalone, is deliberate: retrofitting a durable store
under an already-running worker is strictly harder than building the
worker on a store that already exists.

**Two persisted files, two independent concerns:**

- **`.frob/verify-queue.json`** -- an append-only intent log. One
  `VerifyQueueEntry` per land: `commit_sha`, `ticket_id`, `touched_symbols`
  (see below), `enqueued_at`, and `profile`. `record_intent(root, *,
  commit_sha, ticket_id, touched_symbols, profile)` appends exactly one
  entry and refuses (`WatermarkError.EmptyTouchedSymbols`) on an empty
  symbol set -- a land with nothing for tier-2 attribution to reach would
  otherwise make every later finding at that commit permanently
  unattributable. `queue_status(root)` is a read-only snapshot, oldest
  first.
- **`.frob/verify-watermark.json`** -- one record: "main is verified
  through `commit_sha`, at `verified_at`, by `run_id`, against
  `baseline_digest`". `advance_watermark(root, *, commit_sha, run_id,
  baseline_digest)` unconditionally overwrites the prior record --
  this module trusts the caller's own "fully green batch" decision and
  does not re-derive it. `load_watermark(root)` reads it back.

**Touched SYMBOLS, never file paths.** `VerifyQueueEntry.touched_symbols`
is a tuple of symref-shaped symbol ids (the same id shape
`frob.graph.GraphSnapshot.symbols` keys on), never a path list. Tier-2
attribution (T-1686's own design: "a finding anchored at symbol S
attributes to the commit whose touched symbol set REACHES S in the
reference graph") is a graph reachability query over symbol ids -- a
path-keyed record cannot answer it once a symbol moves between files
without misreporting the move itself as a regression. Computing the
touched-symbol set from a real `Diff`/`GraphSnapshot` pair is deliberately
OUT of this module's own scope (frob.verify never imports `frob.graph`)
-- a caller with graph access (a later leaf's land-time wiring) resolves
and passes the set in; this module only validates the shape (non-empty)
and persists it verbatim.

**One shared lock implementation, not two.** Both files use
`frob.tickets._land_queue.file_lock` (T-1687 extracted the merge queue's
own fcntl advisory-lock mechanics into this reusable, `label`-tagged
context manager so `_queue_lock` above and frob.verify's two locks all
share one implementation) -- "two lock protocols over adjacent state in
one repo is a deadlock waiting to be discovered in production" per this
ticket's own scope note. The queue lock and the watermark lock are still
two SEPARATE lock files (never reuse a lock/state file across a different
concern, matching `_land_queue`'s own rule for `.frob/land.lock` vs
`.frob/land-queue.lock`), just built from the same primitive.

**Append-only, compacted below the watermark, never rewritten in
place.** `record_intent` only ever appends. `compact_queue(root)` is the
one operation that shortens `.frob/verify-queue.json`: it drops every
entry at-or-before the CURRENT watermark's `commit_sha` (a no-op,
`Ok(0)`, if there is no watermark yet or that commit is not present in
the queue) and never rewrites or reorders a still-pending entry. Both
operations still write the whole file in one `write_text` call under
`file_lock`, the identical "not atomic-replace, but never torn under
normal operation" posture `_land_queue._save_queue`'s own docstring
documents.

**"Cannot verify" is never "verified".** `load_watermark` treats a
missing watermark file (nothing verified yet) and a CORRUPT watermark
file identically at the read boundary: both return `Ok(None)`, logged at
WARNING in the corrupt case so the corruption itself stays visible even
though the read degrades safely -- a caller must never be able to
mistake a corrupted record for a stale-but-real one. `queue_status`, by
contrast, propagates a corrupt QUEUE file as
`Err(WatermarkError.StoreCorrupt)` rather than degrading to an empty
tuple: an unreadable intent log misread as "nothing pending" is itself a
false "how far is main verified" claim, just as dangerous as a stale
watermark reading as current. `record_intent`/`compact_queue` (the two
mutators) both refuse outright on that `Err` rather than risk silently
discarding or duplicating intent records on top of an unreadable file.

**What this ticket does NOT do (disclosed, next leaves in the epic):**
no daemon-side coalescing worker (T-1688), no CLI wiring that calls
`record_intent` from a real `land()`, no tier-1/2/3 attribution logic, no
profile-to-queue-depth dial. This module is purely the data model plus
its read/write primitives, verified in isolation
(`tests/unit/verify/test_watermark.py`).

## Coalescing verify worker (T-1688)

<!-- frob:describes src/frob/verify/_worker.py::WorkerError -->
<!-- frob:describes src/frob/verify/_worker.py::WorkerOutcome -->
<!-- frob:describes src/frob/verify/_worker.py::run_coalesced_verification -->
<!-- frob:describes src/frob/verify/_worker.py::CoalescingWorker -->
<!-- frob:describes src/frob/serve/_daemon.py::_poll_verify_worker -->

The trailing-edge-debounce half of the T-1686 epic, and where the
wall-clock saving actually comes from: `frob.verify._worker.
run_coalesced_verification` is the whole job on one wake -- read the
verify queue, look at ONLY its tip entry, verify ONCE, and on a
genuinely green result advance the watermark past every entry the queue
currently holds and compact them away.

**Coalesce, not iterate -- structurally, not by convention.** The
function never loops over queue entries; it reads `entries[-1]` and calls
its `verify_fn` exactly once, so five (or five hundred) queued lands
produce exactly one verification call. This is provable directly:
`tests/unit/verify/test_worker.py::TestRunCoalescedVerification::
test_five_queued_entries_call_verify_exactly_once` enqueues five entries,
injects a call-counting `verify_fn`, and asserts the count is 1 -- an
invocation count, not a timing measurement (a timing-based test proves
nothing about whether coalescing actually happened, only about how fast
it was).

**`None` can never advance the watermark -- structurally.** `verify_fn`
returning `None` (T-1703's own contract for `_unscoped_error_findings`: a
budget-truncated or otherwise partial check is unmeasurable, never
"clean") hits an early `return Err(WorkerError.Unmeasurable)` that sits
BEFORE every other branch in the function, including the one branch that
calls `frob.verify.advance_watermark`. There is no flag to remember to
check -- the only textual path to `advance_watermark` in this file is the
final branch of a chain no `None` result can fall through to.

**Four possible outcomes**, distinguished by `WorkerOutcome.status`:

- `"empty"` -- nothing queued, `verify_fn` never even called.
- `"baseline-established"` -- a real, measured result, but with no PRIOR
  rolling baseline to diff against; "no new findings" cannot be asserted
  with nothing to compare to, so this is deliberately NOT treated as
  green (watermark untouched) even though the check itself succeeded.
- `"red"` -- new findings vs the rolling baseline; files a regression
  ticket (reusing `frob.app.ticket_runner._rapid_sweep.
  _file_regression_ticket`, T-1684's own filer) and leaves the watermark
  untouched -- a red batch quarantines, it does not revert (T-1686's own
  recorded decision).
- `"green"` -- no new findings vs a real prior baseline; the watermark
  advances to the tip commit and `compact_queue` drops every entry the
  queue held (they are all covered by the same tip verification).

**Reused, not reinvented.** The rolling-baseline read/write/diff
machinery is `frob.app.ticket_runner._rapid_sweep`'s own
(`_read_baseline`/`_write_baseline`/`_file_regression_ticket`, built for
T-1684's per-land spawn) -- this module imports those three functions
directly rather than re-deriving the same comparison a second time; the
only genuinely new decision layered on top is "and if it's green, advance
the watermark and compact the queue", which T-1684 had no reason to know
about.

**Touched symbols stay symbolic.** This module never reads
`VerifyQueueEntry.touched_symbols` at all (attribution is deliberately
out of this leaf's scope -- T-1686's own framing: verifying at the tip
proves the batch is green as a whole, but does not by itself attribute
any one finding to any one commit) and never reduces the field to a file
path for its own convenience; that data stays intact for T-1690's
attribution leaf to consume later.

**Wake conditions and where they actually live.** `CoalescingWorker`
holds the debounce/floor DECISION state (`notify()` records a wake,
`tick()` decides whether to actually run); it never runs on a timer of
its own -- `frob.serve._daemon._poll_verify_worker` drives it from the
daemon's existing `DEFAULT_POLL_INTERVAL_S` (20s) cycle, calling
`notify()` when `main`'s HEAD has moved since this job last looked (the
"queue append" wake proxy: a land IS a HEAD move) and calling `tick()`
unconditionally every cycle (cheap -- it is a no-op unless the trailing-
edge debounce window has gone quiet, or the periodic floor has elapsed).
**Disclosed scope cut:** the FS-watch push signal `frob.serve._watch.
WatchThread` already provides is NOT wired to `notify()` yet --
`WatchThread` is instantiated in `frob.serve._socketd.run_socket_daemon`,
outside this ticket's own `src/frob/serve/_daemon.py` scope; filed as a
follow-up rather than silently assumed done (see this ticket's Done
report for the real id).

**Trailing-edge debounce, concretely.** Each `notify()` call pushes the
deadline to `now + debounce_window_s` (default 90s) -- a steady trickle
of lands keeps deferring the run, so a burst of five lands inside the
window produces exactly one verification once the burst actually goes
quiet. The periodic floor (default 300s) is measured from when work FIRST
became pending, independent of how many notifies arrived since -- a
continuous stream of notifies that never lets the debounce window go
quiet still forces a run once the floor elapses, so a busy repo cannot
starve verification indefinitely.

## Symbolic attribution (T-1690)

<!-- frob:describes src/frob/verify/_attribution.py::AttributionError -->
<!-- frob:describes src/frob/verify/_attribution.py::Attribution -->
<!-- frob:describes src/frob/verify/_attribution.py::attribute_batch -->
<!-- frob:describes src/frob/app/ticket_runner/_rapid_sweep.py::_attribute_new_findings -->
<!-- frob:describes src/frob/app/ticket_runner/_rapid_sweep.py::_ticket_is_open -->
<!-- frob:describes src/frob/app/ticket_runner/_rapid_sweep.py::_file_regression_ticket -->

The hard leaf T-1686's own design called out first: when a batch
verification goes red, map each finding to the commit that caused it,
without ever guessing.

**The rule.** A finding anchored at symbol S attributes to the batch
commit whose `VerifyQueueEntry.touched_symbols` REACHES S in the
reference graph (`frob.graph.callgraph.build_reference_graph`'s
caller-symref -> callee-symref edges, walked forward). "The commit that
touched the same file" is the lexical shortcut this module refuses: it is
wrong the moment a change breaks a CALLER rather than the symbol itself,
and it misreports a pure symbol-move between files as a regression the
instant the moved symbol's file changes out from under a path-keyed
identity. `frob.verify._attribution.attribute_batch` never compares a
path string to decide "does this commit explain this finding" -- every
decision walks real symrefs.

**Ambiguity is a first-class outcome.** Exactly one candidate commit
reaching the finding's symbol is `Attribution(status="attributed", ...)`;
zero candidates, or more than one, is `status="unattributed"` -- a
distinct, equally real state, NEVER resolved by picking the newest commit
as a tiebreak (T-1686's own standing decision: a confident wrong
attribution costs more than an honest "unknown", because it sends someone
to read a diff that is not the cause). `candidate_commits` names every
commit that DID reach the finding for the ambiguous case (empty for the
zero-candidate case), so a reader can tell "nobody could have caused
this" apart from "too many could have" at a glance.

**The reachability path is logged, not just the verdict.**
`Attribution.reachability_path` is the actual symref chain the BFS walked
from the owning commit's touched symbol to the finding's own symbol;
`attribute_batch` logs it at INFO for every attributed finding and logs
every candidate commit at WARNING for every unattributed one. An
attribution nobody can audit is an assertion, not evidence (T-1686's own
standing constraint) -- this is how that constraint is actually met, not
just stated.

**Symbol resolution degrades honestly when line information is
missing.** T-1690's declared scope (`_attribution.py`, `_rapid_sweep.py`)
does not include `_land_cmd.py`/`_verify.py`, so the `(rule_id, file)`
finding identity those modules already produce still carries no line
number. When a finding's line IS known, `_resolve_symbol` picks the
single enclosing symbol from `SymbolRecord.span`. When it is NOT known,
every symbol `GraphSnapshot.symbols` records against that file becomes a
candidate target -- strictly better than a bare file-level identity
comparison (a per-symbol reachability check still runs against each
candidate), but weaker than true line-precision: a multi-symbol file
where only one function actually broke can widen the candidate set enough
to manufacture ambiguity that line-precision would have resolved. This is
a disclosed, deliberate degradation, not a silently narrowed guess --
extending the upstream finding identity to carry a line number is future
work outside this ticket's scope.

**"Cannot verify" is never "verified", extended to attribution.** A
reference graph that fails to build/load at all makes EVERY finding's
attribution impossible; `attribute_batch` returns
`Err(AttributionError.GraphUnavailable)` for the WHOLE batch rather than
silently attributing some findings and skipping others.

**Wired into the filer, not a separate report.**
`_rapid_sweep._file_regression_ticket` (T-1684's own regression filer,
called from both the rapid deferred sweep and T-1688's coalescing worker
red branch) now runs every new finding through
`_attribute_new_findings` first (reads the CURRENT durable verify queue
as the batch -- the commits landed since the last watermark advance,
exactly the set a red sweep could have been caused by) before deciding
what to file:

- A finding attributed to EXACTLY ONE commit whose OWNING ticket is
  still open (`_ticket_is_open`: loaded, and not `done`/`dropped`) is
  logged and left OFF the regression ticket entirely -- it already has a
  home, and re-filing it would just be noise.
- Everything else -- attributed to a closed/dropped ticket's commit, or
  genuinely UNATTRIBUTED -- is filed, with the full attribution audit
  trail (commit, symbol, reachability path, or the specific reason
  attribution failed) written into the ticket body so a reader never has
  to re-derive what `attribute_batch` already computed.
- Attribution UNAVAILABILITY (`_attribute_new_findings` returns `{}` when
  the queue is unreadable/empty or the graph cannot be built) degrades to
  the pre-T-1690 behavior verbatim: every finding filed, no attribution
  lines -- "cannot attribute" must never suppress a real regression's own
  ticket.

**What this leaf does NOT do.** The bisect leaf T-1686's own design names
as the handoff for UNATTRIBUTED findings ("tier 3: bisect only the
residue tier 2 cannot attribute") is not built yet -- an unattributed
finding today is filed as an ordinary regression ticket with its
candidate commits named in the body, for a human to read; there is no
automated bisect trigger. This is a disclosed scope cut, not a silent
gap: the bisect leaf is future work this ticket does not claim to close.

**T-1753 follow-up (post-land sweep hygiene).** T-1690's own land
tripped the deferred post-land sweep: `attribute_batch` split along its
tier-1/tier-2/tier-3 seams (`_parse_finding`, `_matching_batch_entries`,
`_attribute_one`) to clear ARCH001's 60-line function threshold, two
lines wrapped under 88 chars (E501), and `_attribute_new_findings`'s
`pairs` parameter widened from `list[tuple[str, str]]` to
`list[tuple[str, str] | tuple[str, str, int]]` -- the annotation was
narrower than what `attribute_batch` itself already accepted, and a real
`ty` invalid-argument-type finding on the test exercising the 3-tuple
(line-bearing) shape caught it. No behavior changed; the split is a pure
extraction and the widened type is a correction, not a new capability.

**T-1754 follow-up (the SAME ty finding, moved not fixed).** T-1753's
own `list[...]` widening on `_attribute_new_findings`'s `pairs`
parameter only moved the invalid-argument-type mismatch to the CALL
SITE: `list` is INVARIANT in Python's type system, so
`_partition_findings_by_attribution`'s own `pairs: list[tuple[str,
str]]` was never actually assignable to `_attribute_new_findings`'s
`list[tuple[str, str] | tuple[str, str, int]]` parameter, no matter how
that parameter's own element-type union was phrased. The real defect was
the CONTAINER type, not the element type: `pairs` is only ever iterated
in `_attribute_new_findings` (never mutated), so the correct, sound type
is a covariant `collections.abc.Sequence[tuple[str, str] | tuple[str,
str, int]]` -- callers passing a `list[tuple[str, str]]` (every
real caller in this module; no caller has ever produced a line-bearing
3-tuple) are naturally accepted, exactly as they should be.
## Backpressure (T-1692)

<!-- frob:describes src/frob/verify/_backpressure.py::BackpressureError -->
<!-- frob:describes src/frob/verify/_backpressure.py::BackpressureCeilings -->
<!-- frob:describes src/frob/verify/_backpressure.py::BackpressureStatus -->
<!-- frob:describes src/frob/verify/_backpressure.py::ceilings_for_profile -->
<!-- frob:describes src/frob/verify/_backpressure.py::current_status -->
<!-- frob:describes src/frob/verify/_backpressure.py::block_until_watermark_advances -->
<!-- frob:describes src/frob/app/ticket_runner/_land_cmd.py::_apply_backpressure -->

Deferral is a credit line, not free money. Without this leaf, T-1687's
durable queue plus T-1688's coalescing worker is a mechanism for
accumulating unbounded unverified debt with a pleasant user experience --
strictly worse than the synchronous sweep it replaces. `frob.verify.
_backpressure` is what makes the deferral BOUNDED.

**Two independent ceilings, either one sufficient to trip.**
`BackpressureStatus.tripped` is `True` the moment EITHER axis is
exceeded:

- DEPTH: the number of entries currently in the verify queue exceeds
  `max_depth`. Depth alone is not enough -- one commit can sit unverified
  all weekend behind a dead worker without depth ever growing past a
  small number.
- AGE: the oldest unverified entry's `enqueued_at` is older than
  `max_age_s`. Age alone is not enough either -- a burst of forty lands
  in quick succession stays inside any reasonable age window while depth
  grows unbounded.

Both axes are read from the SAME durable queue T-1687/T-1688 already
maintain (`frob.verify.queue_status`) -- no new storage.

**Block, never fail.** `block_until_watermark_advances` is the land-path
entrypoint (wired into `frob.app.ticket_runner._land_cmd._land_core_
prepare` via `_apply_backpressure`, called once profile resolution
completes and skipped entirely under `--dry-run`). At the ceiling it does
not refuse the land -- a refusal just makes the developer re-run the
whole thing. It BLOCKS, logging the trip LOUDLY at WARNING (current
depth, age, and the watermark commit being waited on -- T-1686's own
standing rule: "blocking silently is the one unacceptable outcome"), and
ACTIVELY drives the coalescing worker itself
(`frob.verify.run_coalesced_verification`) on each iteration rather than
passively waiting for some other process to drain the queue -- "a block
simply pays back the deferred cost at the moment it came due" (T-1686's
own framing). This is what keeps the design correct even with no daemon
watching the queue: the blocked land IS the thing that unblocks itself.
A persistently red (quarantined) batch that never clears trips
`block_until_watermark_advances`'s own last-resort timeout
(`_DEFAULT_BLOCK_TIMEOUT_S`, 30 minutes) -- logged at ERROR, and the land
PROCEEDS anyway rather than wedging every future land behind one
unresolved batch forever; the loud WARNING trail already logged is the
safeguard, not a second refusal on top of it.

**Per-profile ceilings are the profile-collapse dial.**
`ceilings_for_profile` resolves `fortress` to depth 0 / age 0
(synchronous -- any queued-but-unverified commit trips it, though this
module still BLOCKS rather than refuses even here), `standard` to a
bounded depth/age pair (`_STANDARD_DEFAULT_MAX_DEPTH`=5,
`_STANDARD_DEFAULT_MAX_AGE_S`=3600s, overridable via `frob.toml`'s
`[profile] backpressure_max_depth`/`backpressure_max_age_s`), and
`rapid` to `None`/`None` on both axes -- unbounded, so rapid NEVER
blocks, by construction rather than a separate `if profile == rapid:
skip` branch at every call site.

**Disclosed scope cut.** The full profile-to-queue-depth collapse
(deleting every remaining `if rapid:` seam scattered through the land
pipeline, T-1686's own "payoff" framing) is not this leaf's job --
`_apply_backpressure` is additive, wired alongside the existing
rapid/standard branching `_land_core_prepare` already has, not a
replacement for it. That collapse is later work this ticket does not
claim to close.

**T-1756 follow-up (post-land sweep hygiene).** T-1692's own land
tripped the deferred post-land sweep: 4 E501 lines wrapped under 88
chars across `_land_cmd.py`'s `_land_core_prepare` and
`_backpressure.py`'s `BackpressureError`/`current_status`. No behavior
changed.

## Development profiles (`frob.toml [profile]`, T-1575)

<!-- frob:describes src/frob/tickets/_profile.py::configured_profile -->
<!-- frob:describes src/frob/tickets/_profile.py::effective_profile -->
<!-- frob:describes src/frob/tickets/_profile.py::downgrade_profile_ratchet -->

`frob.tickets._profile` reads `frob.toml`'s `[profile] profile = "..."`
(`ProfileName`: `rapid` | `standard` | `fortress`) -- `standard` is the
default, today's unchanged behavior, whenever `[profile]` or `frob.toml`
itself is absent, so an existing repo's ceremony is never silently
relaxed just because `frob` shipped this feature.

The ticket's own motivation: a small/new repo pays the same fixed land
ceremony (TEST016, the T-1514 double sweep, the T-1463 baseline snapshot
worktree, REL001) as a 950-file repo, and that ceremony is fixed-cost,
not proportional to repo size. `rapid` trims it:

- **No TEST016 on the land path at all.** `_land.py::_check_mutation_
  evidence` checks `effective_profile(worktree)` before its T-1518
  `SYNC_BLOCKING_KINDS` branch; `rapid` skips BOTH the synchronous
  `security`-kind mutation subprocess and the deferred batch-sweep
  enqueue. BUG002 (`bug_repro_violations`) is unaffected by the profile
  and still runs/blocks for bug/security kind regardless of profile.
- **No pre-commit sweep.** `_land_cmd.py::_land` passes
  `pre_commit_sweep=None` to `land()` when rapid.
- **No synchronous post-land sweep, and no baseline thread** (T-1684):
  the post-land sweep runs DETACHED and files a ticket instead of
  reverting; the T-1463 baseline-capture thread is not started at all,
  because the deferred sweep carries its own rolling baseline. See
  "Deferred post-land sweep" below. `standard` keeps both the
  synchronous revert-on-red sweep and the baseline thread verbatim.
- **Evidence/done-report leniency for `kind in {docs, chore}`, and
  REL001 off under rapid** are likewise disclosed as deferred follow-up
  in T-1575's Done report, not wired in this increment -- the ticket's
  land-pipeline seams for both exist but were judged too invasive to
  land safely in the same pass as the two seams above without dedicated
  regression coverage of their own.

**Never relaxed in any profile, `rapid` included:** ledger integrity
checks and LAND-PROOF verification -- neither is gated by
`effective_profile` anywhere.

**`fortress`** parses and round-trips as a `ProfileName` member but has
NO behavioral wiring yet -- a placeholder for a stricter tier a follow-up
ticket defines.

**One-way auto-ratchet.** `effective_profile(root)` -- the read path
every seam above calls, never `configured_profile` directly -- applies a
ONE-WAY ratchet on top of the configured value: if `rapid` and any of
three live thresholds trips (repo file count > 300, total ticket count >
200, concurrent lease count > 5 -- see `frob.tickets._profile`'s module
docstring for the exact primitives each reads and why those numbers),
the ratchet persists to `.frob/profile-ratchet.json` and every future
`effective_profile` call returns `standard` regardless of what `frob.
toml` still says or whether the tripped condition later reverses (files
deleted, tickets archived). `downgrade_profile_ratchet(root, reason=...)`
is the only way back -- an explicit, loudly-logged call, never invoked
from any land-pipeline seam automatically.

<!-- frob:waive DOC006 reason="'frob.toml.j2' is a bare jinja template filename (src/frob/scaffold/data/**), not a dotted code-symbol path -- DOC006's kind-4 matcher has no non-code-extension exclusion, so a bare basename with a 'frob.' prefix reads as a project-namespace symbol lookup and misfires" -->
**`frob scaffold` defaults new repos to `rapid` (T-1576).** Every
`frob.toml.j2` template under `src/frob/scaffold/data/**` writes
`[profile] profile = "rapid"` into a freshly scaffolded project's
generated `frob.toml` -- a brand-new repo is exactly the under-threshold
case `rapid` exists for, and the one-way auto-ratchet above upgrades it
to `standard` automatically the moment it grows past the thresholds.
This does NOT affect an EXISTING repo's `frob.toml`: an absent `[profile]`
key still means `standard` (`configured_profile`'s own documented
default), unchanged by this ticket -- only the scaffold's OWN generated
template content changed.

## Rapid debt and the ratchet override (T-1681)

<!-- frob:describes src/frob/tickets/_profile.py::ratchet_override_enabled -->
<!-- frob:describes src/frob/tickets/_evidence.py::record_rapid_debt -->

The size auto-ratchet above made `rapid` unreachable for exactly the
repos where the ceremony costs the most -- frob's own tree trips the file
and ticket thresholds many times over, so configuring `rapid` here was a
silent no-op. `[profile] override_ratchet = true` (read by
`ratchet_override_enabled`) is the explicit owner decision to keep
`rapid` anyway. Deliberately a config key and not an env var: it lives in
a tracked file, so `git log frob.toml` states exactly which commits were
produced under relaxed rules.

`record_rapid_debt(root, ticket_id, skipped)` is the other half of that
bargain -- every check `rapid` skips appends one self-contained JSON line
(`ticket`, `skipped`, `commit`) to `rapid-debt.jsonl`. TRACKED, not under
`.frob/`: the debt must survive a clone and a `frob clean`, and must be
reviewable in a diff. Best-effort by construction (failing to record debt
never fails a close) but logged at ERROR, because an unrecorded
relaxation is the one outcome that makes the cleanup pass unreliable.
The T-1681 re-verification pass drains that file rather than
re-deriving what happened from git archaeology.

## Deferred post-land sweep (`rapid` only, T-1684)

<!-- frob:describes src/frob/app/ticket_runner/_rapid_sweep.py::spawn_deferred_post_land_sweep -->
<!-- frob:describes src/frob/app/ticket_runner/_rapid_sweep.py::run_deferred_post_land_sweep -->
<!-- frob:describes src/frob/app/ticket_runner/_rapid_sweep.py::RapidSweepError -->

`standard`'s post-land sweep is synchronous and reverts a just-made land
commit when it finds new unscoped errors. Correct when lands are rare,
but it puts a full-repo `frob check` (2-8 minutes on this repo) plus the
T-1463 baseline check on the critical path of every land -- and a
five-minute land is its own correctness risk, because the queue stops
draining and work batches into giant unreviewable lands.

Under `rapid`, `_land_core_finish_post_land` calls
`spawn_deferred_post_land_sweep` instead. That:

1. appends a `rapid-debt.jsonl` line
   (`post-land-unscoped-sweep-deferred`) BEFORE spawning anything, so
   "this commit landed unverified" is a machine-readable fact from the
   instant it is true, even if the child never starts;
2. spawns `frob ticket sweep-async <id> --commit <sha>` detached
   (`start_new_session=True`), logging to
   `.frob/rapid-sweep/<id>-<sha12>.log`;
3. returns immediately -- the land does not wait.

The child runs `run_deferred_post_land_sweep`, which pays exactly ONE
unscoped check by diffing against a **rolling baseline**
(`.frob/rapid-sweep-baseline.json`, the previous deferred sweep's
absolute `(rule_id, file)` set) rather than measuring a fresh pre-land
baseline. Semantics:

- **No baseline yet** (first sweep in a repo, or a corrupt file): record
  one, file nothing. An absent baseline is `None`, never an empty set --
  comparing against assumed-clean would report every pre-existing error
  as newly introduced, which is exactly how an automated filer earns
  being ignored.
- **Unmeasurable check** (refused spawn, timeout, unparsable output):
  `Err(Unmeasurable)`, and the baseline is left untouched, so the next
  sweep still diffs against a set we actually trust.
- **New pairs found:** one `bug` ticket at `high` priority naming every
  new `(rule_id, file)` pair and the commit, scoped to the offending
  files. The commit STANDS -- rapid never rewrites published history,
  because under rapid other agents are already branching from it.
- **Every sweep, red or green, rewrites the baseline.** An error already
  filed as a ticket must not be re-filed by the next land; from then on
  the filed ticket is the record.

**The debt line commits itself (T-1698).** `rapid-debt.jsonl` is tracked
on purpose, and the deferred-sweep record is written AFTER the land
commit is sealed (it names that commit), so it cannot ride along in it.
`_commit_rapid_debt` therefore gives it its own tiny follow-up commit,
staging that one path and nothing else. This is not cosmetic: without it
every rapid land left the shared root checkout dirty and the NEXT land
from ANY agent refused with `DirtyMain` -- one uncommitted line
deadlocked a whole three-agent wave. It stages `rapid-debt.jsonl` alone
rather than `git add -A`, because concurrent lands are racing on that
same root and a blanket add would swallow another agent's in-flight work.
Relatedly, a `DirtyMain` refusal now NAMES the offending paths
(`porcelain_dirty_paths`/`describe_root_dirt`): the original message
said only "root has uncommitted changes", and three agents each burned
minutes without learning it was a single one-line file. T-1740 sharpened
this further: `describe_root_dirt` now calls out STAGED state
explicitly and first ("N STAGED (likely a prior land's leftover index,
T-1740)") whenever any of the dirty paths are staged rather than merely
modified in the working tree -- exactly this deferred-sweep commit's own
failure mode (a killed/refused `_commit_rapid_debt` or land leaving
`rapid-debt.jsonl`/a squash-apply's own content staged) is precisely the
shape that used to read as undifferentiated "uncommitted changes" and
sent an agent looking for working-tree edits instead of the real cause.

`frob ticket sweep-async` is a real subcommand rather than a `-c` code
string so the deferred sweep is inspectable, re-runnable by hand against
any commit, and covered by the same CLI surface tests as every other
verb. It exits non-zero only when the sweep was unmeasurable, so a human
re-running it can tell "verified" from "could not verify".

**The filed regression ticket ALSO needed its own commit (T-1755).**
`_file_regression_ticket`'s `new_ticket(root, spec)` call is the second
tracked-file write the detached sweep makes, and -- unlike the debt
line -- it went uncommitted for the same reason the debt line originally
did: nothing committed it. Root-caused directly (not assumed): `frob.
tickets._new_renumber.new_ticket` is the LIBRARY function -- it takes
`ledger_lock`, calls `write_ticket`, and returns; the T-1130/T-1615
auto-commit (`commit_ticket_ledger_change`) lives entirely in the CLI
dispatch layer (`frob.app.ticket_runner`'s verb table), which a
programmatic caller like the sweep never reaches. This confirms the
THIRD candidate this incident's own investigation named as most likely:
T-1615's uniform auto-commit covers the CLI surface, not programmatic
callers -- a wider gap than this one call site, filed separately (see
this section's own citation below for the real id) so the next
detached/programmatic ledger writer does not rediscover the same hole.

`_commit_regression_ticket` closes THIS call site: after `new_ticket`
succeeds, it calls `commit_ticket_ledger_change` directly -- the SAME
scoped `git add <ledger pathspecs> && git commit -- <ledger pathspecs>`
primitive `frob ticket new`/`drop`/`fail`/`start` already funnel
through, never a bare `git commit`/`git add -A` (T-1740's own incident:
a blanket add on a root checkout concurrent lands are racing against
published 1416 lines of another agent's in-flight work under an
unrelated commit message). A commit failure is logged at ERROR, naming
the regression ticket id and stating explicitly that the next land will
refuse with `DirtyMain` -- the sweep's own regression ticket is already
durably filed by the time this runs, so a commit failure here degrades
to "dirty root, logged loudly", never to "the ticket silently
vanishes".

**`describe_root_dirt` now names the likely author, not just the
paths (T-1755).** An agent hitting `DirtyMain` from a dirty `tickets.md`/
`rapid-debt.jsonl` is, per this incident's own root-cause read, always
correctly isolated from root and structurally unable to investigate WHO
left it dirty -- naming the paths alone (T-1698) still left "now what"
unanswered. When EVERY dirty path matches the sweep's own known writes
(`rapid-debt.jsonl`, `tickets.md`), the refusal now says so explicitly:
"likely author: a sweep child that filed something and did not commit
it". A MIXED dirty set (a sweep-owned path plus something else) is
deliberately NOT attributed to the sweep -- misattributing a genuinely
unknown second cause would send the next agent looking in the wrong
place just as surely as no attribution at all.

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
    kind_history: tuple[str, ...] = ()   # T-1616: `frob ticket kind` changes made
        # AFTER evidence/a Done report already existed, append-only, e.g.
        # "2026-08-06 bug->feature evidence=3 done_report=yes" -- surfaced as a
        # WARNING at `frob ticket land` (docs/modules/gates.md#bug002-t-1421...)
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

class ForceOverrideEntry(BaseModel):   # T-1762, frob.tickets._force_override
    command: str        # e.g. "ticket archive", "ticket land --finish"
    guard: str           # the safety guard bypassed (e.g. "T-1715 worktree-in-use refusal")
    target: str          # what --force was applied to (ticket id(s), worktree path)
    reason: str           # required, never blank -- refused otherwise
    actor: str
    at: date
```

### `--force` audit trail (T-1762)

`ScopeChangeEntry`/`AcceptanceAmendmentEntry`/`EvidenceChangeEntry`
(T-0455/T-1422/T-1733) and `AckAuditEntry` (T-1317,
docs/modules/gates.md#ack-accountability-t-1317) all establish the same
append-only-audit-record discipline for a mutation that can discharge a
tracked obligation more cheaply than the honest route; T-1762 applies it
to `--force`. `frob ticket archive --force` (overriding the T-0843
live-cross-worktree-lease refusal) and `frob ticket land --finish
--force` (overriding the T-1715 worktree-in-use refusal) both now
require `--reason`/`--reason-file` WHEN the guard they bypass would
actually have fired (a `--force` that overrides nothing is a no-op,
guard-wise, and demands no reason for it) -- refusing otherwise -- and
log a WARNING naming the guard skipped before appending one
`ForceOverrideEntry` to `force-overrides.jsonl` (repo root, git-tracked,
append-only, the same "root-level JSONL audit log" shape this repo's own
`rapid-debt.jsonl` already established) via `frob.tickets._force_
override.record_force_override`.

### Archive: the live-worktree guard (T-1750)

`frob ticket archive` (v1 monofile mode -- `tickets.md`/
`tickets-archive.md`) moves every done/dropped ticket from the active
ledger into the archive file with a whole-file `write_all`/`write_archive`
rewrite of BOTH files (`_write_archived_and_active`). That rewrite is a
DELETE from one tracked file plus an ADD to another, from git's
perspective -- not a rename it can reconcile on its own -- so a worktree
whose OWN checkout of `tickets.md` still shows a ticket ACTIVE, merging
`main` AFTER that ticket has been archived there, can produce a ledger
with the ticket's id present in BOTH `tickets.md` and
`tickets-archive.md` (T-1437's `DuplicateId`-collapse recovery path exists
because of exactly this). The 2026-08-07 incident this section documents
was the worse version: 62 tickets moved in one `archive` call while an
agent's worktree was live, and that worktree's next `git merge main`
reproduced the duplicate-id class at scale, forcing a full playbook
section-10b recovery pass.

`archive` already refused (`Err(ArchiveLiveLeaseExists)`) when a ticket
the call would itself move still held a live cross-worktree lease
(T-0843/`_refuse_archive_if_leased`) -- but that check is scoped to
tickets THIS call touches, not to whether any OTHER worktree exists at
all, and the incident's agent held a lease for a completely different,
unrelated ticket. T-1750 adds a second, broader guard ahead of it,
`_refuse_archive_if_other_worktrees_live`: `archive` now refuses
outright whenever `git worktree list` (via `frob.tickets._reconcile.
_live_worktrees`, the same primitive `frob ticket reconcile` already
uses) shows ANY linked worktree besides the primary checkout, naming
every one found, with `--force` as the documented override for an
operator who has confirmed it is safe. This is deliberately the v1
MONOFILE path only -- `archive_v2` (design section 4.3, `git mv
tickets/T-#### tickets/archive/T-####` per ticket) does NOT get this
guard, because its per-ticket-directory move is a real git rename
between two disjoint paths, which a concurrent worktree's `git merge`
resolves correctly with no custom splice code at all (`TestArchiveV2.
test_archive_v2_regression_two_sided_divergence_no_clobber` reproduces
the exact two-sided-divergence shape against `archive_v2` and passes
unforced, with a second worktree live throughout) -- the DuplicateId
failure mode this guard exists to prevent cannot occur on that path, so
gating it the same way would only cost every v2-mode drive real
throughput for no safety gained.

TICK003 (`docs/modules/gates.md#tick003`) is the OTHER half of this
incident: it forced `archive` to run at an arbitrary, non-quiet moment
mid-drive by escalating to a hard ERROR once too many closed tickets sat
un-archived. `_tick003_stale_archive`'s warn/error thresholds moved from
`(20, 60)` to `(10, 400)` (T-1750) -- warn much earlier, so ledger
housekeeping is visible and schedulable well before it becomes urgent,
and error only far above any threshold a real drive would organically
reach, so the gate can no longer itself create the exact "forced to
archive right now, unsafely" deadlock the incident hit. The hard ERROR
tier still exists as an absolute backstop (an ever-growing, truly
unbounded active ledger is a real hygiene problem, not just an
aesthetic one) -- it is pushed far enough out that reaching it means the
housekeeping was neglected for a long time, not that a drive was simply
busy.

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
estimate", never silently omits the line. T-1528 adds
`median_cycle_days`: the median calendar days from `created` to each
ticket's FIRST observed done transition, mined in the same single
history pass as the landed histogram (no second walk), `None` until
anything has completed -- consumers label that "n/a", never omit.
`frob ticket list` renders an always-on one-line state-census footer
from the already-loaded queue, and `frob ticket list --stats` appends a
second line (trailing filed/landed/net rates, median cycle, ETA) built
from this report; --stats inherits the full-history mining cost until
T-1330 lands.

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

### `frob ticket accept --amend`/`--remove` (T-1422)

`frob ticket accept` could, until this ticket, only APPEND criteria. There
was no supported way to correct a mis-specified one or drop one that was
never satisfiable -- both cases occurred for real: T-1411's criterion [0]
was mis-specified (a comment naming no in-scope identifier was ALSO
matched by a poorly-named-variable's own trailing comment, so implementing
it faithfully would have silenced the exact case the rule exists to
catch), and ten burn-down tickets asserted "0 TEST005 findings under
package X" against packages holding 100-400 findings -- unsatisfiable by
construction, no single dispatch can close that. The only available
workarounds were hand-editing `tickets.md` (which has corrupted the ledger
for real -- a stray ` #` inside a plain YAML scalar starts a comment,
truncating the mapping and taking every gate down as a hard failure) or
filing a successor ticket just to carry the same acceptance forward under
a new id.

`frob.tickets.amend_acceptance(root, ticket_id, index, new_text, *,
reason)` replaces `acceptance[index]`'s text with `new_text`; `frob.
tickets.remove_acceptance(root, ticket_id, index, *, reason)` drops
`acceptance[index]` outright. Both:

- REQUIRE a non-blank `reason`, mirroring `mutate_scope`'s `ScopeChangeReasonMissing`
  discipline exactly (`Err(TicketError.AcceptanceAmendReasonMissing)` if
  blank). The reason is the entire point: an amendment with no reason is
  indistinguishable from silently rewriting history, the same hand-edit
  workaround this verb exists to replace.
- Append an `AcceptanceAmendmentEntry` (`op`, `index`, `old_text`,
  `new_text` (`None` for a remove), `reason`, `actor`, `at`) to the
  ticket's `acceptance_amendments` tuple -- never edited or removed once
  written, only appended to, same append-only audit discipline as
  `ScopeChangeEntry`/`FailureEntry`. The OLD text is always preserved, so
  the ledger keeps a full record of exactly what changed and why.
- Are refused outright (`Err(TicketError.AcceptanceAmendTerminalState)`) on
  a ticket already DONE or DROPPED -- amending acceptance after close is
  exactly the "quietly move the goalposts after the fact" case this
  ticket exists to make impossible.
- Refuse an out-of-range `index`
  (`Err(TicketError.AcceptanceAmendIndexOutOfRange)`).
- Are held under `ledger_lock` end to end (T-0458 single-writer
  invariant), same as every other mutation here.

`amend_acceptance` carries forward any evidence already bound to the
criterion unchanged -- amending the TEXT does not invalidate a binding a
reviewer already made; rebind via `frob ticket evidence --accepts` if the
binding itself needs re-verifying against the new wording.

**The abuse case, named plainly.** Amending a criterion is a legitimate
correction when the criterion was WRONG (mis-specified, like T-1411's
[0]). It is goalpost-moving when the criterion was RIGHT and the work fell
short. This mechanism cannot fully automate that distinction -- only a
human or reviewer reading `reason` against the actual diff can. What it
does instead is make the change REVIEWABLE rather than silent: a mandatory
reason, permanently recorded, surfaced everywhere a reviewer looks (never
buried) -- `frob ticket show` prints an `acceptance_amendments:` block
after the acceptance list, and `compose_done_report` (`frob.tickets.
_reporting`) renders an `### Acceptance amendments` section in the SAME
Done report the amending ticket writes, whenever `Ticket.
acceptance_amendments` is non-empty.

CLI: `frob ticket accept <id> --amend INDEX --text TEXT (--reason TEXT |
--reason-file PATH)` and `frob ticket accept <id> --remove INDEX (--reason
TEXT | --reason-file PATH)` (`frob.app.ticket_runner._mutate._accept_
amend`/`_accept_remove`, same "this command does nothing but forward"
pattern as `_scope`/`_accept`'s append mode). `--reason-file` reads the
reason verbatim from a path instead of the shell, same T-0737 rationale as
`frob ticket scope --reason-file` (a backtick or `$(...)` in an inline
`--reason` is expanded by the shell before frob ever sees it). `--amend`
and `--remove` are mutually exclusive with each other and with the default
append mode (`--criterion`/`--criterion-file`) in one invocation.

```python

class AttachmentSource(BaseModel):
    path: Path | None           # None means clipboard

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
    # T-1384: `close`/`reverify` refuse (when the caller injects
    # `own_obligations_clean=False`) while the ticket's OWN diff leaves a
    # new-symbol doc edge, testsuite declaration, or REL001 bump
    # outstanding -- see `transition`'s `own_obligations_clean` parameter
    # above.
    OwnObligationsUnclean = (
        "this ticket's own diff leaves a new-symbol doc edge, testsuite "
        "declaration, or REL001 bump outstanding"
    )
    # T-1721: `_splice_only_ticket`'s base-aware sibling-edit comparison
    # (see "`frob ticket land`" below) refuses rather than silently
    # picking a side when a SIBLING ticket's section was independently
    # edited on both main and the worktree since their common base.
    SiblingLedgerEditConflict = (
        "a sibling ticket's ledger section was independently edited on "
        "both main and the worktree since their common base, in ways "
        "that do not converge"
    )

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
<!-- frob:describes src/frob/tickets/_store.py::_yaml_loader -->
<!-- frob:describes src/frob/tickets/_store.py::_coverage_tracer_active -->
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
<!-- frob:describes src/frob/tickets/_store.py::v2_ticket_dir -->
<!-- frob:describes src/frob/tickets/_store.py::v2_ticket_path -->
<!-- frob:describes src/frob/tickets/_store.py::v2_done_report_path -->
<!-- frob:describes src/frob/tickets/_store.py::v2_attachments_dir -->
<!-- frob:describes src/frob/tickets/_store.py::write_done_report -->
<!-- frob:describes src/frob/tickets/_store.py::read_done_report -->

`frob/tickets/_store.py` implements the single-file-ledger-vs-legacy-dir
backend switch described under Storage above; `frob/tickets/__init__.py`
(the Public API) is the only caller.

### Migration to v2 (T-1259, docs/design/ledger-v2.md section 7)

<!-- frob:describes src/frob/tickets/_store.py::migrate_v1_to_v2 -->
<!-- frob:describes src/frob/tickets/_store.py::_migrate_one_v2 -->
<!-- frob:describes src/frob/tickets/_store.py::_split_done_report -->

`migrate_v1_to_v2(root)` is the one-shot, reversible v1 -> v2 migrator
(design section 7, deliverable 1): it reads today's `tickets.md`/
`tickets-archive.md` via `_parse_ledger`, writes each ticket into a
v2-mode `tickets/T-####/ticket.md` (active) or `tickets/archive/T-####/
ticket.md` (already-archived), splits any embedded `## Done report`
section out into its own `done-report.md` (`_split_done_report`, the
mechanical inverse of `_models.replace_done_report_section`'s splice),
and `git mv`s any legacy `tickets/attachments/<id>/` directory to the
ticket's own `attachments/`. It does NOT delete `tickets.md`/`tickets-
archive.md` in the same call -- rollback is `rm -rf tickets/T-*/
tickets/archive/` while both monofiles are untouched. A no-op (`Ok(0)`)
once the repo is already v2-mode, so it is safe to invoke more than
once. Golden round-trip coverage (a fixture ledger covering a done
ticket with a Done report, a queued ticket with `blocked_by`, a ticket
with attachments, an archived ticket, and a draft-id ticket, migrated
then re-loaded and compared field-for-field) lives in
`tests/test_tickets_migration.py`.

```python
# frob/tickets/_store.py
def migrate_v1_to_v2(root: Path) -> Result[int, TicketError]
    # Reads tickets.md/tickets-archive.md, writes each ticket into its v2
    # directory (ticket.md + done-report.md + moved attachments/),
    # WITHOUT deleting the monofiles. Ok(0) no-op if already v2-mode.
def _split_done_report(body: str) -> tuple[str, str | None]
    # The mechanical inverse of replace_done_report_section: splits a
    # v1-mode body into (body_without_done_report, done_report_text).
```

**Deprecation window (LEDGERV1001, `frob.gates._tickets_gate`)**: once
this migration path shipped, `frob check` on any repo that still has a
real `tickets.md` or legacy `tickets/*.md` on disk (not merely
`_store_mode`'s fresh-repo default) reports one LEDGERV1001 finding
naming `frob ticket migrate --to v2` as the remedy -- a WARNING while
today's date is on or before the recorded sunset below, escalating to a
hard ERROR once it has passed (mirrors the DEPR00x family's own
warn-in-window/error-past-expiry shape, `_deprecated_is_expired`/
`_depr004_violations`, one level up at the whole-ledger-backend
granularity instead of a single symbol). Silent for a repo that is
already v2-mode, and silent for a repo with no ledger content of either
shape at all.

Recorded compatibility window: **opened 2026-08-03 (T-1259 landing this
migrator), sunset 2027-02-02** (`_LEDGERV1_SUNSET` in
`frob.gates._tickets_gate`). Moving the sunset date is a docs+code pair
-- update this note and the constant in the same change so they can
never silently disagree. This repo's own ledger is deliberately NOT cut
over to v2 by this landing (an active multi-agent drive is in
progress); the coordinator flips it in a quiet window per this ticket's
Done report.

**Fresh-repo default cutover (T-1553, LANDED):** `_store_mode`'s final
fallback now returns `"v2"`, not `"single"` -- a repo with NO ledger
content at all (no `tickets.md`, no legacy `tickets/*.md`, no
`tickets/T-####/`) starts on v2 layout from its very first `new_ticket`
call. This does not affect any EXISTING v1-mode repo (a real
`tickets.md` on disk still reads as `"single"`, per the mode-detection
order above) -- only the fresh-repo case changes. `frob ticket migrate
--to v2` remains the path for an existing v1 repo to opt in.

### v2 backend (T-1254, docs/design/ledger-v2.md section 1)

A THIRD backend alongside `single`/`dir`: one directory per ticket,
`tickets/T-####/`, holding `ticket.md` (frontmatter + body, same shape
`_serialize_ticket`/`_parse_ticket_file` already produce/consume for
legacy dir mode) plus a `done-report.md` split OUT of the body, plus a
self-contained `attachments/` directory. `_store_mode` detects it FIRST
(any `tickets/T-*/ticket.md` present) so it takes priority over a stray
`tickets.md`/legacy `tickets/*.md` left behind mid-migration. At the
time this backend was added it was additive only, not yet the
fresh-repo default -- T-1553 later flipped that default to v2 (see the
"Fresh-repo default cutover" note above); an EXISTING v1-mode repo is
unaffected either way, since `ledger_path(root).exists()` still wins.

`write_ticket`'s v2 branch takes the per-ticket `ticket_lock` (not the
whole-ledger `ledger_lock`) so two callers writing DIFFERENT ticket ids
never contend -- the structural fix docs/design/ledger-v2.md's incident
museum traces every ledger-churn race back to. `load_all`/`write_all` gain
matching v2 branches (glob `tickets/T-*/ticket.md`, prune stale
directories on a wholesale replace) alongside their existing single/dir
branches.

```python
# frob/tickets/_store.py
def v2_ticket_dir(root: Path, ticket_id: str) -> Path
    # The tickets/T-####/ directory a v2-mode ticket owns -- the directory
    # name IS the id, never a slugified title (a retitle never renames it).
def v2_ticket_path(root: Path, ticket_id: str) -> Path
    # tickets/T-####/ticket.md -- the frontmatter+body file.
def v2_done_report_path(root: Path, ticket_id: str) -> Path
    # tickets/T-####/done-report.md -- the Done report, split OUT of
    # ticket.md's body so it is an independently mergeable/lockable write.
def v2_attachments_dir(root: Path, ticket_id: str) -> Path
    # tickets/T-####/attachments/ -- the self-contained attachment layout
    # (design section 8's open question, resolved in favor of self-
    # contained), distinct from the legacy shared attachments_dir().
def write_done_report(root: Path, ticket_id: str, report_text: str) -> Result[None, TicketError]
    # v2-mode only: atomically writes report_text to done-report.md, held
    # under ticket_lock (not ledger_lock) since it only touches one ticket.
def read_done_report(root: Path, ticket_id: str) -> str | None
    # v2-mode only: done-report.md's raw text, or None if it does not
    # exist yet.
```

`frob.tickets._reporting.set_done_report` branches on `_store_mode`: in
`v2` mode it calls `write_done_report` instead of splicing a `## Done
report` section into `ticket.body` via `replace_done_report_section` --
the ticket's own frontmatter/description is left untouched. `attach`'s
`_next_attachment_path`/`_record_attachment` route through
`v2_attachments_dir` in v2 mode; `Attachment.path` is still stored
relative to `tickets_dir(root)` in BOTH modes (never relative to the
ticket's own directory), matching `frob.gates`' COV004 sha-verification
convention (`Path("tickets") / attachment.path`) -- v2's own attachment
dir already nests under `tickets_dir`, so no COV004-side change was
needed.

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
    # Every ticket in tickets-archive.md (empty dict if the file is absent).
    # T-1206: cached in .frob/tickets-archive-cache.json, keyed by the
    # archive file's own sha256 content hash (never mtime) -- an unchanged
    # archive is never reparsed; any byte change invalidates the cache.
def _coverage_tracer_active() -> bool
    # T-1204: thin re-export of frob.yaml_io._coverage_tracer_active,
    # kept under this name for this module's own direct-import test
    # coverage. T-1333: True when sys.gettrace() is a coverage.py tracer
    # (detected by the active tracer callable's __module__ starting with
    # "coverage") -- both bare `coverage run` and pytest-cov install
    # their tracer this same way. Used by _yaml_loader to avoid a known-
    # bad CSafeLoader/coverage.py interaction (see below).
def _yaml_loader() -> type[yaml.SafeLoader]
    # T-1204: thin re-export of frob.yaml_io.fast_yaml_loader, kept under
    # this name for this module's own direct-import test coverage and
    # the frob.gates.__init__ re-export (_tickets_yaml_loader) that
    # already depends on this import path. See "Shared YAML loader
    # selection (frob.yaml_io)" below for the full T-1206/T-1333
    # rationale, now the single home for it -- every OTHER per-document
    # YAML parse site in the repo (frob.registry._models, frob.gates.
    # decisions, frob.gates.invariants, frob.vet._lockfile) was left on
    # the slow pure-Python default until T-1204's PERF010 burn-down
    # wired them to this same shared helper instead of each re-deriving
    # the libyaml-availability-and-coverage-tracer check.
def write_archive(root: Path, tickets: dict[str, Ticket]) -> Result[None, TicketError]
    # Replaces tickets-archive.md wholesale (same ledger section format,
    # distinct header).
def attachments_dir(root: Path, ticket_id: str) -> Path
    # tickets/attachments/<id>/ for a given ticket (both storage modes).
def store_mode(root: Path) -> str
    # Which backend a repo uses: 'v2' if any tickets/T-####/ticket.md
    # directory exists (ledger v2, docs/design/ledger-v2.md section 1 --
    # checked FIRST, taking priority over a stray legacy tickets.md/
    # tickets/*.md left behind mid-migration), else 'single' if tickets.md
    # exists, else 'dir' if only legacy tickets/*.md files exist, else
    # 'single' (fresh-repo default).
def serialize_ticket(ticket: Ticket) -> str
    # Renders a Ticket to legacy ---frontmatter + body (dir-mode file text).
def parse_ticket_file(path: Path) -> Result[Ticket, TicketError]
    # Splits a legacy ticket file into frontmatter + body and validates it.
def load_all(root: Path) -> Result[dict[str, Ticket], TicketError]
    # Every ticket in the repo as an id -> Ticket map, backend-agnostic.
def write_ticket(root: Path, ticket: Ticket) -> Result[None, TicketError]
    # Upserts one ticket into whichever backend the repo uses (atomic).
    # T-1536: single mode's spliced ledger text is re-parsed in memory
    # before it is ever written to disk (`_post_splice_integrity_check`) --
    # the write refuses (Err(LedgerIntegrityViolation)) if the result fails
    # to re-parse or silently drops a sibling id, instead of persisting a
    # ledger the next read could fail to load.
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

## Shared YAML loader selection (frob.yaml_io)

<!-- frob:describes src/frob/yaml_io.py::fast_yaml_loader -->

T-1204's PERF010 burn-down moved the T-1206/T-1333 fast-loader-selection
logic above (`_yaml_loader`/`_coverage_tracer_active`) out of this module
into `frob.yaml_io`, the single shared home for "pick the fastest SAFE
YAML loader available, correctly, once" -- this module keeps thin
re-exports under their original names (see the docstrings above) so its
own direct-import tests and `frob.gates.__init__`'s existing
`_tickets_yaml_loader` re-export keep working unchanged.

```python
# frob/yaml_io.py
def fast_yaml_loader() -> type[yaml.SafeLoader]
    # yaml.CSafeLoader (libyaml) when installed, else the pure-Python
    # yaml.SafeLoader -- falls back to SafeLoader regardless of
    # __with_libyaml__ whenever a coverage.py trace function is active
    # (T-1333: a known-bad CSafeLoader/coverage-tracer interaction).
    # Every non-test yaml.load/yaml.safe_load call site in the repo
    # should pass Loader=fast_yaml_loader() rather than re-deriving this
    # check -- frob.registry._models.load_registry_dir, frob.gates.
    # decisions.load_decisions, frob.gates.invariants._frontmatter_dict,
    # and frob.vet._lockfile._parse_pnpm_lock were all found on the slow
    # pure-Python default (PERF010) and wired to this helper in the same
    # pass that fixed PERF010's own false-positive blind spot for the
    # Loader=<helper>() indirection this function's callers now use
    # (`frob.perf._hotpath_smells._has_loader_indirection`).
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
