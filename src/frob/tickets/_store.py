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
import shutil
import sys
import tempfile
import threading
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path
from types import ModuleType

import yaml
from pydantic import ValidationError
from typani.result import Err, Ok, Result

from frob.gitio import run_argv
from frob.logging import get_logger
from frob.tickets._models import (
    Ticket,
    TicketError,
    _done_report_section_end,
    _find_done_report_heading,
    replace_done_report_section,
)

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


# frob:ticket T-1333
# frob:tests tests/unit/test_ticket_store.py::TestYamlLoader.test_detects_coverage_tracer_by_module_name  # noqa: E501
# frob:tests tests/unit/test_ticket_store.py::TestYamlLoader.test_no_active_tracer_is_not_coverage  # noqa: E501
def _coverage_tracer_active() -> bool:
    """True when `sys.gettrace()` is installed by `coverage.py` (or a
    subclass of its tracer), so callers can avoid a known-bad interaction
    between that tracer and `yaml.CSafeLoader` (T-1333: the CSafeLoader/
    libyaml C extension corrupts frontmatter parses -- 'could not
    determine a constructor for the tag None' on otherwise-valid YAML --
    specifically when a `coverage.py` trace function is active; both
    bare `coverage run` and `pytest-cov` install their tracer this same
    way, and the pure-Python `SafeLoader` is unaffected). Detection is by
    the active tracer callable's module name rather than an env var,
    since that is the actual mechanism responsible for the corruption and
    stays accurate under any invocation style (`coverage run`, pytest-cov,
    a hand-rolled `sys.settrace`-based coverage tool)."""
    tracer = sys.gettrace()
    if tracer is None:
        return False
    module = getattr(tracer, "__module__", None) or getattr(
        type(tracer), "__module__", ""
    )
    return module.startswith("coverage")


# frob:ticket T-1206
# frob:ticket T-1333
# frob:tests tests/unit/test_ticket_store.py::TestYamlLoader.test_prefers_csafeloader_when_libyaml_present  # noqa: E501
# frob:tests tests/unit/test_ticket_store.py::TestYamlLoader.test_falls_back_to_safeloader_without_libyaml  # noqa: E501
# frob:tests tests/unit/test_ticket_store.py::TestYamlLoader.test_falls_back_to_safeloader_under_active_coverage_tracer  # noqa: E501
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
    raises the same error class through this loader.

    T-1333: `CSafeLoader` has a known-bad interaction with an active
    `coverage.py` trace function (see `_coverage_tracer_active`'s
    docstring) that corrupts otherwise-valid frontmatter parses. When a
    coverage tracer is detected active, this falls back to the
    pure-Python `SafeLoader` regardless of `__with_libyaml__`, trading the
    T-1206 speed win for correctness for the duration of that run --
    `SafeLoader` accepts the exact same YAML subset, so this never changes
    what parses, only how fast."""
    if yaml.__with_libyaml__ and not _coverage_tracer_active():
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


# frob:ticket T-1536
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/unit/test_ticket_store.py::TestSanitizeNarrativeForLedger.test_defuses_marker_lookalike_line  # noqa: E501
def sanitize_narrative_for_ledger(text: str) -> str:
    """Neutralize any line in caller-authored narrative `text` that would
    otherwise round-trip as a literal `<!-- ticket:T-#### -->` ledger
    section marker (T-1536).

    Root cause of the 2026-08-05 incident this exists to make structurally
    impossible: `_LEDGER_MARKER_RE`/`_splice_ticket_section`/`_parse_ledger`
    all treat ANY line matching `^<!-- ticket:T-#### -->[ \\t]*$` -- no
    matter WHERE it sits, including deep inside a `--why-file` narrative
    quoting a code fence -- as a real section boundary. A Done-report `why`
    that happens to contain such a line (e.g. quoting this very incident's
    corrupt ledger span verbatim, or any other reason an agent's narrative
    text ends up with a marker-shaped line) forges a FAKE section start the
    next time the ledger is parsed: `_parse_ledger` then reads everything
    from that fake marker to the next real one as if it were the named
    ticket's own frontmatter, fails to find valid YAML there (the
    "duplicate anchor with no frontmatter" shape from the incident), and
    the whole store refuses to load. An unbalanced code fence in the same
    narrative compounds this (a stray/incomplete ```` ```yaml ```` block can
    make the bogus chunk swallow real content past it) but is not the root
    cause by itself -- the marker-lookalike line is what turns narrative
    prose into a structural token at all.

    Every line that would otherwise be an EXACT match for the marker
    pattern is defused by inserting a single space inside the HTML-comment
    open token (`<!--` -> `<! --`) -- visually near-identical, ASCII-only,
    and guaranteed to break `_LEDGER_MARKER_RE`'s exact-string match so the
    line can never again be mistaken for a real section boundary, no matter
    how many times it round-trips through parse/splice/render. Text with no
    marker-lookalike line passes through completely unchanged."""

    def _defuse(match: re.Match[str]) -> str:
        return match.group(0).replace("<!--", "<! --", 1)

    return _LEDGER_MARKER_RE.sub(_defuse, text)


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


# frob:ticket T-1253
# Per-ticket lock file directory (`.frob/tickets/<id>.lock`), distinct from
# `_LOCK_REL` (the whole-ledger `ledger_lock` path): ledger v2 (docs/design/
# ledger-v2.md section 3) replaces the one repo-wide writer lock with a
# per-ticket lock plus a tiny allocator lock, so two callers touching
# DIFFERENT ticket ids never contend at all. Kept under `.frob/` (derived,
# gitignored) rather than inside `tickets/T-####/` itself so this ticket can
# ship the primitive ahead of the v2 store backend (T-1254) that will later
# give each ticket its own real directory to hold a lock file natively.
_TICKET_LOCK_DIR_REL = Path(".frob") / "tickets"

# frob:ticket T-1253
# The single allocator lock file guarding ONLY next-id computation (T-1090's
# root cause: allocation is inherently one shared sequence, no per-ticket
# split can avoid that) -- distinct from both `_LOCK_REL` and
# `_TICKET_LOCK_DIR_REL` so it never contends with an unrelated per-ticket or
# whole-ledger hold for a spurious reason.
_ALLOCATOR_LOCK_REL = Path(".frob") / "tickets-allocator.lock"

# frob:ticket T-1253
# Thread-local re-entrancy bookkeeping for `ticket_lock`/`allocator_lock`,
# same shape and same reasoning as `_lock_local` above (one entry per
# (path, depth) key): `flock` is scoped to an open file DESCRIPTION, not a
# process, so a naive "always os.open + flock" implementation would
# self-deadlock the moment a caller already holding a given ticket's lock
# re-enters it (e.g. a helper that itself takes `ticket_lock` for an id its
# own caller already locked). Kept as a SEPARATE thread-local dict from
# `_lock_local`'s `held` mapping (own attribute name) rather than reused, so
# a key collision between a whole-ledger lock path and a per-ticket lock path
# can never happen even in principle.
_fine_lock_local = threading.local()


def _ticket_lock_path(root: Path, ticket_id: str) -> Path:
    """The advisory lock file path for one ticket's `ticket_lock` (T-1253),
    `.frob/tickets/<id>.lock` -- distinct from `_lock_path` (the whole-ledger
    lock) and from `_allocator_lock_path` (the id-allocator lock)."""
    return root / _TICKET_LOCK_DIR_REL / f"{ticket_id}.lock"


def _allocator_lock_path(root: Path) -> Path:
    """The advisory lock file path `allocator_lock` holds (T-1253),
    `.frob/tickets-allocator.lock` -- guards only next-id computation, never
    a whole ticket's read-modify-write."""
    return root / _ALLOCATOR_LOCK_REL


@contextmanager
def _flock_path(path: Path) -> Iterator[None]:
    """Shared re-entrant `flock` primitive `ticket_lock`/`allocator_lock`
    build on (T-1253): exclusive, blocking, cross-process, re-entrant per
    thread via `_fine_lock_local` (mirrors `ledger_lock`'s own re-entrancy
    bookkeeping, kept in a separate dict so the two primitive families never
    share a key namespace). Degrades to a documented no-op on a platform
    without `fcntl`, matching `ledger_lock`'s and `derived_state_lock`'s same
    fallback -- never silently pretends to be locked."""
    if fcntl is None:  # pragma: no cover -- posix-only in this repo's CI
        _log.warning(
            "tickets: %s: fcntl unavailable on this platform, lock is a "
            "NO-OP -- concurrent writers are NOT serialized here",
            path,
        )
        yield
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    key = str(path)
    maybe_held: dict[str, tuple[int, int]] | None = getattr(
        _fine_lock_local, "held", None
    )
    held: dict[str, tuple[int, int]] = maybe_held if maybe_held is not None else {}
    if maybe_held is None:
        _fine_lock_local.held = held

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
    _log.debug("tickets: fine-grained lock acquired (%s)", path)
    try:
        yield
    finally:
        del held[key]
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        _log.debug("tickets: fine-grained lock released (%s)", path)


# frob:doc docs/design/ledger-v2.md#3-lock-model
# frob:tests tests/unit/test_process_lock.py::TestTicketLock.test_two_different_ticket_ids_do_not_block_each_other  # noqa: E501
# frob:tests tests/unit/test_process_lock.py::TestTicketLock.test_reentrant_same_id_in_same_thread_does_not_deadlock  # noqa: E501
# frob:tests tests/unit/test_process_lock.py::TestTicketLock.test_same_id_from_two_threads_serializes  # noqa: E501
# frob:ticket T-1253
@contextmanager
def ticket_lock(root: Path, ticket_id: str) -> Iterator[None]:
    """Per-ticket exclusive lock (ledger v2 design section 3): held only
    while writing ONE ticket's own files, so two callers working DIFFERENT
    ticket ids never contend at all -- generalizes the T-0933/T-0982 fix (a
    process-registry reentrancy bug caused by one shared contended resource)
    by removing the shared resource entirely for the common case (one verb,
    one ticket).

    During the compatibility window (design section 7) this composes
    alongside `ledger_lock`, not instead of it: v1 (monofile) callers keep
    using `ledger_lock` exactly as before; `ticket_lock` is additive,
    reserved for v2-mode call sites (T-1254+) and this module's own
    concurrency tests. Re-entrant per thread (same discipline as
    `ledger_lock`): a caller that already holds `ticket_lock` for `ticket_id`
    in this thread can acquire it again without deadlocking.
    """
    with _flock_path(_ticket_lock_path(root, ticket_id)):
        yield


# frob:doc docs/design/ledger-v2.md#3-lock-model
# frob:tests tests/unit/test_process_lock.py::TestAllocatorLock.test_two_concurrent_allocations_get_distinct_ids  # noqa: E501
# frob:ticket T-1253
@contextmanager
def allocator_lock(root: Path) -> Iterator[None]:
    """The single lock guarding ONLY next-id computation (ledger v2 design
    section 3) -- the one genuinely shared resource left once per-ticket
    writes no longer need a repo-wide lock (T-1090's root cause: allocation
    is inherently a global sequence). Meant to be held for microseconds (read
    an integer, increment, write it back), unlike `ledger_lock`, which today
    is held across an entire read-render-reparse-write cycle. Composes
    alongside `ledger_lock` during the compatibility window exactly like
    `ticket_lock` does -- additive, not a replacement, until the v2 store
    backend (T-1254+) actually routes allocation through it."""
    with _flock_path(_allocator_lock_path(root)):
        yield


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


# frob:ticket T-1254
# `tickets/T-####/ticket.md` (a v2-mode ticket directory), distinct from a
# legacy dir-mode flat file (`tickets/T-####-slug.md`, no subdirectory) --
# the two glob patterns never collide, so a repo can never be misread as
# both modes at once.
_V2_TICKET_GLOB = "T-*/ticket.md"


# frob:ticket T-1254
# frob:ticket T-1504
# frob:tests tests/unit/test_ticket_store.py::TestV2StoreMode.test_v2_tree_present_is_v2
def _v2_glob(root: Path) -> list[Path]:
    """Every v2-mode `tickets/T-####/ticket.md` path, sorted (ledger v2
    design section 1)."""
    d = tickets_dir(root)
    if not d.exists():
        return []
    # frob:waive WALK001 reason="d is the tickets/ dir and the glob pattern is a fixed \
    # one-level-deep 'T-*/ticket.md' shape -- a small, bounded-scope walk with no \
    # nested .git/.venv/node_modules/build/dist/target to prune, matching the gate's \
    # own small-bounded-walk escape hatch"
    return sorted(p for p in d.glob(_V2_TICKET_GLOB) if p.is_file())


# frob:ticket T-1256
# frob:doc docs/design/ledger-v2.md#43-archive-as-git-mv
# frob:tests tests/test_ticket_land.py::TestArchiveV2.test_archive_moves_directory_via_git_mv_no_content_rewrite  # noqa: E501
def v2_archive_dir(root: Path, ticket_id: str) -> Path:
    """The `tickets/archive/T-####/` directory an archived v2-mode ticket
    owns (design section 4.3) -- `archive_v2`'s `git mv` destination, same
    directory-named-by-id convention `v2_ticket_dir` uses for the active
    tree, one level deeper under `archive/`."""
    return tickets_dir(root) / "archive" / ticket_id


# frob:ticket T-1256
# frob:ticket T-1504
def _v2_archive_glob(root: Path) -> list[Path]:
    """Every archived v2-mode `tickets/archive/T-####/ticket.md` path,
    sorted (design section 4.3) -- `load_archive`'s v2-mode source, the
    archive-tree analog of `_v2_glob`."""
    d = tickets_dir(root) / "archive"
    if not d.exists():
        return []
    # frob:waive WALK001 reason="d is the tickets/archive/ dir and the glob pattern is \
    # a fixed one-level-deep 'T-*/ticket.md' shape -- a small, bounded-scope walk with \
    # no nested .git/.venv/node_modules/build/dist/target to prune, matching the \
    # gate's own small-bounded-walk escape hatch"
    return sorted(p for p in d.glob(_V2_TICKET_GLOB) if p.is_file())


# frob:doc docs/modules/tickets.md#storage-internals
# frob:doc docs/design/ledger-v2.md#1-file-per-ticket-layout
# frob:waive COV007 reason="docs/modules/tickets.md's Storage internals section \
# individually frob:describes this private helper by name (T-0529) -- a deliberate \
# architecture doc, not accidental drift onto a private helper"
def _store_mode(root: Path) -> str:
    """Which backend a repo uses: 'v2' if any `tickets/T-####/ticket.md`
    directory exists, ACTIVE OR ARCHIVED (ledger v2, design section 1/4.3 --
    checked FIRST since a v2 tree takes priority over a stray legacy
    `tickets.md`/`tickets/*.md` left behind mid-migration), else 'single' if
    `tickets.md` exists, else 'dir' if only legacy `tickets/*.md` flat files
    exist, else 'v2' (T-1553, design section 7 deliverable 4, final
    cutover: the fresh-repo default -- a repo with no ledger content at
    all now starts on the per-ticket v2 layout, not the v1 monofile).

    T-1491 investigated this exact flip and found the blast radius too
    large to land safely in the SAME pass as the flip itself: dozens of
    existing tests across this suite implicitly relied on a bare
    `tmp_path` fixture choosing v1/'single' as the default backend, not
    on an explicit `tickets.md` seed. T-1553 is that dedicated migration
    effort -- every such fixture across `tests/test_tickets.py`,
    `tests/test_ticket_land.py`, `tests/test_tickets_migration.py`,
    `tests/test_tickets_collision.py`, and `tests/test_tickets_velocity.py`
    now seeds `tickets.md` explicitly (directly, via a per-class autouse
    fixture, or via a `_seed_v1`/`_seed_single_mode` module helper) before
    exercising v1-specific behavior, so this flip changes only the
    fresh-repo default, not what any existing test actually verifies.

    T-1256: the archive glob is included alongside the active glob so a v2
    repo whose active tree has been fully drained (every ticket done/
    dropped and archived) still reads as 'v2', not 'single' -- without this
    an all-archived v2 repo would silently misdetect as a fresh/legacy
    store the moment its last active ticket is archived."""
    if _v2_glob(root) or _v2_archive_glob(root):
        return "v2"
    if ledger_path(root).exists():
        return "single"
    if _dir_glob(root):
        return "dir"
    return "v2"


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
# v2 backend: file-per-ticket (docs/design/ledger-v2.md section 1)
# ---------------------------------------------------------------------------


# frob:ticket T-1254
# frob:doc docs/design/ledger-v2.md#1-file-per-ticket-layout
# frob:tests tests/unit/test_ticket_store.py::TestV2WriteTicket.test_ticket_dir_named_by_id_not_slug  # noqa: E501
def v2_ticket_dir(root: Path, ticket_id: str) -> Path:
    """The `tickets/T-####/` directory a v2-mode ticket owns (design section
    1) -- the directory name IS the id, never a slugified title, so a
    retitle never renames the path the way legacy dir-mode does."""
    return tickets_dir(root) / ticket_id


# frob:ticket T-1254
# frob:doc docs/design/ledger-v2.md#1-file-per-ticket-layout
# frob:tests tests/unit/test_ticket_store.py::TestV2WriteTicket.test_write_then_load_v2_mode  # noqa: E501
def v2_ticket_path(root: Path, ticket_id: str) -> Path:
    """The `tickets/T-####/ticket.md` frontmatter+body file for a v2-mode
    ticket -- same shape `_serialize_ticket`/`_parse_ticket_file` already
    produce/consume for legacy dir mode, one subdirectory deeper."""
    return v2_ticket_dir(root, ticket_id) / "ticket.md"


# frob:ticket T-1254
# frob:doc docs/design/ledger-v2.md#1-file-per-ticket-layout
# frob:tests tests/unit/test_ticket_store.py::TestV2DoneReport.test_write_then_read_back_byte_for_byte  # noqa: E501
def v2_done_report_path(root: Path, ticket_id: str) -> Path:
    """The `tickets/T-####/done-report.md` file (design section 1) -- the
    Done report split OUT of `ticket.md`'s body, its own file so recording
    evidence/scope changes and writing the Done report are independently
    mergeable, independently lockable writes rather than three regex-scoped
    edits into one blob."""
    return v2_ticket_dir(root, ticket_id) / "done-report.md"


# frob:ticket T-1254
# frob:doc docs/design/ledger-v2.md#8-what-this-design-does-not-cover-open-questions-for-the-migration-child  # noqa: E501
# frob:tests tests/unit/test_ticket_store.py::TestV2Attachments.test_attachment_written_under_ticket_dir  # noqa: E501
def v2_attachments_dir(root: Path, ticket_id: str) -> Path:
    """The self-contained `tickets/T-####/attachments/` directory a v2-mode
    ticket's attachments live under (design section 8's open question,
    resolved in favor of the self-contained layout) -- distinct from the
    legacy single/dir-mode `attachments_dir` (`tickets/attachments/<id>/`,
    a side-channel shared across every ticket's attachments)."""
    return v2_ticket_dir(root, ticket_id) / "attachments"


# frob:ticket T-1254
# frob:doc docs/design/ledger-v2.md#1-file-per-ticket-layout
# frob:tests tests/unit/test_ticket_store.py::TestV2DoneReport.test_write_then_read_back_byte_for_byte  # noqa: E501
def write_done_report(
    root: Path, ticket_id: str, report_text: str
) -> Result[None, TicketError]:
    """v2-mode only: atomically write `report_text` to `tickets/T-####/
    done-report.md`, split OUT of `ticket.md`'s body (design section 1) --
    a DIFFERENT file, and therefore a DIFFERENT git object and a
    DIFFERENT lockable unit, than the ticket's own frontmatter/description.
    Held under `ticket_lock` (not the whole-ledger `ledger_lock`) since this
    only ever touches one ticket's own directory."""
    with ticket_lock(root, ticket_id):
        return atomic_write(v2_done_report_path(root, ticket_id), report_text)


# frob:ticket T-1254
# frob:doc docs/design/ledger-v2.md#1-file-per-ticket-layout
# frob:tests tests/unit/test_ticket_store.py::TestV2DoneReport.test_write_then_read_back_byte_for_byte  # noqa: E501
# frob:tests tests/unit/test_ticket_store.py::TestV2DoneReport.test_missing_report_is_none  # noqa: E501
def read_done_report(root: Path, ticket_id: str) -> str | None:
    """v2-mode only: `tickets/T-####/done-report.md`'s raw text, or `None`
    if it does not exist yet (the ticket has not reached `done`, or was
    dropped without one)."""
    path = v2_done_report_path(root, ticket_id)
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


_V2_STATE_ADD_RE = re.compile(r"^\+state:\s*(\S+)\s*$")


# frob:ticket T-1543
# frob:doc docs/design/ledger-v2.md#44-flow--velocity-mining
# frob:tests tests/test_tickets.py::TestV2StateTransitions.test_byte_similar_sibling_ticket_does_not_drop_transitions  # noqa: E501
def _v2_rename_source(root: Path, rel_path: str) -> str | None:
    """Find the single genuine git-mv predecessor path of `rel_path`, if
    any (T-1543). Restricted to `-M100%` (exact-content rename detection,
    `--diff-filter=R` only) rather than `--follow`'s broader byte-
    similarity copy heuristic: frob's own directory-rename tooling
    (`git_mv_dir` / `_renumber_v2._git_mv_ticket_dir`) always performs a
    content-preserving `git mv`, so a REAL predecessor is always exactly
    100% similar. Two v2 tickets that merely share the same templated
    frontmatter (id/title/state/body differ) are never byte-identical, so
    they can never satisfy `-M100%` and are never mistaken for a rename
    -- this is what eliminates the false-copy false positive the old
    `--follow`-based miner was vulnerable to. Returns None (never raises)
    on any git failure, no rename found, or an ambiguous/ multi-line
    match (never guess)."""
    spawned = run_argv(
        [
            "git",
            "-C",
            str(root),
            "log",
            "--diff-filter=R",
            "-M100%",
            "--name-status",
            "--format=--frob-v2-rename-commit--",
            "--",
            rel_path,
        ]
    )
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return None
    sources: set[str] = set()
    for line in spawned.danger_ok.stdout.splitlines():
        if not line.startswith("R"):
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        _status, old_path, new_path = parts
        if new_path == rel_path:
            sources.add(old_path)
    if len(sources) != 1:
        return None
    return next(iter(sources))


# frob:ticket T-1543
# frob:tests tests/test_tickets.py::TestV2StateTransitions.test_byte_similar_sibling_ticket_does_not_drop_transitions  # noqa: E501
def _v2_path_lineage(root: Path, rel_path: str) -> list[str]:
    """Reconstruct the FULL sequence of paths a v2 ticket's `ticket.md`
    has ever lived at, oldest-first (T-1543). Walks backward from
    `rel_path` through `_v2_rename_source`'s exact-100%-similarity rename
    detection only -- never git's `--follow` byte-similarity heuristic --
    so a renumber (`T-draft-<hex>` -> `T-####`) or archive `git mv` is
    still followed correctly while an unrelated ticket file that merely
    shares template boilerplate is never mistaken for a predecessor.
    Bounded to a generous fixed depth so a pathological rename cycle
    (should never occur; git mv never round-trips a path back to itself
    in this codebase) cannot loop forever."""
    lineage = [rel_path]
    seen = {rel_path}
    current = rel_path
    for _ in range(64):
        prev = _v2_rename_source(root, current)
        if prev is None or prev in seen:
            break
        lineage.insert(0, prev)
        seen.add(prev)
        current = prev
    return lineage


# frob:ticket T-1543
# frob:doc docs/design/ledger-v2.md#44-flow--velocity-mining
# frob:tests tests/test_tickets.py::TestV2StateTransitions.test_transitions_mined_oldest_first  # noqa: E501
# frob:tests tests/test_tickets.py::TestV2StateTransitions.test_no_history_returns_empty_tuple  # noqa: E501
# frob:tests tests/test_tickets.py::TestV2StateTransitions.test_byte_similar_sibling_ticket_does_not_drop_transitions  # noqa: E501
def v2_state_transitions(
    root: Path, ticket_id: str
) -> tuple[tuple[str, str, str], ...]:
    """Every `state:` transition a v2-mode ticket's OWN file has ever
    recorded, oldest-first, as `(commit_sha, author-date-iso, new_state)`
    triples -- mined purely from `git log -p` over each path in the
    ticket's `_v2_path_lineage` (design section 4.4), no separate event
    log required. A renumbered/renamed ticket directory (`T-draft-<hex>`
    -> `T-####`, or an archive `git mv`) still yields its full pre-rename
    history, mirroring how `git log --follow` used to.

    T-1543 fix: this used to run a single `git log --follow -p` call.
    `--follow`'s rename detection uses a >=50%-byte-similarity heuristic
    that is NOT restricted to genuine renames -- two unrelated v2 tickets
    routinely clear 50% similarity purely from sharing the same templated
    frontmatter (id/title/state differ, ~8 other fields identical), so
    `--follow` would misattribute a brand-new ticket's creation commit as
    a "copy from" a sibling ticket's file. Combined with `--reverse`, git
    then reports only that ONE (mis-detected) commit and stops, silently
    dropping every real subsequent transition for the ticket. Mining each
    lineage segment separately via plain (non-`--follow`) `git log -p`,
    with lineage boundaries found only through `_v2_path_lineage`'s exact
    100%-similarity rename check, cannot misattribute a merely-similar
    sibling file as a predecessor.

    Every commit that touches this file contributes at most one entry:
    the LAST added `+state: X` line the diff shows for that commit (a
    ticket rewrite that happens to touch the state line twice in one
    diff -- never expected in practice, but not assumed away -- still
    yields the one value the file actually ends that commit holding).
    Returns an empty tuple (never raises) if the ticket has no v2-mode
    file, `root` is not a git checkout, or the file has no history yet --
    matching `_setters._ledger_commit_history`'s existing best-effort git
    contract for the v1 monofile path."""
    rel_path = f"{tickets_dir(root).name}/{ticket_id}/ticket.md"
    transitions: list[tuple[str, str, str]] = []
    seen_shas: set[str] = set()
    for path in _v2_path_lineage(root, rel_path):
        _mine_v2_path_transitions(root, path, transitions, seen_shas)
    return tuple(transitions)


# frob:ticket T-1560
def _mine_v2_path_transitions(
    root: Path,
    path: str,
    transitions: list[tuple[str, str, str]],
    seen_shas: set[str],
) -> None:
    """One lineage segment's worth of `v2_state_transitions` mining:
    plain (non-`--follow`) `git log --reverse -p` over `path`, appending
    each commit's LAST added `+state: X` line to `transitions` (skipping
    shas already in `seen_shas`, which a rename commit shares across two
    adjacent lineage segments). Appends in place so the caller's
    oldest-first ordering across segments is preserved as-is."""
    spawned = run_argv(
        [
            "git",
            "-C",
            str(root),
            "log",
            "--reverse",
            "-p",
            "--format=--frob-v2-commit-- %H%x1f%aI",
            "--",
            path,
        ]
    )
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return
    current: tuple[str, str] | None = None
    pending_state: str | None = None

    def flush() -> None:
        if current is not None and pending_state is not None:
            if current[0] not in seen_shas:
                transitions.append((current[0], current[1], pending_state))
                seen_shas.add(current[0])

    for line in spawned.danger_ok.stdout.splitlines():
        if line.startswith("--frob-v2-commit-- "):
            flush()
            sha, _, iso = line[len("--frob-v2-commit-- ") :].partition("\x1f")
            current = (sha, iso)
            pending_state = None
            continue
        match = _V2_STATE_ADD_RE.match(line)
        if match is not None:
            pending_state = match.group(1)
    flush()


# frob:ticket T-1256
# frob:doc docs/design/ledger-v2.md#43-archive-as-git-mv
# frob:tests tests/test_ticket_land.py::TestArchiveV2.test_archive_moves_directory_via_git_mv_no_content_rewrite  # noqa: E501
# frob:waive DUP002 reason="near-duplicate of _renumber_v2._git_mv_ticket_dir (T-1420 \
# split of _new_renumber's v2 backend) by design -- _renumber_v2 already imports \
# helpers back from _new_renumber, and _new_renumber already imports _load_merged FROM \
# _archive, so importing this back from either would cycle; a third shared-helper \
# module for one ~15-line git-mv-with-rename-fallback is not worth the indirection, \
# per the T-1255 precedent this mirrors"
def git_mv_dir(root: Path, old_dir: Path, new_dir: Path) -> Result[None, TicketError]:
    """`git mv old_dir new_dir` (design section 4.3's archive-as-rename) --
    falls back to a plain filesystem rename if `old_dir` is not yet tracked
    by git (e.g. a just-filed draft never `git add`ed), since a git-mv over
    an untracked path always fails even though the rename itself is
    perfectly safe. Shared by `archive_v2` (this ticket) and mirrors
    `frob.tickets._renumber_v2._git_mv_ticket_dir`'s identical shape -- kept
    as its own copy here rather than imported, since `_renumber_v2` already
    imports helpers back from `_new_renumber`, and `_new_renumber` already
    imports FROM `_archive` (`_load_merged`), so a reverse import would cycle.

    Chain-review fix (found alongside T-1258, connected to
    T-1331): `git mv` on a DIRECTORY refuses with "No such file
    or directory" whenever `new_dir`'s PARENT does not exist yet (e.g. the
    very first-ever archive of a v2 repo, before `tickets/archive/` has
    ever been created) -- previously this silently took the os.rename
    fallback below, which never leaves a real git rename record (only
    `git status`'s own similarity heuristic makes it LOOK like a rename
    after the fact), undermining rename-detection unification for what is
    actually the COMMON case, not the rare untracked-draft case the
    fallback's docstring/log line describes. Pre-creating the parent here
    makes `git mv` itself succeed (and record a real rename) for every
    case except a genuinely untracked source, which is the only case the
    fallback below should ever need to handle now."""
    new_dir.parent.mkdir(parents=True, exist_ok=True)
    argv = ("git", "-C", str(root), "mv", str(old_dir), str(new_dir))
    spawned = run_argv(argv)
    if spawned.is_ok and spawned.danger_ok.returncode == 0:
        return Ok(None)
    _log.debug(
        "tickets: git mv %s -> %s failed or untracked, falling back to os.rename",
        old_dir,
        new_dir,
    )
    try:
        new_dir.parent.mkdir(parents=True, exist_ok=True)
        old_dir.rename(new_dir)
    except OSError as exc:
        _log.error(
            "tickets: git_mv_dir: rename %s -> %s failed: %s", old_dir, new_dir, exc
        )
        return Err(TicketError.WriteFailed)
    return Ok(None)


def _prune_stale_v2_dirs(root: Path, keep_dirs: set[Path]) -> None:
    """Remove any v2 ticket directory (and its `ticket.md`/`done-report.md`/
    `attachments/`) not in `keep_dirs` -- `write_all`'s v2 counterpart to
    `_prune_stale_files`. Only removes directories this store actually
    manages (`tickets/T-####/` holding a `ticket.md`); a KEPT directory's
    own files are never touched, and nothing outside `tickets/` is ever
    touched."""
    stale_dirs = {path.parent for path in _v2_glob(root)} - keep_dirs
    for ticket_dir in stale_dirs:
        shutil.rmtree(ticket_dir, ignore_errors=True)


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


# frob:ticket T-1257
# The derived, gitignored index cache (design section 6): rebuildable at
# any time from `tickets/**/ticket.md`, NEVER a second source of truth --
# a stale or missing index degrades to a full glob+parse (always correct)
# and then rebuilds itself, exactly the same "derived vs tracked" split
# `.frob/` already draws for the archive-parse cache (`_ARCHIVE_CACHE_REL`,
# T-1206) and the symbol graph.
_INDEX_REL = Path(".frob") / "tickets-index.json"


# frob:ticket T-1257
def _index_path(root: Path) -> Path:
    """The v2-mode derived index cache file (`.frob/tickets-index.json`),
    gitignored and safe to delete like the rest of `.frob/` -- deleting it
    only costs the next load's speedup, never correctness (section 6)."""
    return root / _INDEX_REL


# frob:ticket T-1257
# frob:tests tests/test_tickets.py::TestV2IndexCache.test_stale_index_falls_back_to_fresh_parse  # noqa: E501
def _read_index_cache(index_path: Path, paths: list[Path]) -> dict[str, Ticket] | None:
    """The cached v2-mode parse keyed by exact `(relative path, mtime-ns)`
    pairs for every path in `paths`, or `None` meaning "caller must parse
    fresh" -- a cache hit requires the recorded path SET and every
    recorded mtime to match `paths` EXACTLY (an added/removed/touched
    ticket file is a miss, never a silently stale hit, per design section
    6's staleness contract). Any read/parse/schema failure is treated the
    same as a miss -- logged and ignored, since this cache is purely a
    speed optimization derived from the files themselves."""
    if not index_path.exists():
        return None
    try:
        raw = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _log.warning("tickets: v2 index cache unreadable, reparsing (%s)", exc)
        return None
    if not isinstance(raw, dict):
        return None
    entries = raw.get("entries")
    tickets_raw = raw.get("tickets")
    if not isinstance(entries, dict) or not isinstance(tickets_raw, dict):
        return None
    live: dict[str, int] = {}
    for path in paths:
        try:
            live[str(path)] = path.stat().st_mtime_ns
        except OSError:
            return None
    if set(live) != set(entries):
        _log.debug("tickets: v2 index cache stale (path set changed)")
        return None
    if any(entries[key] != mtime_ns for key, mtime_ns in live.items()):
        _log.debug("tickets: v2 index cache stale (mtime changed)")
        return None
    try:
        return {
            ticket_id: Ticket.model_validate(data)
            for ticket_id, data in tickets_raw.items()
        }
    except ValidationError as exc:
        _log.warning(
            "tickets: v2 index cache failed to deserialize, reparsing (%s)", exc
        )
        return None


# frob:ticket T-1257


# frob:raises BaseException
def _write_index_cache(
    index_path: Path, paths: list[Path], tickets: dict[str, Ticket]
) -> None:
    """Best-effort rebuild of the v2 index cache from a just-completed
    fresh parse. Never raises for an ordinary write failure -- OSError or
    any other `Exception` only costs the NEXT load's speedup, never
    correctness (mirrors `_write_archive_cache`). A `KeyboardInterrupt`/
    `SystemExit` mid-write still propagates (the inner `except
    BaseException: ... raise` is cleanup-then-reraise, never a discharge)
    -- this cache write has no business intercepting a real interrupt/
    exit, T-1371."""
    entries: dict[str, int] = {}
    for path in paths:
        try:
            entries[str(path)] = path.stat().st_mtime_ns
        except OSError:
            return  # a path vanished mid-write -- skip caching this round
    payload = {
        "entries": entries,
        "tickets": {
            ticket_id: ticket.model_dump(mode="json")
            for ticket_id, ticket in tickets.items()
        },
    }
    try:
        index_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(index_path.parent), prefix=".tickets-index-"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
            os.replace(tmp_name, index_path)
        except BaseException:
            with suppress(OSError):
                os.unlink(tmp_name)
            raise
    except OSError as exc:
        _log.warning("tickets: failed to write v2 index cache, skipping (%s)", exc)
    except Exception as exc:
        # "Never raises" (this function's own docstring) -- the inner
        # `except BaseException: ... raise` above is cleanup-then-
        # reraise, not a discharge, so a non-`OSError` write surprise
        # (e.g. `json.dump` choking on a genuinely unexpected payload
        # shape) previously escaped past this function's own documented
        # contract (EXHAUST002, T-1371). A bare `except:`/`BaseException`
        # here would also swallow `KeyboardInterrupt`/`SystemExit`, which
        # this best-effort CACHE write has no business intercepting.
        _log.warning("tickets: failed to write v2 index cache, skipping (%s)", exc)


# frob:doc docs/modules/tickets.md#storage-internals
# frob:doc docs/design/ledger-v2.md#1-file-per-ticket-layout
# frob:doc docs/design/ledger-v2.md#6-greppability
def load_all(root: Path) -> Result[dict[str, Ticket], TicketError]:
    """Every ticket in the repo as an id -> Ticket map, backend-agnostic.

    T-1257: v2-mode reads try the derived `.frob/tickets-index.json` cache
    first (design section 6) -- a hit skips re-parsing every
    `ticket.md`'s YAML frontmatter, a miss (missing/stale) transparently
    falls back to the full glob+parse below and then rebuilds the cache,
    so a v2-mode `doable`/`list`/`show` never trades correctness for
    speed."""
    mode = _store_mode(root)
    if mode == "single":
        ledger = ledger_path(root)
        if not ledger.exists():
            return Ok({})
        return _parse_ledger(ledger.read_text(encoding="utf-8"))
    paths = _v2_glob(root) if mode == "v2" else _dir_glob(root)
    if mode == "v2":
        cache_key_paths = _v2_cache_key_paths(paths)
        cached = _read_index_cache(_index_path(root), cache_key_paths)
        if cached is not None:
            _log.debug("tickets: v2 index cache hit (%d ticket(s))", len(cached))
            return Ok(cached)
    tickets: dict[str, Ticket] = {}
    for path in paths:
        parsed = _parse_ticket_file(path)
        if parsed.is_err:
            _log.error("tickets: load aborted, %s is malformed", path)
            return Err(parsed.danger_err)
        ticket = parsed.danger_ok
        if mode == "v2":
            ticket = _merge_sibling_done_report(ticket, path)
        if ticket.id in tickets:
            _log.error("tickets: duplicate id %s (%s)", ticket.id, path)
            return Err(TicketError.DuplicateId)
        tickets[ticket.id] = ticket
    if mode == "v2":
        _write_index_cache(_index_path(root), cache_key_paths, tickets)
    return Ok(tickets)


# frob:ticket T-1587
def _v2_cache_key_paths(ticket_paths: list[Path]) -> list[Path]:
    """`ticket_paths` plus every existing sibling `done-report.md`, sorted
    -- the staleness key `_read_index_cache`/`_write_index_cache` must use
    now that a loaded `Ticket.body` carries its Done report
    (`_merge_sibling_done_report`).

    Keying on `ticket.md` alone would serve a cached body from before a
    `done-report.md` write, since `set_done_report`'s v2 path never
    touches `ticket.md` at all -- the report would appear only after some
    unrelated edit happened to invalidate the cache."""
    keyed = list(ticket_paths)
    keyed.extend(
        report
        for path in ticket_paths
        if (report := path.parent / "done-report.md").exists()
    )
    return sorted(keyed)


# frob:ticket T-1587
def _merge_sibling_done_report(ticket: Ticket, ticket_md: Path) -> Ticket:
    """`ticket` with its v2 `done-report.md` spliced back into `body`.

    v2 stores the Done report in its own file for lock independence
    (`write_done_report`), but EVERY consumer -- close's substantive-report
    check, evidence recovery, TICK006, the land ledger merge -- reads
    `Ticket.body`. Without this merge they all silently see no report in a
    v2 repo: `frob ticket close` refuses a ticket whose report was written
    seconds earlier, and TICK006 goes blind. `write_ticket`'s v2 branch
    splits it back out, so the round trip never duplicates the section
    into `ticket.md`."""
    report = ticket_md.parent / "done-report.md"
    if not report.exists():
        return ticket
    text = report.read_text(encoding="utf-8")
    if not text.strip():
        return ticket
    return ticket.model_copy(
        update={"body": replace_done_report_section(ticket.body, text)}
    )


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
# frob:invariant INV-050
# invariant spec: [INV-050](invariants/INV-050.md)
# frob:ticket T-1519
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


# frob:raises BaseException
def _write_archive_cache(
    cache_path: Path, digest: str, tickets: dict[str, Ticket]
) -> None:
    """Best-effort write of the parsed archive to `cache_path`, keyed by
    `digest`. Never raises for an ordinary write failure -- OSError or
    any other `Exception` is logged and swallowed rather than surfaced as
    a `load_archive` error. A `KeyboardInterrupt`/`SystemExit` mid-write
    still propagates (the inner `except BaseException: ... raise` is
    cleanup-then-reraise, never a discharge) -- this cache write has no
    business intercepting a real interrupt/exit, T-1371."""
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
    except Exception as exc:
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
    byte change invalidates the cache on the very next read.

    T-1256: v2 mode (design section 4.3) has no single archive FILE to
    hash, so this branch bypasses the content-hash cache entirely and globs
    `tickets/archive/T-####/ticket.md` directly, one small parse per
    archived ticket -- the same shape `load_all`'s v2 branch already uses
    for the active tree. Archived tickets are never rewritten in place
    (only `git mv`-ed in whole), so there is little steady-state churn for
    a cache to save here the way there is for the single-file archive."""
    if _store_mode(root) == "v2":
        tickets: dict[str, Ticket] = {}
        for path in _v2_archive_glob(root):
            parsed = _parse_ticket_file(path)
            if parsed.is_err:
                _log.error("tickets: load_archive aborted, %s is malformed", path)
                return Err(parsed.danger_err)
            # T-1587: same merge the active tree gets -- an archived
            # ticket's Done report is what TICK006 resolves against.
            ticket = _merge_sibling_done_report(parsed.danger_ok, path)
            if ticket.id in tickets:
                _log.error("tickets: duplicate archived id %s (%s)", ticket.id, path)
                return Err(TicketError.DuplicateId)
            tickets[ticket.id] = ticket
        return Ok(tickets)
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
# frob:ticket T-1583
def _write_archive_v2(
    root: Path, tickets: dict[str, Ticket]
) -> Result[None, TicketError]:
    """`write_archive`'s v2-mode body: upsert every entry into its own
    `tickets/archive/T-####/ticket.md` (`write_archived_ticket`) and prune
    any archived ticket directory whose id is absent from `tickets`, so
    the wholesale-replace contract the monofile branch has holds here too.

    Every prune is logged with its id -- this is the only path that
    removes archived ledger content, and a silent removal here would be
    indistinguishable from the T-1583 loss it exists to fix."""
    for ticket in tickets.values():
        written = write_archived_ticket(root, ticket)
        if written.is_err:
            return Err(written.danger_err)
    for path in _v2_archive_glob(root):
        ticket_id = path.parent.name
        if ticket_id in tickets:
            continue
        _log.info(
            "tickets: write_archive pruning archived %s -- absent from the "
            "wholesale map this call replaces the archive with",
            ticket_id,
        )
        shutil.rmtree(path.parent)
    return Ok(None)


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
    not been updated to pass a digest.

    T-1583: v2 mode has no archive monofile, so this delegates to
    `_write_archive_v2` -- one `tickets/archive/T-####/ticket.md` per
    entry, matching what `load_archive`'s own v2 branch reads. Writing the
    monofile unconditionally (the pre-T-1583 behavior) put every archived
    ticket somewhere `load_archive` would never look while `archive()`
    went on to drop those same ids from the active store, losing them from
    every read path."""
    if _store_mode(root) == "v2":
        return _write_archive_v2(root, tickets)
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
# frob:doc docs/design/ledger-v2.md#3-lock-model
# frob:ticket T-0458
# frob:ticket T-1254
# frob:ticket T-1536
# frob:tests tests/unit/test_ticket_store.py::TestV2WriteTicket.test_write_then_load_v2_mode  # noqa: E501
# frob:tests tests/unit/test_ticket_store.py::TestWriteTicket.test_marker_lookalike_body_line_refuses_write  # noqa: E501
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

    T-1254: v2 mode takes the NEW per-ticket `ticket_lock` (design section
    3) rather than the whole-ledger `ledger_lock` -- two callers writing
    DIFFERENT ticket ids never contend at all, the structural fix the design
    doc's incident museum (T-1036/T-0933/T-0982) traces every ledger-churn
    race back to. Composes with the caller's own `ledger_lock` hold where
    one exists (e.g. `_reporting.py`'s `set_done_report`) rather than
    replacing it -- see `ticket_lock`'s own docstring.

    T-1536: single mode's spliced text is re-parsed IN MEMORY before it is
    ever written to disk (`_post_splice_integrity_check`) -- the same
    "refuse before the corruption is durable" posture `write_all`/
    `write_archive`/`splice_ledger` already had via `_check_ledger_id_
    integrity`, extended to this single-ticket path, which previously had
    no post-splice check at all. A `ticket.body` containing a line that
    happens to be byte-identical to another ticket's `<!-- ticket:T-#### -->`
    marker (forging a fake section boundary) or any other splice defect
    that would make the ledger fail to re-parse, or silently drop a
    sibling id that was present before this write, refuses the write
    outright (`Err(LedgerIntegrityViolation)`) instead of persisting a
    ledger the very next read could fail to load.
    """
    mode = _store_mode(root)
    if mode == "v2":
        # T-1587: `load_all` merges done-report.md back into `body`, so a
        # load -> modify -> write round trip arrives here carrying the
        # report. Split it back out (never write it into ticket.md) or the
        # section would be duplicated on the next read and ticket.md would
        # start contending with done-report.md writes again.
        body, report_text = _split_done_report(ticket.body)
        with ticket_lock(root, ticket.id):
            written = atomic_write(
                v2_ticket_path(root, ticket.id),
                _serialize_ticket(ticket.model_copy(update={"body": body})),
            )
            if written.is_err or report_text is None:
                return written
            return atomic_write(v2_done_report_path(root, ticket.id), report_text)
    with ledger_lock(root):
        if mode == "single":
            return _write_ticket_single_mode(root, ticket)
        return atomic_write(_dir_path_for(root, ticket), _serialize_ticket(ticket))


# frob:ticket T-1536
def _write_ticket_single_mode(root: Path, ticket: Ticket) -> Result[None, TicketError]:
    """`write_ticket`'s single-mode body, split out to keep the public
    dispatcher under the ARCH001 length threshold (T-1536): splice
    `ticket`'s own marker block into the on-disk ledger text
    (`_splice_ticket_section`, T-0505) and refuse to persist unless the
    result re-parses cleanly with no id lost (`_post_splice_integrity_
    check`). Caller already holds `ledger_lock`."""
    return _splice_single_ticket(ledger_path(root), _LEDGER_HEADER, ticket)


def _splice_single_ticket(
    path: Path, header: str, ticket: Ticket
) -> Result[None, TicketError]:
    """Shared single-mode splice body for `_write_ticket_single_mode` and
    `write_archived_ticket` (T-1536/T-1561): splice `ticket`'s own marker
    block into the monofile at `path` (seeded from `header` if absent) and
    refuse to persist unless the result re-parses cleanly with no id lost
    (`_post_splice_integrity_check`). Caller already holds the appropriate
    lock for `path`."""
    if not path.exists():
        fresh = _splice_ticket_section(header, ticket)
        integrity = _post_splice_integrity_check(frozenset(), ticket.id, fresh)
        if integrity.is_err:
            return Err(integrity.danger_err)
        return atomic_write(path, fresh)
    text = path.read_text(encoding="utf-8")
    parsed = _parse_ledger(text)
    if parsed.is_err:
        return Err(parsed.danger_err)
    before_ids = frozenset(parsed.danger_ok)
    spliced = _splice_ticket_section(text, ticket)
    integrity = _post_splice_integrity_check(before_ids, ticket.id, spliced)
    if integrity.is_err:
        return Err(integrity.danger_err)
    return atomic_write(path, spliced)


# frob:ticket T-1536
# frob:tests tests/unit/test_ticket_store.py::TestWriteTicket.test_marker_lookalike_body_line_refuses_write  # noqa: E501
def _post_splice_integrity_check(
    before_ids: frozenset[str], written_id: str, spliced_text: str
) -> Result[None, TicketError]:
    """`write_ticket`'s single-mode post-splice guard (T-1536): re-parse
    `spliced_text` and refuse (`Err(LedgerIntegrityViolation)`) unless it
    parses cleanly AND every id that was present in `before_ids` (plus
    `written_id` itself) still round-trips out with its marker intact.

    Catches two failure shapes in one check: (1) `spliced_text` fails to
    re-parse at all -- e.g. `written_id`'s own body contains a line that
    forges a fake `<!-- ticket:T-#### -->` marker for some OTHER id, so
    `_parse_ledger` reads a chunk of narrative prose as that id's (invalid)
    frontmatter and errors; (2) `spliced_text` parses fine but a sibling id
    silently vanished from it -- the markerless-block class T-0764's
    `_check_ledger_id_integrity` already guards for `write_all`/
    `write_archive`/`splice_ledger`, extended here to the one write path
    that previously had no post-write check of its own at all."""
    reparsed = _parse_ledger(spliced_text)
    if reparsed.is_err:
        _log.error(
            "tickets: write refused -- splicing %s produced a ledger that "
            "fails to re-parse (%s, T-1536 post-write integrity check)",
            written_id,
            reparsed.danger_err,
        )
        return Err(TicketError.LedgerIntegrityViolation)
    missing = (before_ids | {written_id}) - set(reparsed.danger_ok)
    if missing:
        _log.error(
            "tickets: write refused -- splicing %s dropped id(s) %s from "
            "the ledger (T-1536 post-write integrity check)",
            written_id,
            sorted(missing),
        )
        return Err(TicketError.LedgerIntegrityViolation)
    return Ok(None)


# frob:ticket T-1561
# frob:doc docs/modules/tickets.md#storage-internals
# frob:tests \
# tests/unit/test_ticket_store.py::TestWriteArchivedTicket.test_v2_mode_writes_under_ar\
# chive_dir kind="unit"
# frob:tests \
# tests/unit/test_ticket_store.py::TestWriteArchivedTicket.test_single_mode_splices_int\
# o_archive_file kind="unit"
def write_archived_ticket(root: Path, ticket: Ticket) -> Result[None, TicketError]:
    """Upsert ONE ticket into ARCHIVE storage (T-1561): the archive-side
    analog of `write_ticket`, which only ever writes to ACTIVE storage.

    Root cause this exists to close: `frob ticket evidence --replace`
    (and any other single-ticket mutation) loads via `_load_one` ->
    `load_all`, which reads ONLY the active tree/ledger -- an archived
    ticket resolves to `NotFound` there even though COV003 still scans
    `tickets-archive.md`/`tickets/archive/**` for stale evidence bindings
    on it. The 2026-08-05 incident this fixes: COV003 fired on archived
    T-1269/T-1495 after their bound tests were renamed, `evidence
    --replace` answered `NotFound`, and the coordinator worked around it
    with a raw string swap directly in `tickets-archive.md` -- exactly
    the hand-edit-the-ledger hazard this whole CLI exists to make
    unnecessary. `write_archived_ticket` plus `--archived`-aware callers
    (see `replace_evidence`'s `archived` parameter) give the CLI a real
    path to repair what the gate polices, instead of a workaround.

    v2 mode: identical shape to `write_ticket`'s v2 branch, just under
    `v2_archive_dir` instead of `v2_ticket_path`, still under the
    per-ticket `ticket_lock` (never the archive's own bulk `ledger_lock`
    -- writing one archived ticket must not block a concurrent archive of
    a DIFFERENT ticket). Single mode: the archive-side analog of
    `_write_ticket_single_mode` -- splices `ticket`'s own marker block
    into `tickets-archive.md`'s raw text (`_splice_ticket_section`) and
    refuses (`Err(LedgerIntegrityViolation)`) unless the result re-parses
    cleanly with no id lost, the SAME T-1536 post-splice integrity
    posture `write_ticket` already holds for the active ledger. `dir`
    mode has no archive concept of its own (legacy dir-mode repos have
    always used `archive()`'s wholesale `write_archive` instead) -- this
    function refuses with `Err(NotFound)` rather than silently writing
    somewhere a dir-mode repo would never look."""
    mode = _store_mode(root)
    if mode == "v2":
        with ticket_lock(root, ticket.id):
            return atomic_write(
                v2_archive_dir(root, ticket.id) / "ticket.md",
                _serialize_ticket(ticket),
            )
    if mode != "single":
        _log.error(
            "tickets: write_archived_ticket refused -- %s mode has no "
            "single-ticket archive write path (T-1561)",
            mode,
        )
        return Err(TicketError.NotFound)
    with ledger_lock(root):
        return _splice_single_ticket(archive_path(root), _ARCHIVE_HEADER, ticket)


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
    fingerprint.

    T-1254: v2 mode writes each ticket's own `ticket.md` (never touching a
    sibling's `done-report.md`/`attachments/`) and prunes any v2 directory
    not present in `tickets` (`_prune_stale_v2_dirs`), mirroring dir mode's
    write-each-then-prune shape one directory level deeper. Held under the
    same `ledger_lock` as the other branches -- a wholesale replace is
    still a whole-store operation regardless of backend, distinct from the
    single-ticket `ticket_lock` `write_ticket` uses for its own v2 path.
    Each backend's own body is a private per-mode helper (`_write_all_
    single`/`_write_all_v2`/`_write_all_dir`) so this function stays the
    thin mode-dispatch it reads as."""
    with ledger_lock(root):
        mode = _store_mode(root)
        if mode == "single":
            return _write_all_single(root, tickets, expected_digest)
        if mode == "v2":
            return _write_all_v2(root, tickets)
        return _write_all_dir(root, tickets)


def _write_all_single(
    root: Path, tickets: dict[str, Ticket], expected_digest: str | None
) -> Result[None, TicketError]:
    """`write_all`'s single-mode body (T-0889 digest guard, T-0764
    integrity check), split out so `write_all` itself stays a thin
    mode-dispatch."""
    path = ledger_path(root)
    if expected_digest is not None:
        current = ledger_digest(path)
        if current != expected_digest:
            _log.error(
                "tickets: write_all refused -- %s changed on disk "
                "since this caller's load (expected digest %s, found %s)",
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


def _write_all_v2(root: Path, tickets: dict[str, Ticket]) -> Result[None, TicketError]:
    """`write_all`'s v2-mode body (T-1254): write each ticket's own
    `ticket.md`, then prune any v2 directory not present in `tickets`."""
    keep_dirs: set[Path] = set()
    for ticket in tickets.values():
        path = v2_ticket_path(root, ticket.id)
        result = atomic_write(path, _serialize_ticket(ticket))
        if result.is_err:
            return Err(result.danger_err)
        keep_dirs.add(v2_ticket_dir(root, ticket.id))
    _prune_stale_v2_dirs(root, keep_dirs)
    return Ok(None)


def _write_all_dir(root: Path, tickets: dict[str, Ticket]) -> Result[None, TicketError]:
    """`write_all`'s legacy dir-mode body: write each `T-####-slug.md`, then
    prune any file whose id is no longer present."""
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


# frob:ticket T-1259
# frob:doc docs/modules/tickets.md#migration-to-v2-t-1259-docsdesignledger-v2md-section-7  # noqa: E501
def _split_done_report(body: str) -> tuple[str, str | None]:
    """Split a v1-mode ticket `body` into (body_without_done_report,
    done_report_text_or_None), the mechanical inverse of `_models.
    replace_done_report_section`'s splice: v1 embeds the '## Done report'
    section inside the same body block `_render_ledger` writes; v2 stores
    it in its own `done-report.md` (design section 1). Reuses `_models`'s
    own heading/section-boundary scan (`_find_done_report_heading`/
    `_done_report_section_end`) rather than re-deriving the same T-0493/
    T-0848 boundary logic a second time -- the section runs from a genuine
    `## Done report` heading through the next structural heading or EOF,
    exactly what `replace_done_report_section` itself treats as
    replaceable. Returns `(body, None)` unchanged if `body` carries no Done
    report section at all (a queued/in-progress ticket)."""
    lines = body.splitlines()
    heading_idx = _find_done_report_heading(lines)
    if heading_idx is None:
        return body, None
    end_idx = _done_report_section_end(lines, heading_idx)
    report_lines = lines[heading_idx:end_idx]
    remaining = lines[:heading_idx] + lines[end_idx:]
    while remaining and remaining[-1] == "":
        remaining.pop()
    report_text = "\n".join(report_lines).strip("\n") + "\n"
    new_body = "\n".join(remaining)
    return new_body, report_text


# frob:ticket T-1259
# frob:doc docs/modules/tickets.md#migration-to-v2-t-1259-docsdesignledger-v2md-section-7  # noqa: E501
# frob:tests tests/test_tickets_migration.py::TestMigrateV1ToV2.test_migrates_one_active_ticket_with_done_report  # noqa: E501
def _migrate_one_v2(
    root: Path, ticket: Ticket, dest_dir: Path
) -> Result[None, TicketError]:
    """Write one v1-mode `ticket` into a v2-mode `dest_dir` (an active
    `tickets/T-####/` or archived `tickets/archive/T-####/` directory,
    caller's choice): splits the embedded Done report out of `ticket.body`
    into `dest_dir/done-report.md` (`_split_done_report`), writes the
    remaining frontmatter+body to `dest_dir/ticket.md`, and `git mv`s any
    legacy `tickets/attachments/<id>/` directory to `dest_dir/attachments/`
    (design section 7's "moved attachments" deliverable) via the same
    `git_mv_dir` primitive `archive_v2` already uses."""
    new_body, report_text = _split_done_report(ticket.body)
    migrated = ticket.model_copy(update={"body": new_body})
    written = atomic_write(dest_dir / "ticket.md", _serialize_ticket(migrated))
    if written.is_err:
        return Err(written.danger_err)
    if report_text is not None:
        report_written = atomic_write(dest_dir / "done-report.md", report_text)
        if report_written.is_err:
            return Err(report_written.danger_err)
    legacy_attachments = attachments_dir(root, ticket.id)
    if legacy_attachments.is_dir() and any(legacy_attachments.iterdir()):
        moved = git_mv_dir(root, legacy_attachments, dest_dir / "attachments")
        if moved.is_err:
            return Err(moved.danger_err)
    return Ok(None)


# frob:ticket T-1259
# frob:doc docs/modules/tickets.md#migration-to-v2-t-1259-docsdesignledger-v2md-section-7  # noqa: E501
# frob:doc docs/modules/tickets.md#storage-internals
# frob:tests tests/test_tickets_migration.py::TestMigrateV1ToV2.test_golden_round_trip_semantic_equality  # noqa: E501
# frob:tests tests/test_tickets_migration.py::TestMigrateV1ToV2.test_idempotent_no_v1_state_is_a_no_op  # noqa: E501
# frob:tests tests/test_tickets_migration.py::TestMigrateV1ToV2.test_draft_id_ticket_migrates_like_any_other  # noqa: E501
def migrate_v1_to_v2(root: Path) -> Result[int, TicketError]:
    """One-shot, reversible migrator (ledger v2 design section 7,
    deliverable 1): reads today's `tickets.md`/`tickets-archive.md` via
    `_parse_ledger`, writes each ticket into a v2-mode `tickets/T-####/
    ticket.md` (+ `done-report.md`, + a moved `attachments/`), WITHOUT
    deleting the monofile ledgers in the same call -- rolling back is
    `rm -rf tickets/T-*/ tickets/archive/` while `tickets.md`/`tickets-
    archive.md` are still exactly as they were (nothing here ever writes
    to either path).

    A no-op (`Ok(0)`) if the repo is already v2-mode (`_store_mode`) --
    migrate is safe to invoke repeatedly. Returns the number of tickets
    migrated (active + archived), mirroring `migrate_to_ledger`'s own
    return-count convention."""
    if _store_mode(root) == "v2":
        _log.info("tickets: already v2-mode, nothing to migrate")
        return Ok(0)
    active: dict[str, Ticket] = {}
    active_path = ledger_path(root)
    if active_path.exists():
        parsed = _parse_ledger(active_path.read_text(encoding="utf-8"))
        if parsed.is_err:
            return Err(parsed.danger_err)
        active = parsed.danger_ok
    archived: dict[str, Ticket] = {}
    archive_p = archive_path(root)
    if archive_p.exists():
        parsed = _parse_ledger(archive_p.read_text(encoding="utf-8"))
        if parsed.is_err:
            return Err(parsed.danger_err)
        archived = parsed.danger_ok
    for ticket_id, ticket in active.items():
        result = _migrate_one_v2(root, ticket, v2_ticket_dir(root, ticket_id))
        if result.is_err:
            return Err(result.danger_err)
    for ticket_id, ticket in archived.items():
        result = _migrate_one_v2(root, ticket, v2_archive_dir(root, ticket_id))
        if result.is_err:
            return Err(result.danger_err)
    total = len(active) + len(archived)
    _log.info(
        "tickets: migrated %d ticket(s) to v2 layout (%d active, %d archived); "
        "tickets.md/tickets-archive.md left in place -- delete tickets/T-*/ "
        "tickets/archive/ to roll back",
        total,
        len(active),
        len(archived),
    )
    return Ok(total)


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
