"""ROOT001: a repo-root top-level directory with zero code references
(docs/modules/gates.md#root001-t-1784).

T-1611 classification history: the `agents/`/`skills/` root directories
were audited TWICE with opposite verdicts. The first pass (T-1767)
concluded KEEP, reading the tracked `SKILL.md` files' prose as "empirically
confirmed live-read" because it happened to match this very repo's own
system-prompt role definitions near-verbatim -- a coincidence of AUTHORSHIP
(the harness's real `~/.claude/agents`/`~/.claude/skills` were almost
certainly seeded FROM these files at some point), misread as proof of a
LIVE LOAD PATH. The second pass (T-1772) corrected it with a mechanical
check: `git grep` across `src/frob/**` for `agents/`/`skills/` path
references returns nothing, `pyproject.toml` packages `src/` only, and
`frob scaffold` does not emit either directory -- nothing in this repo's
OWN code reads either tree. Deleted.

Nothing mechanized that second, correct verification -- it was manual and
ad hoc, so the same wrong "must be live, the names match" read can recur on
the next repo-root directory someone audits. This gate is that
mechanization: for every repo-root top-level directory that is not
`src/`/`tests/`/`.git/`, not on the small explicit allowlist below, and not
referenced by a Makefile-invoked script, at least one of four checks must
hold, or the directory is flagged (surfaced, never auto-deleted):

  (a) `src/frob/**` references the directory's name literally (as a
      `"name/"`-shaped path token) -- covers both real code paths AND
      `frob.scaffold`'s own template/data assets, since both live under
      `src/frob/**` and this check scans every tracked file there, not
      just `.py` sources.
  (b) `pyproject.toml`'s own text references the directory's name --
      packaging/data-files config lives there.
  (c) an explicit `<!-- frob:external-reader dir="name" reason="..." -->`
      declaration exists in any tracked markdown file -- a real, checkable
      claim that some process OUTSIDE this repo's own code reads it (the
      harness-config case), instead of an inferred one.

A directory satisfying none of these is flagged: the next audit starts
from a measured "zero code references" fact instead of re-deriving it from
scratch and getting fooled by name-matching again, the way T-1767 did.
"""
# frob:ticket T-1784

from __future__ import annotations

import re
from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.gates._tracked_files import tracked_files as _tracked_files
from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = ["root_asset_dir_gate"]

#: Directories a repo-root scan must never flag regardless of reference
#: evidence -- the two structural code/test roots every check in this
#: gate family already treats specially, plus the ticket's own named
#: allowlist of directories with a well-understood, non-code purpose
#: (documentation, the ticket ledger, the strata design tree).
_STRUCTURAL_EXEMPT = frozenset({"src", "tests"})
_NAMED_ALLOWLIST = frozenset({"docs", "tickets", "design"})

#: `<!-- frob:external-reader dir="NAME" reason="..." -->` -- the one
#: doc-side directive shape this gate recognizes for check (c). Mirrors
#: the `frob:waive`/`frob:debt` directive comment shape used elsewhere in
#: this repo, deliberately kept to a single regex rather than routed
#: through the full `frob.graph.dsl` edge machinery -- a repo-root
#: directory audit is rare enough (a few times a year, per T-1611) that a
#: dedicated DSL edge kind is not worth the maintenance surface; promoting
#: it there is a reasonable follow-up if that changes.
_EXTERNAL_READER_RE = re.compile(r'frob:external-reader\s+dir="([^"]+)"')


def _top_level_dirs(tracked: tuple[str, ...]) -> frozenset[str]:
    """The set of repo-root top-level directory names that own at least
    one TRACKED file -- an untracked/empty directory carries no git
    history to reason about and is out of this gate's scope, matching the
    git-less-target contract every other tracked-file-driven gate in this
    package already follows (docs/modules/gates.md#git-less-target-contract-t-0705)."""
    names: set[str] = set()
    for path in tracked:
        head, sep, _ = path.partition("/")
        if sep and head:
            names.add(head)
    return frozenset(names)


def _makefile_referenced_names(
    root: Path, candidates: frozenset[str]
) -> frozenset[str]:
    """Candidate directory names that appear literally in the repo-root
    `Makefile`'s text -- the ticket's own "scripts a Makefile target
    actually invokes, etc." exemption clause. Degrades to an empty set
    (no exemptions from this source) if there is no Makefile."""
    makefile_path = root / "Makefile"
    try:
        text = makefile_path.read_text(encoding="utf-8")
    except OSError:
        return frozenset()
    return frozenset(name for name in candidates if name in text)


def _referenced_in_src(root: Path, tracked: tuple[str, ...], name: str) -> bool:
    """Check (a): does any tracked file under `src/frob/**` contain
    `name` as a `"name/"`-shaped literal path token? Scans every tracked
    file under that prefix, not only `.py` sources, so `frob.scaffold`'s
    own non-Python template/data assets (check (c) in the module
    docstring) are covered by the same pass."""
    needle_variants = (f"{name}/", f'"{name}"', f"'{name}'")
    for rel in tracked:
        if not rel.startswith("src/frob/"):
            continue
        try:
            text = (root / rel).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(variant in text for variant in needle_variants):
            return True
    return False


def _referenced_in_pyproject(root: Path, name: str) -> bool:
    """Check (b): does `pyproject.toml`'s own text reference `name`?"""
    pyproject_path = root / "pyproject.toml"
    try:
        text = pyproject_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return name in text


def _external_reader_declared(root: Path, tracked: tuple[str, ...], name: str) -> bool:
    """Check (c): does any tracked markdown file carry an explicit
    `frob:external-reader dir="name"` declaration for `name`?"""
    for rel in tracked:
        if not rel.endswith(".md"):
            continue
        try:
            text = (root / rel).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(match == name for match in _EXTERNAL_READER_RE.findall(text)):
            return True
    return False


# frob:doc docs/modules/gates.md#root001-t-1784
def root_asset_dir_gate(root: Path) -> tuple[Violation, ...]:
    """ROOT001: flag every repo-root top-level directory with zero code
    references -- not `src/`/`tests/`, not on the named allowlist, not
    exempted by a Makefile reference, and satisfying none of the three
    reference checks documented on the module. WARNING severity: this is
    a surfacing gate (per the ticket's own "not auto-deleted, just
    surfaced" posture), never a hard block."""
    tracked = _tracked_files(root, caller="root_asset_dirs")
    if not tracked:
        return ()
    candidates = _top_level_dirs(tracked) - _STRUCTURAL_EXEMPT - _NAMED_ALLOWLIST
    if not candidates:
        return ()
    candidates -= _makefile_referenced_names(root, candidates)
    if not candidates:
        return ()

    violations: list[Violation] = []
    for name in sorted(candidates):
        if _referenced_in_src(root, tracked, name):
            continue
        if _referenced_in_pyproject(root, name):
            continue
        if _external_reader_declared(root, tracked, name):
            continue
        _log.debug("root_asset_dirs: %s has zero code references", name)
        violations.append(
            Violation(
                rule="ROOT001",
                severity=Severity.WARN,
                file=name,
                line=0,
                message=(
                    f"ROOT001: repo-root directory '{name}/' has zero code "
                    "references -- not under src/ or tests/, not on the "
                    "docs/tickets/design allowlist, not referenced by the "
                    "Makefile, not referenced anywhere under src/frob/**, "
                    "not referenced in pyproject.toml, and no "
                    f'<!-- frob:external-reader dir="{name}" reason="..." '
                    "--> declaration names an external process that reads "
                    "it (T-1611/T-1784: this is exactly the shape that "
                    "made agents/ and skills/ look live-read by name-"
                    "matching alone). Either wire a real reference, add "
                    "the external-reader declaration if something outside "
                    "this repo's own code genuinely reads it, or delete it."
                ),
            )
        )
    return tuple(violations)
