# frob.tickets -- data models, storage internals, organization primitives

Part of the `frob.tickets` reference, split out of `docs/modules/tickets.md` by T-1780 so this subject's own lease no longer blocks every other ticket working a different one; see [`docs/modules/tickets.md`](tickets.md#split-files-t-1780) for the full split index.

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

**`frob agent env` also bounds pytest-xdist under a fleet (T-2221).**

<!-- frob:describes src/frob/tickets/_worktree_guard.py::agent_env_exports -->

**Incident:** `pyproject.toml`'s `addopts` includes `-n auto`, which
`pytest-xdist` resolves against the machine's whole CPU count -- correct
for a single developer, wrong the moment several dispatched agents each
resolve `auto` independently in their own worktree. Measured: 4 concurrent
agents on a 12-CPU machine each requesting ~12 workers, `LOAD 28.2`.

`agent_env_exports(root)` (T-0574's `frob agent env` choke point) now also
computes `PYTEST_XDIST_AUTO_NUM_WORKERS` -- the env var `pytest-xdist`
3.8.0 itself reads when resolving `-n auto` (`xdist/plugin.py`) -- and
includes it in the exported env whenever `read_all_leases(root)` (the same
real, cross-worktree lease side-channel `doable()` already uses, never a
`ps`-parsed process count) shows at least one OTHER live agent lease. The
bound is `max(1, cpu_count // (existing_leases + 1))`, treating this
agent as one more concurrent claimant alongside whatever `existing_leases`
already holds. No other live lease -- the single-developer path --
exports nothing at all, so `-n auto` resolves against xdist's own default
(the full CPU count) unaffected.

This is the single choke point for the fix: every pytest spawn that
inherits this exported shell environment -- an agent's own raw `uv run
pytest` invocation, or any of the several frob-internal `guarded_
subprocess_run`/`subprocess.run` pytest spawns across this codebase that
do not themselves override `addopts` -- picks up the same bound without
the rule being duplicated at each spawn site. (`_verify.py`'s own direct-
pytest fallback, `_run_pytest_directly`, is unaffected either way: it
already passes `-o addopts=`, fully overriding `addopts` and never
invoking `-n auto` in the first place.)

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
  T-1892: a command whose captured stdout+stderr is EMPTY is also
  refused (`Err(EvidenceCmdSilent)`), even on exit 0 -- closes the hole
  where `true`/`grep -q`/`: ` all silently satisfied `--evidence-cmd`
  with the sha256-of-empty-string digest, a passing check that never
  actually observed anything. Prefer a chatty check (`grep -c`/`grep
  -n`) over a silent one (`grep -q`) when authoring a `--evidence-cmd`.
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

## Disclosed-remainder-requires-follow-up guard at close (T-1648)

`frob ticket close` (and `frob ticket reverify`) refuses to close a ticket
whose Done report discloses unfinished work but names no real, open
follow-up ticket. This closes the "closed with disclosed unfinished work,
silently dropped" incident class: T-1420 split 1 file and disclosed 52
more still over the LARGE001 threshold, closed clean, and the 54 warnings
had no owner until a coordinator noticed by hand and filed T-1646; T-1204
did the same for 5 undone PERF rule families (T-1647).

- `frob.tickets._reporting.disclosure_shaped_language(text)` is a
  deliberately generous phrase match over a Done report's own narrative
  (`"not attempted"`, `"still outstanding"`, `"out of scope for this
  pass"`, and similar) -- not an English parser. A false positive costs
  one extra `Filed:` line; a false negative is the incident this exists
  to prevent, so the heuristic errs toward firing.
- `frob.tickets._reporting.filed_followup_tickets(body)` parses every
  `T-####` id named on a `Filed:` line -- the existing playbook Done-report
  convention (`docs/guides/agent-playbook.md` section 8), now made
  checkable rather than free text.
- `frob.app.ticket_runner._close_cmd._undisclosed_remainder_reason(root,
  ticket)` combines the two: if disclosure-shaped language is found and
  NONE of the `Filed:` ids resolve to a real, still-open ticket (reusing
  `frob.gates._OPEN_STATES`, the same "open" definition WIRE002's
  `follow_up=` check already uses), `_close`/`_reverify` refuse with a
  message naming the matched phrase and the remedy (file a follow-up,
  add a `Filed: T-####` line, retry).

This deliberately reuses WIRE002's own precedent (an escape hatch must
bind to a real, open ticket, not free-text prose) rather than inventing a
second obligation-tracking mechanism. It does not attempt to verify that
the filed ticket's own content actually describes the disclosed
remainder -- only that SOMETHING checkable was recorded, keeping the
ceremony cheap enough that honest disclosure is not punished.

## Mega-glob scope refused at start (T-1866)

`frob ticket start` REFUSES (exit 1) a scope containing a mega-glob
instead of merely warning about it -- promotes T-1645's WARN-only
`_warn_scope_breadth_on_start` nudge to a hard refusal at
`frob.app.ticket_runner._lifecycle._refuse_over_broad_scope_on_start`,
called before the state transition to `IN_PROGRESS` (before the
whole-tree lease is taken, not after).

"Mega-glob" is decided by the SAME breadth measure TICK009 already
computes -- `frob.tickets.large_glob_warnings`/`scope_breadth_context`
(T-0453): a glob whose match set exceeds the configured threshold, or a
chronically-broad literal (`OVER_BROAD_LITERAL_GLOBS`) -- never the bare
presence of `**` in the glob's spelling. A scope of `docs/design/T-1866-
notes.md` and a scope of `docs/**` differ by what they MATCH, not by how
they are typed.

This adds no new mechanism: `large_glob_warnings` itself is unchanged,
and `frob ticket scope-ack` (T-1484's existing WAVE14-B escape hatch,
`ticket.scope_breadth_ack`) is reused wholesale as T-1866's own bypass --
a ticket whose honest scope really is a package glob (a genuine epic/
umbrella) acknowledges it explicitly and starts cleanly; every other
mega-glob scope is refused, naming the offending globs and the two
remedies (narrow via `scope --remove/--add`, or `scope-ack`) in the
refusal message.

A `QUEUED` ticket is never checked by this refusal -- `start` always
transitions OUT of queued/planned, so the check only ever runs at the
one point T-1645 already identified as correct: the author has the code
open and a broad scope has started actually costing other tickets. The
"treat a queued scope as a prediction, not yet demandable" rule from
T-1645 is preserved unchanged, by construction rather than by a separate
state check.

MEASURED, freshly re-run (see T-1866's own Done report for the exact
command): 39 of 72 currently-queued tickets carry at least one mega-glob
entry. The queue moves constantly under concurrent dispatch, so this
number is a point-in-time measurement, not a static fact -- re-run the
same query to get the current one rather than trusting either this
figure or T-1866's own originally-filed census, which measured a
slightly different, now-stale queue snapshot.
