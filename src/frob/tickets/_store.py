"""Ticket storage: a single-file `tickets.md` ledger (default) or the legacy
one-file-per-ticket `tickets/*.md` layout, behind one interface.

The queue is a contract surface (docs/modules/tickets.md): every read is strict
(Err on any malformation) and every write is atomic (temp file + os.replace
in the same directory, so a crash mid-write never corrupts what a
concurrent reader observes).

Two backends, auto-detected by `_store_mode`:

- **single** (default for new repos): all tickets live in one `tickets.md`
  at the repo root, each a section delimited by a `<!-- ticket:T-#### -->`
  marker followed by a fenced ```yaml frontmatter block and a free markdown
  body. This is the compact central log -- one file, greppable, no sprawl.
- **dir** (legacy / back-compat): `tickets/T-####-slug.md`, one file each.

The public `Ticket` / `TicketQueue` shapes are identical across both, so
frob.gates and the CLI never see the difference.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/tickets/_store.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
import tempfile
import threading
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path
from types import ModuleType

import yaml
from pydantic import ValidationError
from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.tickets._models import Ticket, TicketError

# T-0458: `fcntl` is posix-only; `ledger_lock` degrades to a documented
# no-op (see its docstring) on a platform without it, rather than failing
# import outright.
fcntl: ModuleType | None
try:
    fcntl = importlib.import_module("fcntl")
except ImportError:  # pragma: no cover -- posix-only in this repo's CI
    fcntl = None

_log = get_logger(__name__)

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?\n)---\n(.*)\Z", re.DOTALL)
_SLUG_RE = re.compile(r"[^a-z0-9]+")


# frob:ticket T-1206
# frob:tests tests/unit/test_ticket_store.py::TestYamlLoader.test_prefers_csafeloader_when_libyaml_present  # noqa: E501
# frob:tests tests/unit/test_ticket_store.py::TestYamlLoader.test_falls_back_to_safeloader_without_libyaml  # noqa: E501
def _yaml_loader() -> type[yaml.SafeLoader]:
    """The fastest safe YAML loader available: `yaml.CSafeLoader` (libyaml,
    a C extension) when installed, else the pure-Python `yaml.SafeLoader`.

    T-1206: every per-document `yaml.safe_load` call in this module
    profiled at 67 pct of `load_queue`'s cost on the 1235+-document
    `tickets-archive.md` ledger -- `yaml.safe_load` always uses the
    pure-Python `SafeLoader` even when `yaml.__with_libyaml__` reports the
    C extension is installed. Both loaders reject the exact same YAML
    constructs (CSafeLoader is a C reimplementation of the same safe
    subset, not a superset) -- so this swap is fail-open-preserving: a
    malformed frontmatter block that raised `yaml.YAMLError` before still
    raises the same error class through this loader."""
    if yaml.__with_libyaml__:
        return yaml.CSafeLoader
    return yaml.SafeLoader


# frob:ticket T-0162
# `_TICKET_ID_RE`'s alternation matches BOTH a final sequential id (T-####)
# and a provisional draft id (T-draft-<8 hex chars>, T-0162's collision-proof
# mechanism) -- every place an id appears in a filename/marker regex must
# accept both forms, or a draft ticket silently disappears the moment it
# round-trips through storage.
_TICKET_ID_RE = r"T-(?:\d{4}|draft-[0-9a-f]{8})"

# Single-file ledger: sections start at a `<!-- ticket:T-#### -->` marker
# (or `<!-- ticket:T-draft-<hex> -->` for a not-yet-finalized draft, T-0162).
_LEDGER_NAME = "tickets.md"
_LEDGER_MARKER_RE = re.compile(rf"(?m)^<!-- ticket:({_TICKET_ID_RE}) -->[ \t]*$")
_YAML_FENCE_RE = re.compile(r"\A\s*```ya?ml\n(.*?\n)```[ \t]*\n?(.*)\Z", re.DOTALL)
_LEDGER_HEADER = (
    "# Tickets\n\nCentral ledger managed by `frob ticket` -- one section per ticket.\n"
)

# Archive ledger: same format/marker/fence as the active ledger, rotated in
# by `frob ticket archive` (T-0096) so the active file stays a few hundred
# lines instead of growing forever with every done ticket.
_ARCHIVE_NAME = "tickets-archive.md"
_ARCHIVE_HEADER = (
    "# Tickets archive\n\nDone/dropped tickets moved here by `frob ticket archive` "
    "-- same format as tickets.md, still tracked and greppable.\n"
)

# frob:ticket T-0458
# The single-writer lock file: every ledger mutation (active OR archive) in
# this repo serializes through one lock, not two, so an `archive()` call
# (which touches both files) can never interleave with a concurrent
# `write_ticket` on the active ledger alone.
_LOCK_REL = Path(".frob") / "tickets.lock"

# frob:ticket T-0458
# Thread-local re-entrancy bookkeeping for `ledger_lock`: {lock_path_str:
# (fd, depth)}. `flock` is scoped to an open file DESCRIPTION, not a
# process, so a naive "always os.open + flock" implementation would
# self-deadlock the moment one call site (e.g. `new_ticket`) wraps a
# sequence that itself calls another lock-holding primitive (`write_ticket`)
# -- the second `os.open` gets a fresh description and blocks forever
# waiting on a lock the SAME thread already holds via the first
# description. Tracking depth per thread makes nested `with ledger_lock():`
# blocks in one thread a no-op re-entry instead of a deadlock, while a
# different thread (or process) still genuinely blocks on the real flock.
_lock_local = threading.local()


# frob:tests tests/unit/test_ticket_store.py::TestLockPath.test_lock_path_under_frob_dir
# frob:ticket T-0601
def _lock_path(root: Path) -> Path:
    """The advisory lock file path (`.frob/tickets.lock`) `ledger_lock` holds.

    Private (T-0601): no consumer outside this module and its own test --
    `_land.py` deliberately uses its own distinctly-named `_land_lock_path`
    rather than this one, so there is no cross-module public contract here."""
    return root / _LOCK_REL


# frob:doc docs/modules/tickets.md#storage-internals
# frob:tests tests/unit/test_ticket_store.py::TestLedgerLock.test_two_threads_serialize
# frob:ticket T-0601
@contextmanager
def ledger_lock(root: Path) -> Iterator[None]:
    """Exclusive, blocking, cross-process lock serializing EVERY ledger
    mutation under `root` (T-0458 single-writer invariant).

    Every write path that reads-then-writes the ledger (`write_ticket`,
    `write_all`, `write_archive`, and therefore every `frob.tickets`
    mutation built on them: `new_ticket`'s id allocation, `transition`,
    `add_evidence`, `set_done_report`, ...) acquires this BEFORE its own
    load step and holds it through the atomic write, so two concurrent
    callers -- same process or different agent processes -- can never
    observe-then-clobber each other's state. This is what makes an id
    allocation race (T-0465's duplicate T-0427) and a lost concurrent
    Done-report edit structurally impossible rather than merely unlikely.

    Uses `fcntl.flock` on `.frob/tickets.lock` (POSIX). On a platform
    without `fcntl` this degrades to a documented no-op (logged at WARNING,
    not silently pretended to be locked) -- a real Windows named-pipe/lock
    equivalent is the T-0458 phase-2 daemon-pipe follow-up, not built here.
    Re-entrant per thread (see `_lock_local`) so a locked primitive called
    from inside an already-locked caller in the SAME thread does not
    deadlock; a different thread or process still blocks on the real OS
    lock.
    """
    if fcntl is None:  # pragma: no cover -- posix-only in this repo's CI
        _log.warning(
            "tickets: ledger_lock: fcntl unavailable on this platform, "
            "lock is a NO-OP (T-0458 phase-2 tracks a real cross-platform "
            "primitive) -- concurrent writers are NOT serialized here"
        )
        yield
        return

    path = _lock_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    key = str(path)
    maybe_held: dict[str, tuple[int, int]] | None = getattr(_lock_local, "held", None)
    held: dict[str, tuple[int, int]] = maybe_held if maybe_held is not None else {}
    if maybe_held is None:
        _lock_local.held = held

    entry = held.get(key)
    if entry is not None:
        fd, depth = entry
        held[key] = (fd, depth + 1)
        try:
            yield
        finally:
            fd, depth = held[key]
            if depth <= 1:
                del held[key]
            else:
                held[key] = (fd, depth - 1)
        return

    fd = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o644)
    fcntl.flock(fd, fcntl.LOCK_EX)
    held[key] = (fd, 1)
    _log.debug("tickets: ledger_lock acquired (%s)", path)
    try:
        yield
    finally:
        del held[key]
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        _log.debug("tickets: ledger_lock released (%s)", path)


# frob:doc docs/modules/tickets.md#storage-internals
def slugify(title: str) -> str:
    """Lowercase, hyphenate, and strip non-alnum runs from a title for a filename."""
    slug = _SLUG_RE.sub("-", title.strip().lower()).strip("-")
    return slug or "untitled"


# frob:doc docs/modules/tickets.md#storage-internals
def tickets_dir(root: Path) -> Path:
    """The legacy tickets/ directory (also holds attachments in single mode)."""
    return root / "tickets"


# frob:doc docs/modules/tickets.md#storage-internals
def ledger_path(root: Path) -> Path:
    """The single-file `tickets.md` ledger path at the repo root."""
    return root / _LEDGER_NAME


# frob:doc docs/modules/tickets.md#storage-internals
def archive_path(root: Path) -> Path:
    """The `tickets-archive.md` path at the repo root (same ledger format)."""
    return root / _ARCHIVE_NAME


# frob:doc docs/modules/tickets.md#storage-internals
def attachments_dir(root: Path, ticket_id: str) -> Path:
    """The tickets/attachments/<id>/ directory for a given ticket (both modes)."""
    return tickets_dir(root) / "attachments" / ticket_id


def _dir_glob(root: Path) -> list[Path]:
    """Every legacy ticket markdown file directly under tickets/, sorted."""
    d = tickets_dir(root)
    if not d.exists():
        return []
    return sorted(p for p in d.glob("T-*.md") if p.is_file())


# frob:doc docs/modules/tickets.md#storage-internals
# frob:waive COV007 reason="docs/modules/tickets.md's Storage internals section \
# individually frob:describes this private helper by name (T-0529) -- a deliberate \
# architecture doc, not accidental drift onto a private helper"
def _store_mode(root: Path) -> str:
    """Which backend a repo uses: 'single' if tickets.md exists, 'dir' if only
    the legacy tickets/*.md files exist, else 'single' (the default for a
    fresh repo -- new ledgers are compact, not sprawling)."""
    if ledger_path(root).exists():
        return "single"
    if _dir_glob(root):
        return "dir"
    return "single"


# ---------------------------------------------------------------------------
# Serialization (shared)
# ---------------------------------------------------------------------------


def _frontmatter_yaml(ticket: Ticket) -> str:
    """The ticket's scalar/list fields as YAML (body excluded)."""
    payload = ticket.model_dump(mode="json", exclude={"body"})
    return yaml.safe_dump(payload, sort_keys=False, default_flow_style=False)


# frob:doc docs/modules/tickets.md#storage-internals
# frob:waive COV007 reason="docs/modules/tickets.md's Storage internals section \
# individually frob:describes this private helper by name (T-0529) -- a deliberate \
# architecture doc, not accidental drift onto a private helper"
def _serialize_ticket(ticket: Ticket) -> str:
    """Render a Ticket to legacy `---`-frontmatter + body (dir-mode file text)."""
    return f"---\n{_frontmatter_yaml(ticket)}---\n{ticket.body}"


def _validate(data: dict, body: str, where: str) -> Result[Ticket, TicketError]:
    """Validate a frontmatter mapping + body into a Ticket, or a hard Err."""
    if not isinstance(data, dict):
        _log.error("tickets: %s frontmatter did not parse to a mapping", where)
        return Err(TicketError.MalformedFrontmatter)
    data = {**data, "body": body}
    try:
        return Ok(Ticket.model_validate(data))
    except ValidationError as exc:
        _log.error("tickets: %s failed schema validation: %s", where, exc)
        return Err(TicketError.MalformedFrontmatter)


# ---------------------------------------------------------------------------
# dir backend
# ---------------------------------------------------------------------------


# frob:doc docs/modules/tickets.md#storage-internals
# frob:waive COV007 reason="docs/modules/tickets.md's Storage internals section \
# individually frob:describes this private helper by name (T-0529) -- a deliberate \
# architecture doc, not accidental drift onto a private helper"
def _parse_ticket_file(path: Path) -> Result[Ticket, TicketError]:
    """Split a legacy ticket file into frontmatter + body and validate it."""
    text = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        _log.error("tickets: %s has no valid frontmatter block", path)
        return Err(TicketError.MalformedFrontmatter)
    try:
        data = yaml.load(match.group(1), Loader=_yaml_loader())
    except yaml.YAMLError as exc:
        _log.error("tickets: %s frontmatter is not valid YAML: %s", path, exc)
        return Err(TicketError.MalformedFrontmatter)
    return _validate(data, match.group(2), str(path))


def _dir_path_for(root: Path, ticket: Ticket) -> Path:
    """The tickets/T-####-slug.md path a ticket serializes to."""
    return tickets_dir(root) / f"{ticket.id}-{slugify(ticket.title)}.md"


# ---------------------------------------------------------------------------
# single-file ledger backend
# ---------------------------------------------------------------------------


# frob:ticket T-1132
# frob:doc docs/modules/tickets.md#storage-internals
# frob:tests tests/test_tickets.py::TestIterRawLedgerFrontmatter.test_returns_raw_dict_per_ticket kind="unit"  # noqa: E501
# frob:tests tests/test_tickets.py::TestIterRawLedgerFrontmatter.test_skips_malformed_yaml_block_without_raising kind="unit"  # noqa: E501
def iter_raw_ledger_frontmatter(text: str) -> list[tuple[str, dict]]:
    """Every `<!-- ticket:ID -->` section's RAW (unvalidated) frontmatter
    dict, tolerating a malformed YAML block by skipping just that one
    section (logged) rather than failing the whole scan -- unlike
    `_parse_ledger`, which is strict end to end (any single malformed
    section fails the entire load, matching how the shared ledger's other
    consumers need an all-or-nothing view).

    T-1132: this is the read-side complement `frob doctor`'s malformed-
    edge scan needs -- `Ticket.model_validate` deliberately does NOT
    reject a malformed `blocked_by`/`parent` entry (see `Ticket`'s
    docstring note in `frob.tickets._models`), so a strict loader like
    `_parse_ledger`/`load_all` cannot be doctor's data source for finding
    one: a single bad edge anywhere in the ~1000+-ticket shared ledger
    would otherwise make EVERY `frob` command relying on `load_all` refuse
    outright the moment it existed. Reading raw dicts here means doctor
    can find and report a malformed edge without the rest of the toolchain
    ever being at risk of the same hard failure."""
    out: list[tuple[str, dict]] = []
    markers = list(_LEDGER_MARKER_RE.finditer(text))
    for i, marker in enumerate(markers):
        ticket_id = marker.group(1)
        chunk_end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        chunk = text[marker.end() : chunk_end]
        fence = _YAML_FENCE_RE.match(chunk.lstrip("\n"))
        if fence is None:
            _log.warning(
                "tickets: %s section has no ```yaml frontmatter, skipping in raw scan",
                ticket_id,
            )
            continue
        try:
            data = yaml.load(fence.group(1), Loader=_yaml_loader())
        except yaml.YAMLError as exc:
            _log.warning(
                "tickets: %s frontmatter is not valid YAML, skipping in raw scan: %s",
                ticket_id,
                exc,
            )
            continue
        if isinstance(data, dict):
            out.append((ticket_id, data))
    return out


def _parse_ledger(text: str) -> Result[dict[str, Ticket], TicketError]:
    """Parse a `tickets.md` ledger into an id -> Ticket map (strict)."""
    tickets: dict[str, Ticket] = {}
    markers = list(_LEDGER_MARKER_RE.finditer(text))
    for i, marker in enumerate(markers):
        ticket_id = marker.group(1)
        chunk_end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        chunk = text[marker.end() : chunk_end]
        fence = _YAML_FENCE_RE.match(chunk.lstrip("\n"))
        if fence is None:
            _log.error("tickets: %s section has no ```yaml frontmatter", ticket_id)
            return Err(TicketError.MalformedFrontmatter)
        try:
            data = yaml.load(fence.group(1), Loader=_yaml_loader())
        except yaml.YAMLError as exc:
            _log.error("tickets: %s frontmatter is not valid YAML: %s", ticket_id, exc)
            return Err(TicketError.MalformedFrontmatter)
        parsed = _validate(data, fence.group(2).strip("\n"), ticket_id)
        if parsed.is_err:
            return Err(parsed.danger_err)
        ticket = parsed.danger_ok
        if ticket.id != ticket_id:
            _log.error("tickets: marker %s wraps ticket %s", ticket_id, ticket.id)
            return Err(TicketError.MalformedFrontmatter)
        if ticket.id in tickets:
            _log.error("tickets: duplicate id %s in ledger", ticket.id)
            return Err(TicketError.DuplicateId)
        tickets[ticket.id] = ticket
    return Ok(tickets)


def _render_section(ticket_id: str, ticket: Ticket) -> str:
    """One ledger section's text, LEADING blank-line included (`\\n<!--
    ticket:... -->...`) -- the single home for the marker+yaml+body layout,
    shared by `_render_ledger` (whole-file) and `_splice_ticket_section`
    (single-block, T-0505) so the two paths can never format a section
    differently."""
    body = ticket.body.strip("\n")
    section = (
        f"\n<!-- ticket:{ticket_id} -->\n```yaml\n{_frontmatter_yaml(ticket)}```\n"
    )
    if body:
        section += f"{body}\n"
    return section


def _render_ledger(tickets: dict[str, Ticket], header: str = _LEDGER_HEADER) -> str:
    """Render an id -> Ticket map to ledger text, ordered by id (same section
    format for both the active ledger and the archive -- only the header
    text differs)."""
    parts = [header]
    ordered_ids = sorted(tickets)
    for ticket_id in ordered_ids:
        parts.append(_render_section(ticket_id, tickets[ticket_id]))
    return "".join(parts)


# frob:ticket T-0764
# frob:tests \
# tests/test_ticket_land.py::TestSpliceLedgerIdDropGuard.test_render_that_would_drop_an\
# _id_is_refused kind="unit"  # noqa: E501
# frob:ticket T-0601
def _check_ledger_id_integrity(
    tickets: dict[str, Ticket], rendered: str
) -> Result[None, TicketError]:
    """Structural guard against the T-0367 incident class: re-parse
    `rendered` and refuse loudly (`Err(LedgerIntegrityViolation)`) unless
    every id in `tickets` round-trips back out with its marker intact.

    A ledger section with no `<!-- ticket:... -->` marker line silently
    reads as trailing BODY TEXT of the PRECEDING ticket, not as its own
    ticket -- `_parse_ledger` has no way to notice this on its own, since
    from its perspective the id simply never existed in the file. The
    T-0367 field incident lost an entire in-progress block this way with
    no error anywhere in the chain. Calling this immediately before ANY
    wholesale ledger commit (`write_all`, `write_archive`) turns that
    silent loss into a hard `Err` at the one point it is still cheap to
    catch: right after rendering, before the bytes ever hit disk."""
    reparsed = _parse_ledger(rendered)
    if reparsed.is_err:
        _log.error(
            "tickets: ledger write refused -- rendered text fails to re-parse (%s)",
            reparsed.danger_err,
        )
        return Err(TicketError.LedgerIntegrityViolation)
    missing = set(tickets) - set(reparsed.danger_ok)
    if missing:
        _log.error(
            "tickets: ledger write refused -- rendering dropped id(s) %s "
            "(markerless-block class, T-0764)",
            sorted(missing),
        )
        return Err(TicketError.LedgerIntegrityViolation)
    return Ok(None)


# frob:ticket T-0505
def _splice_ticket_section(text: str, ticket: Ticket) -> str:
    """Rewrite ONLY `ticket.id`'s own marker block within `text`, leaving
    every other byte of `text` untouched.

    T-0505: `write_ticket`'s old single-ticket path read the WHOLE ledger,
    upserted one id into the in-memory map, and re-rendered EVERY section
    from scratch (`_render_ledger`) -- so a write that only ever touched one
    ticket produced a diff spanning the entire file, byte-for-byte
    reproducing whatever every OTHER ticket's section happened to look like
    in THIS worktree's on-disk copy at read time. On a branch whose local
    tickets.md predates a sibling ticket's later state on `main` (a finalize,
    a close, a requeue), that "byte-for-byte reproduction" is actually a
    silent revert the moment this write lands -- the command never touched
    that sibling id, but its bytes moved anyway. Splicing only the target
    section (the same single-writer principle as `_land._splice_only_ticket`,
    T-0479) makes every other ticket's bytes provably absent from the diff,
    so a sibling's state can never travel through a write it was never part
    of.

    If `ticket.id` already has a marker in `text`, only that marker's span
    (start of its marker line through the next marker's start, or EOF) is
    replaced. Otherwise the ticket is new to this file and its section is
    appended at the end, matching `_render_ledger`'s section format
    (leading blank line included)."""
    markers = list(_LEDGER_MARKER_RE.finditer(text))
    for i, marker in enumerate(markers):
        if marker.group(1) != ticket.id:
            continue
        start = marker.start()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
        replacement = _render_section(ticket.id, ticket).lstrip("\n")
        return text[:start] + replacement + text[end:]
    return text + _render_section(ticket.id, ticket)


# ---------------------------------------------------------------------------
# unified interface
# ---------------------------------------------------------------------------


# frob:ticket T-0889
_MISSING_LEDGER_DIGEST = ""


# frob:ticket T-0889
# frob:doc docs/modules/tickets.md#storage-internals
# frob:tests \
# tests/test_ticket_store_stale_snapshot.py::TestLedgerDigest.test_digest_stable_for_un\
# changed_content  # noqa: E501
def ledger_digest(path: Path) -> str:
    """Sha256 hex digest of `path`'s current raw bytes, or `""`
    (`_MISSING_LEDGER_DIGEST`) if it does not exist yet -- the on-disk
    fingerprint `write_all`/`write_archive` compare an `expected_digest`
    against (T-0889) to detect that the ledger changed since a caller's
    earlier `load_all`/`load_archive` snapshot, rather than silently
    overwriting whatever changed with that stale in-memory map.

    Deliberately returns the empty string rather than `None` for a missing
    file: `write_all`/`write_archive` use `expected_digest=None` to mean
    "caller opted out of the check entirely" (the pre-T-0889 default,
    preserved for callers not yet updated) -- collapsing "file did not
    exist at load time" into that same `None` would make a load-time-
    missing-file race indistinguishable from no check at all, silently
    reopening the exact hazard this exists to close. Callers capture this
    via the same path helper (`ledger_path`/`archive_path`) they load
    through, immediately after (or immediately before) the load it is
    meant to pin."""
    if not path.exists():
        return _MISSING_LEDGER_DIGEST
    return hashlib.sha256(path.read_bytes()).hexdigest()


# frob:doc docs/modules/tickets.md#storage-internals
def load_all(root: Path) -> Result[dict[str, Ticket], TicketError]:
    """Every ticket in the repo as an id -> Ticket map, backend-agnostic."""
    if _store_mode(root) == "single":
        ledger = ledger_path(root)
        if not ledger.exists():
            return Ok({})
        return _parse_ledger(ledger.read_text(encoding="utf-8"))
    tickets: dict[str, Ticket] = {}
    for path in _dir_glob(root):
        parsed = _parse_ticket_file(path)
        if parsed.is_err:
            _log.error("tickets: load aborted, %s is malformed", path)
            return Err(parsed.danger_err)
        ticket = parsed.danger_ok
        if ticket.id in tickets:
            _log.error("tickets: duplicate id %s (%s)", ticket.id, path)
            return Err(TicketError.DuplicateId)
        tickets[ticket.id] = ticket
    return Ok(tickets)


# frob:ticket T-1206
# The parsed-archive cache file: keyed by the archive's own content hash
# (never mtime, T-1206 -- an mtime-only key survives a touch/checkout that
# does not change bytes, but silently misses a same-second edit and is
# unreliable across filesystems/git checkouts that do not preserve mtimes)
# so a stale cache can never be read as fresh.
_ARCHIVE_CACHE_REL = Path(".frob") / "tickets-archive-cache.json"


def _archive_cache_path(root: Path) -> Path:
    """The cache file `load_archive` reads/writes (`.frob/tickets-archive-
    cache.json`), gitignored and safe to delete like the rest of `.frob/`."""
    return root / _ARCHIVE_CACHE_REL


# frob:ticket T-1206
# frob:tests tests/unit/test_ticket_store.py::TestLoadArchiveCache.test_reparses_when_archive_content_changes  # noqa: E501
# frob:tests tests/unit/test_ticket_store.py::TestLoadArchiveCache.test_skips_reparse_when_content_hash_unchanged  # noqa: E501
def _read_archive_cache(
    cache_path: Path, digest: str
) -> Result[dict[str, Ticket], TicketError] | None:
    """The cached parse of `tickets-archive.md` if `cache_path` exists AND
    its recorded digest matches `digest` exactly (content-hash keyed, never
    mtime -- T-1206), else `None` meaning "caller must parse fresh".

    A cache hit that fails to deserialize (corrupt/foreign-format file, a
    schema change across a `frob` upgrade) is treated the SAME as a miss --
    logged and ignored -- rather than propagated as an error, since this
    cache is purely a speed optimization derived from the archive file
    itself, never a source of truth in its own right."""
    if not cache_path.exists():
        return None
    try:
        raw = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _log.warning("tickets: archive cache unreadable, reparsing (%s)", exc)
        return None
    if not isinstance(raw, dict) or raw.get("digest") != digest:
        return None
    try:
        tickets = {
            ticket_id: Ticket.model_validate(data)
            for ticket_id, data in raw.get("tickets", {}).items()
        }
    except ValidationError as exc:
        _log.warning(
            "tickets: archive cache failed to deserialize, reparsing (%s)", exc
        )
        return None
    _log.debug("tickets: archive cache hit (digest %s)", digest)
    return Ok(tickets)


def _write_archive_cache(
    cache_path: Path, digest: str, tickets: dict[str, Ticket]
) -> None:
    """Best-effort write of the parsed archive to `cache_path`, keyed by
    `digest`. Never raises: a failed cache write only costs the NEXT
    load's speedup, not correctness, so it is logged and swallowed rather
    than surfaced as a `load_archive` error."""
    payload = {
        "digest": digest,
        "tickets": {
            ticket_id: ticket.model_dump(mode="json")
            for ticket_id, ticket in tickets.items()
        },
    }
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(cache_path.parent), prefix=".tickets-archive-cache-"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
            os.replace(tmp_name, cache_path)
        except BaseException:
            with suppress(OSError):
                os.unlink(tmp_name)
            raise
    except OSError as exc:
        _log.warning("tickets: failed to write archive cache, skipping (%s)", exc)


# frob:doc docs/modules/tickets.md#storage-internals
# frob:ticket T-1206
def load_archive(root: Path) -> Result[dict[str, Ticket], TicketError]:
    """Every ticket in `tickets-archive.md` as an id -> Ticket map (empty if
    the archive does not exist yet -- a fresh repo has never archived
    anything).

    T-1206: the archive is append-mostly and can grow into the thousands
    of documents, so re-running `_parse_ledger` (1235+ `yaml.load` calls at
    the time this was measured) on every `frob ticket doable`/`list`/`check`
    invocation dominates queue-loading cost even after the CSafeLoader
    swap. This caches the parsed result under `.frob/tickets-archive-
    cache.json`, keyed by the archive file's own sha256 content hash
    (`ledger_digest`, never mtime -- an mtime-based key would treat a
    content-identical `git checkout` or same-second edit as either a false
    hit or a false miss) -- an unchanged archive is never reparsed, and any
    byte change invalidates the cache on the very next read."""
    path = archive_path(root)
    if not path.exists():
        return Ok({})
    digest = ledger_digest(path)
    cache_path = _archive_cache_path(root)
    cached = _read_archive_cache(cache_path, digest)
    if cached is not None:
        return cached
    parsed = _parse_ledger(path.read_text(encoding="utf-8"))
    if parsed.is_ok:
        _write_archive_cache(cache_path, digest, parsed.danger_ok)
    return parsed


# frob:doc docs/modules/tickets.md#storage-internals
# frob:ticket T-0458
# frob:ticket T-0601
# frob:ticket T-0889
def write_archive(
    root: Path,
    tickets: dict[str, Ticket],
    *,
    expected_digest: str | None = None,
) -> Result[None, TicketError]:
    """Replace `tickets-archive.md` wholesale with `tickets` (same ledger
    section format as the active file, distinct header); serialized against
    every other ledger mutation via `ledger_lock` (T-0458).

    T-0889: when `expected_digest` is given (the caller's `ledger_digest`
    snapshot from the `load_archive` this wholesale map was computed from),
    the on-disk archive is re-fingerprinted under the SAME lock right before
    writing; a mismatch means something else wrote the archive since that
    load and this call refuses (`Err(LedgerChangedSinceLoad)`) rather than
    clobbering it with a stale in-memory map. `None` (the default) preserves
    the pre-T-0889 unconditional-overwrite behavior for callers that have
    not been updated to pass a digest."""
    with ledger_lock(root):
        path = archive_path(root)
        if expected_digest is not None:
            current = ledger_digest(path)
            if current != expected_digest:
                _log.error(
                    "tickets: write_archive refused -- %s changed on disk "
                    "since this caller's load (expected digest %s, found %s)",
                    path,
                    expected_digest,
                    current,
                )
                return Err(TicketError.LedgerChangedSinceLoad)
        text = _render_ledger(tickets, _ARCHIVE_HEADER)
        integrity = _check_ledger_id_integrity(tickets, text)
        if integrity.is_err:
            return Err(integrity.danger_err)
        return atomic_write(path, text)


# frob:doc docs/modules/tickets.md#storage-internals
# frob:ticket T-0458
def write_ticket(root: Path, ticket: Ticket) -> Result[None, TicketError]:
    """Upsert one ticket into whichever backend the repo uses (atomic).

    Single mode reads the raw ledger TEXT, still Err-propagates if the file
    as a whole fails to parse (`_parse_ledger`, unchanged malformed-ledger
    behavior), then splices in ONLY `ticket`'s own marker block
    (`_splice_ticket_section`, T-0505) using that raw text -- every other
    ticket's bytes pass through completely untouched, never round-tripped
    through parse-then-`_render_ledger`. Before T-0505 this reparsed the
    WHOLE ledger into a dict and re-rendered every section from scratch, so
    a write that only ever touched one ticket produced a diff spanning the
    entire file: on a branch whose on-disk tickets.md predated a sibling
    ticket's later state on `main`, that "diff spanning the entire file"
    silently carried the sibling's stale state along for the ride the
    moment this write landed, even though the command never touched that
    id. The read-modify-write is still held under `ledger_lock` end to end
    (T-0458) so a concurrent writer can never read the pre-write state and
    clobber this write (or vice versa). Dir mode has no read step (one file
    per ticket) but still locks, so it serializes correctly against a
    concurrent `write_all`/`archive` touching the same store.
    """
    with ledger_lock(root):
        if _store_mode(root) == "single":
            path = ledger_path(root)
            if not path.exists():
                fresh = _splice_ticket_section(_LEDGER_HEADER, ticket)
                return atomic_write(path, fresh)
            text = path.read_text(encoding="utf-8")
            parsed = _parse_ledger(text)
            if parsed.is_err:
                return Err(parsed.danger_err)
            return atomic_write(path, _splice_ticket_section(text, ticket))
        return atomic_write(_dir_path_for(root, ticket), _serialize_ticket(ticket))


# frob:doc docs/modules/tickets.md#storage-internals
# frob:ticket T-0458
# frob:ticket T-0601
# frob:ticket T-0889
def write_all(
    root: Path,
    tickets: dict[str, Ticket],
    *,
    expected_digest: str | None = None,
) -> Result[None, TicketError]:
    """Replace the ENTIRE store with `tickets` (used by archive/renumber).
    Single mode rewrites the ledger wholesale; dir mode writes each file and
    removes any T-*.md whose id is no longer present. Held under
    `ledger_lock` (T-0458) so a wholesale replace can never interleave with
    a concurrent single-ticket `write_ticket`.

    T-0889: when `expected_digest` is given (the caller's `ledger_digest`
    snapshot from the `load_all` this wholesale `tickets` map was computed
    from), the on-disk ledger is re-fingerprinted under the SAME lock right
    before writing; a mismatch means the ledger changed since that load --
    another writer's splice, or an external replacement (e.g. `git checkout
    main -- tickets.md`) -- and this call refuses
    (`Err(LedgerChangedSinceLoad)`) instead of silently overwriting whatever
    changed with the caller's now-stale in-memory map (the T-0680 field
    incident: three unrelated done tickets reverted to queued this way).
    `None` (the default) preserves the pre-T-0889 unconditional-overwrite
    behavior for callers that have not been updated to pass a digest --
    single-mode only, since dir mode has no single ledger file to
    fingerprint."""
    with ledger_lock(root):
        if _store_mode(root) == "single":
            path = ledger_path(root)
            if expected_digest is not None:
                current = ledger_digest(path)
                if current != expected_digest:
                    _log.error(
                        "tickets: write_all refused -- %s changed on disk "
                        "since this caller's load (expected digest %s, "
                        "found %s)",
                        path,
                        expected_digest,
                        current,
                    )
                    return Err(TicketError.LedgerChangedSinceLoad)
            text = _render_ledger(tickets)
            integrity = _check_ledger_id_integrity(tickets, text)
            if integrity.is_err:
                return Err(integrity.danger_err)
            return atomic_write(path, text)
        keep_files: set[Path] = set()
        for ticket in tickets.values():
            path = _dir_path_for(root, ticket)
            result = atomic_write(path, _serialize_ticket(ticket))
            if result.is_err:
                return Err(result.danger_err)
            keep_files.add(path)
        _prune_stale_files(root, keep_files)
        return Ok(None)


def _prune_stale_files(root: Path, keep_files: set[Path]) -> None:
    """Delete any dir-mode ticket file whose path is not in `keep_files`."""
    for path in _dir_glob(root):
        if path not in keep_files:
            path.unlink(missing_ok=True)


# frob:doc docs/modules/tickets.md#storage-internals
def migrate_to_ledger(root: Path) -> Result[int, TicketError]:
    """Collapse a legacy tickets/*.md layout into a single tickets.md ledger.

    Reads every dir-mode ticket, writes the ledger, then deletes the source
    files. Attachments under tickets/attachments/ are left untouched (both
    modes share that location). Returns the number of tickets migrated.
    """
    files = _dir_glob(root)
    if not files:
        return Ok(0)
    tickets: dict[str, Ticket] = {}
    for path in files:
        parsed = _parse_ticket_file(path)
        if parsed.is_err:
            return Err(parsed.danger_err)
        tickets[parsed.danger_ok.id] = parsed.danger_ok
    written = atomic_write(ledger_path(root), _render_ledger(tickets))
    if written.is_err:
        return Err(written.danger_err)
    for path in files:
        try:
            path.unlink()
        except OSError as exc:
            _log.warning("tickets: could not remove migrated %s: %s", path, exc)
    _log.info("tickets: migrated %d ticket(s) into %s", len(tickets), ledger_path(root))
    return Ok(len(tickets))


# frob:doc docs/modules/tickets.md#storage-internals
# frob:tests \
# tests/unit/test_ticket_store.py::TestAtomicWrite.test_fsyncs_file_before_replace  # \
# noqa: E501
# frob:tests \
# tests/unit/test_ticket_store.py::TestAtomicWrite.test_fsync_failure_is_write_failed_n\
# ot_a_partial_file  # noqa: E501
# frob:waive ARCH103 reason="T-0977: crash-safe write primitive -- temp file + fsync + \
# os.replace with a str/bytes branch for the write call itself; the encoding branch is \
# the SAME single 'write content safely' concern the docstring names (T-0456), not a \
# separate one to extract"
def atomic_write(path: Path, content: str | bytes) -> Result[None, TicketError]:
    """Write content via temp file + fsync + os.replace in the same directory
    (T-0456: crash-safe -- `os.replace` alone is atomic AT THE FILESYSTEM
    level, but without an `fsync` first, a power loss between the write and
    the rename can leave the temp file's data unflushed to disk, so a
    subsequent replay of the rename journal entry (on filesystems that log
    renames separately from data blocks) can surface a zero-length or
    truncated file. `fsync`ing the temp file's own fd before `os.replace`
    guarantees the data is durable before the rename that makes it visible
    under `path`, so `tickets.md`/`.frob-release.json`/lease and journal
    files are never left partially written after an interrupt.)"""
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "wb" if isinstance(content, bytes) else "w"
    encoding = None if isinstance(content, bytes) else "utf-8"
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, mode, encoding=encoding) as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except OSError as exc:
        _log.error("tickets: atomic write to %s failed: %s", path, exc)
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        return Err(TicketError.WriteFailed)
    _log.debug("tickets: wrote %s", path)
    return Ok(None)
