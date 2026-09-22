"""frob.tickets._registry_files -- the append-shared "registry file" class
(T-4650): config-driven paths (default: design/frob.strata,
docs/design/registry/capability-via-ratchet.lock.json,
docs/modules/gates.md, docs/design/registry/check-coverage.yaml) that
nearly every gate ticket must add exactly one line to.

WHY this module exists: the scope lease treats a declared path as
whole-file exclusive -- one in-progress ticket holding any of these four
files made every sibling's `frob ticket scope --add` refuse with
ScopeLeaseConflict and every sibling's land refuse with CrossTicketLeakage
(measured overnight: 5-8 agents serialized on one file, the coordinator
hand-landing with --allow-cross-ticket). A registry file is different from
an ordinary whole-file lease target: many tickets legitimately each add
ONE line to it and never touch any OTHER ticket's line, so the lease/
leakage machinery's "whole file belongs to one ticket at a time" model is
simply the wrong fit for this narrow file class.

This module is the single home for that class: `registry_files` reads the
configured set (or falls back to the documented default), and
`is_additive_diff_text` is the pure half of the CrossTicketLeakage
exemption test -- a registry file is only ever exempted from a
sibling-scope hit while every change to it on this branch is a pure
append; a single deleted/rewritten line (destructive to whatever another
ticket already appended) still refuses, same as any ordinary file. The
actual `git diff` spawn lives in `frob.tickets._land` (see
`_registry_leakage_exempt_paths`), not here -- this module declares no
exec capability of its own, so it adds zero new SELFAUDIT001 surface.
Do not duplicate a second literal list of these paths elsewhere (the
T-3296 FROB_MANAGED_SIDE_EFFECT_PATHS module comment in frob.tickets.
_scope draws the identical "one home, not a second copy" line for its
own file class).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from frob.logging import get_logger

_log = get_logger("frob.tickets")

#: The registry-file default set (T-4650): append-shared paths
#: nearly every gate ticket must add one line to. Overridable per-repo via
#: `[tickets].registry_files` in frob.toml (a list of repo-relative posix
#: paths); this constant is only the fallback when that key is absent,
#: unreadable, or malformed -- never empty, so an unconfigured repo still
#: gets the exemption for the four paths this ticket was filed over.
# frob:ticket T-4650
# frob:doc docs/modules/tickets.md#registry-files-append-shared-t-draft-a62505d4
DEFAULT_REGISTRY_FILES: frozenset[str] = frozenset(
    {
        "design/frob.strata",
        "docs/design/registry/capability-via-ratchet.lock.json",
        "docs/modules/gates.md",
        "docs/design/registry/check-coverage.yaml",
    }
)


# frob:ticket T-4650
# frob:doc docs/modules/tickets.md#registry-files-append-shared-t-draft-a62505d4
def registry_files(root: Path | None) -> frozenset[str]:
    """The repo's configured `[tickets].registry_files` set from
    `frob.toml`, or `DEFAULT_REGISTRY_FILES` when `root` is `None`,
    `frob.toml` is absent/unreadable, or the key is unset/malformed --
    the same fail-open-to-the-documented-default shape
    `frob.tickets._doable._default_milestone` uses for its own
    `[tickets]` key, except the fallback here is never empty (a
    registry-file class that silently vanished on a bad config value
    would resurrect exactly the serialization this ticket fixes)."""
    if root is None:
        return DEFAULT_REGISTRY_FILES
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        return DEFAULT_REGISTRY_FILES
    try:
        with toml_path.open("rb") as handle:
            table = tomllib.load(handle).get("tickets", {})
        value = table.get("registry_files", None)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        _log.warning(
            "tickets: registry_files unreadable in %s (%s), default applied",
            toml_path,
            exc,
        )
        return DEFAULT_REGISTRY_FILES
    if value is None:
        return DEFAULT_REGISTRY_FILES
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        _log.warning(
            "tickets: [tickets].registry_files in %s is %r (not a list of "
            "strings), default applied",
            toml_path,
            value,
        )
        return DEFAULT_REGISTRY_FILES
    return frozenset(str(v) for v in value)


# frob:ticket T-4650
# frob:doc docs/modules/tickets.md#registry-files-append-shared-t-draft-a62505d4
def is_registry_file(path: str, root: Path | None) -> bool:
    """Whether `path` (a repo-relative posix path) is a configured
    registry file (`registry_files`) -- the single membership test every
    registry-file-aware caller uses, so no second, possibly-drifted copy
    of the set is ever consulted."""
    return path in registry_files(root)


# frob:ticket T-4650
# frob:doc docs/modules/tickets.md#registry-files-append-shared-t-draft-a62505d4
def is_additive_diff_text(diff_text: str) -> bool:
    """`True` when a unified `git diff` body contains no removed lines at
    all (a pure append) -- the pure, no-subprocess half of the
    CrossTicketLeakage exemption test for a registry file
    (T-4650 acceptances b/c): a registry file is exempted from
    a sibling-scope hit ONLY while every change to it on this branch is
    additive; a single deleted/rewritten line (destructive to whatever
    another ticket already appended to the same file) still refuses,
    same as any ordinary file.

    Deliberately takes already-fetched diff TEXT rather than running
    `git` itself: this module has no existing `via`-declared exec
    capability of its own, while `frob.tickets._land` (the sole caller,
    through `_registry_leakage_exempt_paths`) already does for its own
    `git diff`/`git diff --name-only` calls -- keeping the subprocess
    spawn there means this new registry-file exemption adds zero new
    exec surface anywhere, rather than duplicating a second `via` grant
    for the exact same capability. Scans for a line starting with a
    single `-` (never `---`, the file-header marker, and never a blank/
    context line)."""
    for line in diff_text.splitlines():
        if line.startswith("-") and not line.startswith("---"):
            return False
    return True
