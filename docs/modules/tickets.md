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

```python
# frob/tickets/__init__.py
def load_queue(root: Path) -> Result[TicketQueue, TicketError]
    # Active store AND tickets-archive.md merged (id-collision checked) --
    # the resolution source for blocker/parent lookups and gate joins, so
    # an archived (done/dropped) ticket never reads as unknown.
def load_active(root: Path) -> Result[TicketQueue, TicketError]
    # Active store ONLY, not the archive -- what `frob ticket list`/`doable`
    # display against, so archived tickets never bloat them (T-0096).
def new_ticket(root: Path, spec: TicketSpec) -> Result[Ticket, TicketError]
    # Allocates next id (T-####), writes file atomically.
def doable(queue: TicketQueue) -> tuple[Ticket, ...]
    # state in {queued, planned} and no open blockers, ordered oldest-first.
def transition(root: Path, ticket_id: str, to: TicketState) -> Result[Ticket, TicketError]
    # Enforces the state machine; done additionally requires evidence
    # non-empty and a Done report section (the gate re-verifies).
def record_failure(root: Path, ticket_id: str, entry: FailureEntry) -> Result[Ticket, TicketError]
    # Appends to the failure log so no future session retries a dead end.
def attach(root: Path, ticket_id: str, source: AttachmentSource,
           caption: str) -> Result[Attachment, AttachError]
    # source is a file path or clipboard; stores under tickets/attachments/.
def add_evidence(root: Path, ticket_id: str, node_ids: Sequence[str],
                  collected: frozenset[str]) -> Result[Ticket, TicketError]
    # Validates node_ids against `collected` (frob.testing.collect_python_tests
    # node ids, supplied by the caller) and appends the resolvable ones;
    # rejects the whole batch as Err(UnknownEvidence) if any id is
    # unresolvable -- closes the COV003-after-close gap at write time.
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

# frob/tickets/clipboard.py
def clipboard_image() -> Result[bytes, ClipboardError]
    # PNG bytes from the platform clipboard, via the first working backend.
def clipboard_has_image() -> bool
    # Cheap probe used to decide whether to offer the interactive prompt.
```

## State machine

```
queued -> planned -> in-progress -> done
   |         |            |-> blocked -> in-progress
   |         |            |-> queued        (yield: agent gives it back)
   +---------+------------+-> dropped      (explicit, with reason in body)
```

Any other transition is `Err(InvalidTransition)`. `done` and `dropped` are
terminal. Cutting scope is `dropped` with a reason -- recorded, not deleted.

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
ledger plus every code reference via `renumber_one`. This is deliberately
NOT wired to run automatically anywhere yet -- T-0176 (`frob ticket land`)
is the queued ticket that will call it as part of an atomic merge/land
step. Until T-0176 lands, finalizing a draft is a manual
`frob ticket renumber <draft-id> <next-id>` (or a direct `finalize_draft`
call from a script).

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
<!-- frob:describes src/frob/tickets/_store.py::store_mode -->
<!-- frob:describes src/frob/tickets/_store.py::serialize_ticket -->
<!-- frob:describes src/frob/tickets/_store.py::parse_ticket_file -->
<!-- frob:describes src/frob/tickets/_store.py::load_all -->
<!-- frob:describes src/frob/tickets/_store.py::write_ticket -->
<!-- frob:describes src/frob/tickets/_store.py::write_all -->
<!-- frob:describes src/frob/tickets/_store.py::migrate_to_ledger -->
<!-- frob:describes src/frob/tickets/_store.py::atomic_write -->

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

- `pydantic`, `typani`; stdlib `subprocess` (clipboard), `hashlib`, `date`.
- PyYAML (frontmatter) -- already transitively present; pinned direct.
- No dependency on `frob.graph` (gates join the two; see `docs/rework.md`).

## Integration points

- `frob.gates`: scope gate reads `scope`, coverage gate reads `evidence`
  and joins `frob:ticket`/`frob:todo` edge targets against the queue.
  `tickets_gate` (TICK001/TICK002, T-0162) checks the id-collision invariant
  -- see "Decision record: T-0162" above.
- CLI: `frob ticket new|list|show|doable|plan|start|sweep|migrate|renumber|
  attach|block|close|fail|evidence|archive`. `start` auto-plans a queued
  ticket (both legal steps); `sweep` re-records the pre-work sweep after a
  scope change; `migrate` collapses a legacy dir into the ledger;
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
- **Finalization is not an agent's job today.** A draft id is finalized to
  its permanent sequential id only once it has actually landed on the
  default branch, via `finalize_draft` -- which T-0176 (`frob ticket land`)
  will call automatically as part of an atomic merge/land step. Until
  T-0176 ships, an agent that lands its own worktree's changes onto main by
  hand should call `frob ticket renumber <draft-id> <T-####>` right after
  the merge, before closing out; `frob check`'s TICK002 rule will refuse to
  pass silently if this is forgotten (draft ids are unwaivable on the
  default branch).
- **A draft id surviving a merge into the default branch is a hard-fail,
  not a warning.** `frob check` (TICK002) makes this loud on purpose --
  see "Why TICK001/TICK002 are unwaivable" above. Treat a TICK002 failure
  the same way as any other unwaivable gate failure: fix the root cause
  (finalize the draft), never suppress it.
