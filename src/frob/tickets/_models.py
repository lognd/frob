"""Data models and error types for frob.tickets
(docs/modules/tickets.md is authoritative)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.error_set import ErrorSet


# frob:doc docs/modules/tickets.md#data-models
class TicketState(StrEnum):
    """The six states a ticket can occupy in the queue state machine."""

    QUEUED = "queued"
    PLANNED = "planned"
    IN_PROGRESS = "in-progress"
    BLOCKED = "blocked"
    DONE = "done"
    DROPPED = "dropped"


# frob:doc docs/modules/tickets.md#data-models
class TicketKind(StrEnum):
    """What kind of work a ticket represents."""

    FEATURE = "feature"
    BUG = "bug"
    SECURITY = "security"
    UX = "ux"
    DOCS = "docs"
    INVARIANT = "invariant"
    INCIDENT = "incident"


# frob:doc docs/modules/tickets.md#data-models
class Stride(StrEnum):
    """STRIDE threat categories for kind=security tickets (T-0007)."""

    SPOOFING = "spoofing"
    TAMPERING = "tampering"
    REPUDIATION = "repudiation"
    INFO_DISCLOSURE = "info-disclosure"
    DENIAL_OF_SERVICE = "denial-of-service"
    ELEVATION_OF_PRIVILEGE = "elevation-of-privilege"


# frob:doc docs/modules/tickets.md#data-models
class Origin(StrEnum):
    """Who filed a ticket."""

    HUMAN = "human"
    AGENT = "agent"
    AUDITOR = "auditor"


# frob:doc docs/modules/tickets.md#data-models
class Attachment(BaseModel):
    """One image/file attached to a ticket, with integrity hash."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: str
    caption: str
    sha256: str


# frob:doc docs/modules/tickets.md#data-models
class FailureEntry(BaseModel):
    """One line of append-only cross-session failure memory for a ticket."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    date: date
    attempt: int
    summary: str


# frob:doc docs/modules/tickets.md#data-models
class Ticket(BaseModel):
    """One ticket: frontmatter fields plus the verbatim markdown body."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    title: str
    state: TicketState
    kind: TicketKind
    origin: Origin
    created: date
    blocked_by: tuple[str, ...] = ()
    parent: str | None = None
    scope: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    attachments: tuple[Attachment, ...] = ()
    # given/when/then acceptance criteria the reviewer verifies (T-0006)
    acceptance: tuple[str, ...] = ()
    # STRIDE category for kind=security tickets (T-0007)
    threat: Stride | None = None
    body: str = ""


# frob:doc docs/modules/tickets.md#data-models
class TicketSpec(BaseModel):
    """Input to new_ticket; id/created/state are assigned by the library."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str
    kind: TicketKind
    origin: Origin
    scope: tuple[str, ...] = ()
    blocked_by: tuple[str, ...] = ()
    parent: str | None = None
    acceptance: tuple[str, ...] = ()
    threat: Stride | None = None
    evidence: tuple[str, ...] = ()
    body: str = ""


# frob:doc docs/modules/tickets.md#data-models
# frob:ticket T-0162
class RenumberReport(BaseModel):
    """Outcome of `renumber_one`/`finalize_draft`: what changed (or would
    change, under `--dry-run`) rewriting one ticket id everywhere."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    old_id: str
    new_id: str
    ledger_changed: bool
    files_changed: tuple[str, ...]
    occurrences: int
    dry_run: bool


# frob:doc docs/modules/tickets.md#data-models
class TicketQueue(BaseModel):
    """The full set of tickets loaded from tickets/, keyed by id."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tickets: Mapping[str, Ticket]


# frob:doc docs/modules/tickets.md#data-models
class AttachmentSource(BaseModel):
    """Where attach() should read image bytes from; None path means clipboard."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    path: Path | None = None


# frob:doc docs/modules/tickets.md#error-types
class TicketError(ErrorSet):
    """Fallible outcomes of frob.tickets queue/mutation operations."""

    NotFound = "No ticket with that id"
    DuplicateId = "Ticket id already exists"
    MalformedFrontmatter = "Ticket file failed schema validation"
    InvalidTransition = "State change not allowed by the state machine"
    MissingEvidence = "done requires evidence and a Done report"
    MalformedEvidence = "evidence entry failed schema validation"
    BlockerOpen = "Cannot start: blocked_by contains open tickets"
    WriteFailed = "Atomic ticket write failed"
    UnknownEvidence = "Evidence id does not resolve to a collected test"


# frob:ticket T-0176
# frob:doc docs/modules/tickets.md#frob-ticket-land
class LandError(ErrorSet):
    """Fallible outcomes of `frob.tickets.land` (`frob ticket land`); every
    variant corresponds to an abort path that names its own manual remedy
    in the log line raised alongside it (T-0176)."""

    DirtyMain = "root checkout has uncommitted changes"
    NotFound = "ticket not found in the worktree's store"
    NotCloseable = "ticket is missing evidence or a Done report"
    GitFailed = "a required git operation failed"
    MergeConflict = "merging main into the worktree produced real conflicts"
    UnownedDeletions = "worktree deletes files outside the ticket's scope"
    CloseFailed = "closing the ticket after merge failed"
    SquashConflict = "squash-applying the worktree onto main produced real conflicts"
    CommitFailed = "the final landing commit failed"


# frob:ticket T-0176
# frob:doc docs/modules/tickets.md#frob-ticket-land
class LandReport(BaseModel):
    """Outcome of one `land()` call: what happened (or, under `dry_run`,
    what WOULD happen) landing `ticket_id` from a worktree onto main."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ticket_id: str
    final_id: str
    dry_run: bool
    wip_committed: bool
    merged_main_into_worktree: bool
    ledger_spliced: bool
    unowned_deletions: tuple[str, ...] = ()
    commit_sha: str | None = None
    files_changed: tuple[str, ...] = ()
