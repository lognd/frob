"""`changelog.d/T-####.md` fragment-per-ticket changelog (T-2445).

MEASURED PROBLEM: 6 of the last 7 land commits touched BOTH `CHANGELOG.md`
and `pyproject.toml`'s version line -- every land writes the same shared
paths, independent of how disjoint the tickets' own code scopes are. This
module gives `frob ticket land` a COLLISION-FREE alternative for the
changelog half: instead of splicing prose into `CHANGELOG.md`'s single
shared "unreleased" section (an insertion point every land shares), each
land writes its OWN uniquely-named fragment file -- `changelog.d/T-####.
md`, keyed by ticket id, which by construction can never collide with any
other ticket's fragment, ever, regardless of concurrent activity on main.

WHY A FRAGMENT INSTEAD OF A DIRECT SPLICE, EVEN THOUGH `frob.tickets.
_land_release._reset_release_artifacts_to_pre_land` already resets
`CHANGELOG.md` fresh from `pre_land_tip` before every land (so the
in-land splice itself is not usually a literal git merge conflict): an
interrupted land (a killed process, an uncaught exception, a lock
timeout) that dies AFTER writing but before finishing a multi-file
text-splice/regex-substitute leaves root's shared working tree in a
half-mutated state that the NEXT land -- for a completely unrelated,
disjoint ticket -- has to manually reconcile before it can proceed. A
fragment write is a single new file, written via `atomic_write` (temp
file + fsync + `os.replace`), so the worst an interrupted land can leave
behind is one harmless extra file; the very next land's own fragment
assembly step trivially heals over it (SELF-HEALING BY CONSTRUCTION,
not by an unwind step that itself might fail).

`assemble_changelog_from_fragments` regenerates `CHANGELOG.md`'s current
"unreleased" section as a pure, deterministic function of the full
fragment set (sorted by ticket id, numerically, for reproducible order)
every time it runs -- so two lands that each add a fragment and then
regenerate never disagree about the result: whichever runs last simply
recomputes the same answer from the (now larger) fragment set. This is
called from INSIDE `frob ticket land`'s own serialized critical section
(the same `land.lock` that already serializes real land execution), so
there is no concurrent-write hazard on `CHANGELOG.md` itself either --
the fragment is the durable, collision-free artifact; the assembled
`CHANGELOG.md` write is a cheap, idempotent derived step.

DISCLOSED SCOPE CUT (see T-2445's Done report for the follow-up ticket
id): `pyproject.toml`'s version line and `.frob-release.json`'s stamped
manifest are UNCHANGED by this module -- they still bump on every land,
exactly as before T-2445. A fuller design that also defers THAT bump to
an explicit `frob release assemble`-style cut needs `frob.gates.
release_gate`'s REL001 check and `frob.app.ticket_runner._close_cmd`'s
close-time bump preflight to both learn a new "deferred, not missing"
posture -- out of this leaf's reach (its `src/frob/gates/__init__.py`
lease was held by a concurrent ticket at dispatch time) and correctly
belongs in its own leaf regardless, per this repo's staged-landing
discipline for exactly this class of change.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.release import ReleaseError
from frob.tickets._store import atomic_write

_log = get_logger(__name__)

# frob:doc docs/modules/release.md#changelog-fragments-t-2445
#: The land-owned fragment directory name, relative to a repo root --
#: mirrors `towncrier`'s own `changelog.d/` convention (T-2445's own
#: acceptance note: "the standard solution to exactly this problem").
FRAGMENT_DIR_NAME = "changelog.d"

_TICKET_ID_RE = re.compile(r"^T-(\d+)$")
_FRAGMENT_HEADER_RE = re.compile(r"^bump:\s*(\S+)\s*$")


# frob:doc docs/modules/release.md#changelog-fragments-t-2445
# frob:tests tests/test_release.py::TestChangelogFragments.test_write_then_read_round_trips  # noqa: E501
class ChangelogFragment(BaseModel):
    """One `changelog.d/T-####.md` file's parsed content: the ticket id
    that wrote it, the note text a `CHANGELOG.md` bullet is built from,
    and the raw `bump:` header line's value (`frob.release.BumpClass`'s
    lowercased name -- kept as `str` here, not the enum itself, so this
    model stays a trivial round-trip of the on-disk text with no import
    coupling to the enum's own definition)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ticket_id: str
    bump: str
    note: str


# frob:doc docs/modules/release.md#changelog-fragments-t-2445
# frob:tests tests/test_release.py::TestChangelogFragments.test_assemble_writes_every_fragment_as_a_bullet  # noqa: E501
def fragment_dir(root: Path) -> Path:
    """`root`'s `changelog.d/` directory (T-2445) -- may not exist yet on
    a repo that has never landed a bump-worthy ticket."""
    return root / FRAGMENT_DIR_NAME


# frob:doc docs/modules/release.md#changelog-fragments-t-2445
# frob:tests tests/test_release.py::TestChangelogFragments.test_write_then_read_round_trips  # noqa: E501
def fragment_path(root: Path, ticket_id: str) -> Path:
    """The fragment path a land for `ticket_id` writes/reads (T-2445):
    `changelog.d/T-####.md`. The ticket id IS the collision-avoidance
    mechanism -- two different tickets can never write the same path,
    and the SAME ticket landing is (by this repo's own ticket-lifecycle
    invariant) a one-time event, so an overwrite here is never a
    legitimate two-writer race."""
    return fragment_dir(root) / f"{ticket_id}.md"


# frob:doc docs/modules/release.md#changelog-fragments-t-2445
# frob:tests tests/test_release.py::TestChangelogFragments.test_write_then_read_round_trips  # noqa: E501
def write_changelog_fragment(
    root: Path, ticket_id: str, bump: str, note: str
) -> Result[Path | None, ReleaseError]:
    """Write `changelog.d/T-####.md` for `ticket_id` (T-2445): `bump` is
    `frob.release.BumpClass`'s lowercased `.name` (e.g. `"minor"`),
    `note` is the same `"{final_id}: {ticket.title}"` string `frob.
    tickets._land_release`'s old direct-splice path used to hand
    `changelog_skeleton_entry`. Overwrites idempotently if a fragment for
    this ticket already exists (a retried land for the same ticket
    writing the same content, never two different tickets colliding).
    `Err(WriteFailed)` on the underlying `atomic_write` I/O failure,
    matching every other release-artifact write in this package's error
    vocabulary.

    T-2615: refuses to write -- `Ok(None)`, no file touched, not an error
    -- when `ticket_id`'s CURRENT on-disk state is a known non-`DONE`
    terminal/non-terminal state (observed: `DROPPED`). A real incident
    landed a ticket that had already been dropped on `main` moments
    earlier (the worktree's pre-land snapshot predated the drop, and the
    land's own pre-land `main` merge pulled the dropped state in just
    before this call runs) -- its fragment then announced a fix that was
    never made and fed a real version bump. Re-reading state here, right
    before the write, catches exactly that window: whatever `_load_one`
    reports is the freshest state a still-in-progress land can see. If
    the ticket cannot be loaded at all (`Err`), this fails OPEN and
    writes anyway -- an unrelated lookup failure (a transient I/O error,
    an unusual store layout) must not silently swallow a legitimate
    land's changelog entry; the check exists to catch a KNOWN non-DONE
    state, not to gate on an inability to determine one."""
    from frob.tickets import _load_one
    from frob.tickets._models import TicketState

    loaded = _load_one(root, ticket_id)
    if loaded.is_ok and loaded.danger_ok.state != TicketState.DONE:
        _log.warning(
            "release: write_changelog_fragment: %s is %s (not done) -- "
            "refusing to write a changelog fragment for it (T-2615)",
            ticket_id,
            loaded.danger_ok.state,
        )
        return Ok(None)
    path = fragment_path(root, ticket_id)
    content = f"bump: {bump}\n{note}\n"
    written = _atomic_write(path, content)
    if written.is_err:
        _log.error(
            "release: write_changelog_fragment: %s failed (%s)",
            path,
            written.danger_err,
        )
        return Err(written.danger_err)
    _log.info(
        "release: write_changelog_fragment: %s wrote %s (bump=%s)",
        ticket_id,
        path,
        bump,
    )
    return Ok(path)


def _sort_key(fragment: ChangelogFragment) -> tuple[int, str]:
    """Numeric ticket-id ordering (`T-2` before `T-10`) for a
    reproducible, correctly-ordered assembled changelog -- a lexical sort
    would put `T-10` before `T-2` (T-2445's own acceptance: "correct
    order", not "lexical order"). Falls back to the raw string for a
    ticket id that does not match the usual `T-####` shape (never raises
    on an unexpected id -- this is a sort key, not a validator)."""
    match = _TICKET_ID_RE.match(fragment.ticket_id)
    if match is None:
        return (1 << 62, fragment.ticket_id)
    return (int(match.group(1)), fragment.ticket_id)


def _parse_fragment(path: Path) -> Result[ChangelogFragment, ReleaseError]:
    """One fragment file's content as a `ChangelogFragment`. `Err(
    Malformed)` on anything that does not match the `write_changelog_
    fragment`-written shape (a missing/garbled `bump:` header line, or an
    unreadable file) -- FAIL CLOSED, never silently skipped: a fragment
    this function cannot parse is exactly the kind of entry T-2445's own
    acceptance says a release must not silently drop."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        _log.error("release: _parse_fragment: %s unreadable (%s)", path, exc)
        return Err(ReleaseError.Malformed)
    lines = text.splitlines()
    if not lines:
        return Err(ReleaseError.Malformed)
    header = _FRAGMENT_HEADER_RE.match(lines[0])
    if header is None:
        return Err(ReleaseError.Malformed)
    note = "\n".join(lines[1:]).strip()
    if not note:
        return Err(ReleaseError.Malformed)
    return Ok(
        ChangelogFragment(ticket_id=path.stem, bump=header.group(1).lower(), note=note)
    )


# frob:doc docs/modules/release.md#changelog-fragments-t-2445
# frob:tests tests/test_release.py::TestChangelogFragments.test_read_sorts_numerically_not_lexically  # noqa: E501
# frob:tests tests/test_release.py::TestChangelogFragments.test_read_fails_closed_on_a_malformed_fragment  # noqa: E501
def read_changelog_fragments(
    root: Path,
) -> Result[tuple[ChangelogFragment, ...], ReleaseError]:
    """Every `changelog.d/*.md` fragment under `root`, parsed and sorted
    by numeric ticket id (T-2445). `Ok(())` (empty) when the directory
    does not exist or has no fragments -- "nothing pending" is not an
    error. `Err(Malformed)` propagates the FIRST unparsable fragment
    found rather than skipping it: an assembly step that silently
    dropped a fragment it could not parse would reproduce the exact
    "incomplete changelog" failure mode T-2445's acceptance forbids."""
    directory = fragment_dir(root)
    if not directory.exists():
        return Ok(())
    fragments: list[ChangelogFragment] = []
    for path in sorted(directory.glob("*.md")):
        parsed = _parse_fragment(path)
        if parsed.is_err:
            return Err(parsed.danger_err)
        fragments.append(parsed.danger_ok)
    fragments.sort(key=_sort_key)
    return Ok(tuple(fragments))


#: `re.escape`d-version, non-digit-bounded pattern for locating a
#: `## [version] - ...` heading line -- the SAME anchored-heading match
#: `frob.gates._changelog_mentions`/`frob.release.changelog_skeleton_
#: entry` already use (T-0403 B14's fix, kept independent here rather
#: than imported to avoid a `_fragments` <-> `gates` import coupling).
def _heading_pattern(version: str) -> re.Pattern[str]:
    """The compiled heading-match pattern for `version`, shared by every
    section-locating helper below."""
    return re.compile(r"(?<![0-9.])" + re.escape(version) + r"(?![0-9.])")


def _find_heading_span(lines: list[str], version: str) -> tuple[int, int] | None:
    """`(start, end)` line-index span of `version`'s own `## ...` section
    within `lines` -- `start` is the heading line itself, `end` is the
    index of the NEXT `## ` heading (or `len(lines)` if this is the last
    section) so `lines[start:end]` is exactly the region a regenerate
    call should replace. `None` if no heading for `version` exists yet."""
    pattern = _heading_pattern(version)
    start = next(
        (
            i
            for i, line in enumerate(lines)
            if line.lstrip().startswith("#") and pattern.search(line)
        ),
        None,
    )
    if start is None:
        return None
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")),
        len(lines),
    )
    return start, end


# frob:doc docs/modules/release.md#changelog-fragments-t-2445
# frob:tests tests/test_release.py::TestChangelogFragments.test_assemble_writes_every_fragment_as_a_bullet  # noqa: E501
# frob:tests tests/test_release.py::TestChangelogFragments.test_assemble_is_a_noop_with_no_fragments  # noqa: E501
# frob:tests tests/test_release.py::TestChangelogFragments.test_assemble_is_idempotent_and_picks_up_new_fragments  # noqa: E501
def assemble_changelog_from_fragments(
    root: Path, version: str
) -> Result[int, ReleaseError]:
    """Regenerate `CHANGELOG.md`'s `## [version] - unreleased` section as
    a pure function of every CURRENTLY-PRESENT `changelog.d/*.md`
    fragment (T-2445) -- one bullet per fragment, in the same numeric-
    ticket-id order `read_changelog_fragments` returns.

    UNLIKE `frob.release.changelog_skeleton_entry` (which only ever
    inserts a heading ONCE and is a no-op forever after -- the right
    contract for its own single-note call sites), this REPLACES the
    entire body of `version`'s section every call, so a SECOND land at
    the same still-unreleased `version` correctly grows the bullet list
    to match the larger fragment set instead of silently staying frozen
    at whatever the FIRST land wrote. Still idempotent: calling this
    twice in a row with an unchanged fragment set reproduces byte-
    identical output, so `frob.app.ticket_runner._land_cmd` can call it
    unconditionally on every bump-worthy land under `land.lock` with no
    special-casing for "first land at this version" vs "a later one".

    `Ok(0)` (no-op, `CHANGELOG.md` untouched) when there are no fragments
    at all -- nothing to assemble. `Err(WriteFailed)` on `CHANGELOG.md`
    being absent or the underlying `atomic_write` I/O failure; `Err`
    propagates `read_changelog_fragments`'s own fail-closed parse error
    unchanged."""
    fragments = read_changelog_fragments(root)
    if fragments.is_err:
        return Err(fragments.danger_err)
    entries = fragments.danger_ok
    if not entries:
        return Ok(0)
    path = root / "CHANGELOG.md"
    if not path.exists():
        _log.error(
            "release: assemble_changelog_from_fragments: %s has no CHANGELOG.md "
            "to assemble %d fragment(s) into",
            root,
            len(entries),
        )
        return Err(ReleaseError.WriteFailed)
    # T-2615: `f.note` is written by `write_changelog_fragment` as
    # `f"{ticket_id}: {ticket.title}"` -- it ALREADY carries the ticket id
    # as its own prefix. Prepending `f.ticket_id` again here duplicated it
    # on every rendered bullet (`- T-2593: T-2593: <title>`, 101 released
    # lines carried it as of T-2615's filing). The id is the bullet's own
    # leading token by construction; render `f.note` verbatim.
    body = "".join(f"- {f.note}\n" for f in entries) + "\n"
    new_section = [f"## [{version}] - unreleased\n", "\n", body]
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    span = _find_heading_span(lines, version)
    if span is None:
        insert_at = next(
            (i for i, line in enumerate(lines) if line.startswith("## ")), len(lines)
        )
        lines[insert_at:insert_at] = new_section
    else:
        start, end = span
        lines[start:end] = new_section
    written = _atomic_write(path, "".join(lines))
    if written.is_err:
        _log.error(
            "release: assemble_changelog_from_fragments: %s write failed (%s)",
            path,
            written.danger_err,
        )
        return Err(written.danger_err)
    _log.info(
        "release: assemble_changelog_from_fragments: %s regenerated %s's "
        "section from %d fragment(s)",
        path,
        version,
        len(entries),
    )
    return Ok(len(entries))


def _atomic_write(path: Path, content: str) -> Result[None, ReleaseError]:
    """This module's own copy of `frob.release._atomic_write_release`'s
    translate-to-`ReleaseError` posture -- duplicated rather than
    imported because the source is a leading-underscore private symbol
    of the `frob.release` package `__init__` this module already imports
    PUBLIC names from; kept to one line of actual logic so the
    duplication is cheap to keep in sync."""
    written = atomic_write(path, content)
    if written.is_err:
        return Err(ReleaseError.WriteFailed)
    return Ok(None)


__all__ = [
    "FRAGMENT_DIR_NAME",
    "ChangelogFragment",
    "assemble_changelog_from_fragments",
    "fragment_dir",
    "fragment_path",
    "read_changelog_fragments",
    "write_changelog_fragment",
]
