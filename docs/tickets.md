# frob.tickets -- statically-checkable ticket and feature queue

One sentence: a git-tracked queue of tickets (features, bugs, audits,
invariant work) with a state machine, blockers, evidence, failure memory,
and image attachments -- the shared work surface for the human and every
agent, so the bottom of the stack is never silently forgotten.

## Storage

```
tickets/
  T-0042-clipboard-attach.md        one file per ticket
  attachments/
    T-0042/
      01-mockup.png
```

Ticket file = YAML frontmatter (pydantic-validated) + free markdown body.

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
<!-- frob:describes src/frob/tickets/clipboard.py::clipboard_image -->
<!-- frob:describes src/frob/tickets/clipboard.py::clipboard_has_image -->

```python
# frob/tickets/__init__.py
def load_queue(root: Path) -> Result[TicketQueue, TicketError]
    # Parses every tickets/*.md; any malformed file is a hard Err (the queue
    # is a contract surface, not best-effort data).
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

## Clipboard capture

`frob ticket new` and `frob ticket attach` offer clipboard paste only when
stdin is a TTY and `clipboard_has_image()` is true; non-interactive callers
(agents, CI) must pass explicit file paths -- prompts never block automation.

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

class ClipboardError(ErrorSet):
    NoBackend     = "No clipboard backend available on this platform"
    NoImage       = "Clipboard does not contain an image"
    BackendFailed = "Clipboard backend exited nonzero"

AttachError = TicketError | ClipboardError
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

## Dependencies

- `pydantic`, `typani`; stdlib `subprocess` (clipboard), `hashlib`, `date`.
- PyYAML (frontmatter) -- already transitively present; pinned direct.
- No dependency on `frob.graph` (gates join the two; see `docs/rework.md`).

## Integration points

- `frob.gates`: scope gate reads `scope`, coverage gate reads `evidence`
  and joins `frob:ticket`/`frob:todo` edge targets against the queue.
- CLI: `frob ticket new|list|show|doable|plan|start|sweep|attach|block|
  close|fail`. `start` auto-plans a queued ticket (both legal steps);
  `sweep` re-records the pre-work sweep after a scope change.
- Agents: planner emits ticket trees; implementer starts/closes tickets and
  writes done-reports; auditors file tickets with `origin: auditor`.
