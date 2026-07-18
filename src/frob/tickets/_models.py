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
    body: str = ""


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
    BlockerOpen = "Cannot start: blocked_by contains open tickets"
    WriteFailed = "Atomic ticket write failed"
    UnknownEvidence = "Evidence id does not resolve to a collected test"
