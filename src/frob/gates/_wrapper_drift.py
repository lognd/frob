"""WRAP001/WRAP002/WRAP003 (T-4760): derived-wrapper drift.

A scaffolded project's `Makefile` and `make.bat` are generated artefacts
(`frob scaffold apply`, `frob.scaffold._managed`): every target/branch is
a one-line call to `frob run <name>`, and the named entry lives exactly
once, in `frob.toml`'s `[commands]` table (or a frob-native default,
`frob.app.run_runner._NATIVE_DEFAULTS`). This gate is the standing check
that keeps that true after the initial scaffold, the same "generated
artefact vs. hand-edited drift" shape `frob.deploy._drift` already
enforces for deploy scripts:

- WRAP001: a wrapper target's recipe expands more than one command
  inline instead of delegating to `frob run <name>` (or `uv run frob run
  <name>`) alone -- the sequence has exactly one legitimate home, the
  `[commands]` table itself (docs/commands/run.md#relationship-to-
  derived-wrappers), so a second copy inlined into the wrapper is drift.
- WRAP002: a wrapper target names an entry that is neither declared in
  `frob.toml`'s `[commands]` table nor one of the four native-default
  names -- typically an entry `[commands]` used to declare and no longer
  does.
- WRAP003: the Makefile and make.bat managed-block target/branch name
  sets are not equal -- the two wrapper files must offer the same
  surface on every platform.

Only the managed-block region (between the `# frob:managed-block BEGIN
makefile-wrapper-targets ... END` markers, or the make.bat counterpart)
is scanned -- content outside those markers is the repo's own
hand-written bootstrap and is not this gate's concern (mirrors
`frob.scaffold._managed`'s own "only ever touch what is between the
markers" contract).
"""

from __future__ import annotations

import re
from pathlib import Path

from frob.findings import Severity, Violation
from frob.logging import get_logger
from frob.scaffold._managed import _extract_region, _wrapper_entry_names

_log = get_logger(__name__)

__all__ = ["wrapper_drift_gate"]

_MAKEFILE_BLOCK_ID = "makefile-wrapper-targets"
_MAKEBAT_BLOCK_ID = "makebat-wrapper-targets"

#: A one-line delegating recipe: `frob run <name>` or `uv run frob run
#: <name>`, optionally followed by `--dry-run` or other flags -- anything
#: else in a wrapper target's recipe is drift (WRAP001).
_DELEGATING_RECIPE_RE = re.compile(r"^(?:uv run )?frob run \S+.*$")

#: One `<name>:` target header inside the Makefile managed block, and its
#: (single-line) recipe.
_MAKEFILE_TARGET_RE = re.compile(r"^([A-Za-z0-9_.-]+):\s*$\n\t(.*)$", re.MULTILINE)

#: One `if "%1"=="<name>" (...)` branch inside the make.bat managed block.
_MAKEBAT_BRANCH_RE = re.compile(
    r'^if "%1"=="([A-Za-z0-9_.-]+)"\s*\((.*)\)\s*$', re.MULTILINE
)


def _parse_makefile_targets(region: str) -> dict[str, str]:
    """Every `<name>: / \\t<recipe>` pair in the Makefile managed-block
    region, name -> the single recipe line found for it (T-4760)."""
    return {name: recipe for name, recipe in _MAKEFILE_TARGET_RE.findall(region)}


def _parse_makebat_targets(region: str) -> dict[str, str]:
    """Every `if "%1"=="<name>" (<body>)` branch in the make.bat
    managed-block region, name -> its inline body (T-4760)."""
    return {name: body for name, body in _MAKEBAT_BRANCH_RE.findall(region)}


#: The mandatory make.bat exit-code-propagation suffix every generated
#: branch carries (`_makebat_wrapper_block_content`) -- part of the ONE
#: canonical delegating form for a batch branch, not a second command
#: joined by `&`, so it is stripped before the generic single-command
#: check below runs.
_MAKEBAT_EXIT_SUFFIX = " & exit /b %errorlevel%"


def _is_single_delegating_command(recipe: str, *, is_makebat: bool = False) -> bool:
    """Whether `recipe` is exactly one delegating call and nothing else --
    a `&&`/`;`/`&` joining a second command is exactly the "expands two
    steps inline" drift WRAP001 exists to catch. `is_makebat` strips the
    mandatory `& exit /b %errorlevel%` suffix first (T-4760): that `&` is
    part of the one legitimate batch-branch form, not a joined command."""
    recipe = recipe.strip()
    if is_makebat:
        if not recipe.endswith(_MAKEBAT_EXIT_SUFFIX):
            return False
        recipe = recipe[: -len(_MAKEBAT_EXIT_SUFFIX)]
    if any(sep in recipe for sep in ("&&", ";", "&")):
        return False
    return bool(_DELEGATING_RECIPE_RE.match(recipe))


def _known_names(root: Path) -> frozenset[str]:
    """Every name a wrapper target may legitimately reference: declared
    `[commands]` entries plus the four always-invocable native defaults --
    reuses `frob.scaffold._managed._wrapper_entry_names` (the same
    function `apply_managed_blocks` uses to generate the block in the
    first place) rather than re-deriving the name set here (T-4760)."""
    return frozenset(_wrapper_entry_names(root))


def _drift_for_file(
    targets: dict[str, str], known: frozenset[str], *, file: str, is_makebat: bool
) -> list[Violation]:
    """WRAP001 (inline sequence) and WRAP002 (unknown entry) over one
    wrapper file's parsed targets -- the per-file half of
    `wrapper_drift_gate`, shared by the Makefile and make.bat walks so the
    two emit identically shaped findings (T-4760)."""
    unit = "branch" if is_makebat else "target"
    violations: list[Violation] = []
    for name, recipe in sorted(targets.items()):
        if not _is_single_delegating_command(recipe, is_makebat=is_makebat):
            _log.debug("wrapper_drift_gate: %s %s %r inline sequence", file, unit, name)
            violations.append(
                Violation(
                    rule="WRAP001",
                    severity=Severity.ERROR,
                    file=file,
                    line=0,
                    message=(
                        f"{unit} {name!r} expands more than one command inline "
                        f"({recipe!r}); a wrapper {unit} must be a single `frob "
                        "run <name>` call -- the sequence belongs in frob.toml's "
                        "[commands] table (frob scaffold apply regenerates this "
                        f"{unit})"
                    ),
                )
            )
        if name not in known:
            _log.debug("wrapper_drift_gate: %s %s %r unknown entry", file, unit, name)
            violations.append(
                Violation(
                    rule="WRAP002",
                    severity=Severity.ERROR,
                    file=file,
                    line=0,
                    message=(
                        f"{unit} {name!r} names an entry frob.toml's [commands] "
                        "table no longer declares (and it is not a frob-native "
                        "default) -- run frob scaffold apply to regenerate the "
                        "wrapper"
                    ),
                )
            )
    return violations


# frob:doc docs/commands/scaffold.md#the-wrapper-drift-gate-wrap001wrap002wrap003-t-4760  # noqa: E501
# frob:ticket T-4760
def wrapper_drift_gate(root: Path) -> tuple[Violation, ...]:
    """WRAP001/WRAP002/WRAP003 over `root`'s `Makefile`/`make.bat` managed
    wrapper-target blocks (T-4760). Returns no violations when neither
    wrapper file carries the managed block at all -- a project that has
    never run `frob scaffold apply` has nothing generated yet to drift
    from (this gate checks an existing generated artefact for staleness,
    it does not itself require one to exist)."""
    makefile_path = root / "Makefile"
    makebat_path = root / "make.bat"
    makefile_text = (
        makefile_path.read_text(encoding="utf-8") if makefile_path.exists() else ""
    )
    makebat_text = (
        makebat_path.read_text(encoding="utf-8") if makebat_path.exists() else ""
    )

    makefile_region = _extract_region(
        makefile_text, _MAKEFILE_BLOCK_ID, target="Makefile"
    )
    makebat_region = _extract_region(makebat_text, _MAKEBAT_BLOCK_ID, target="make.bat")

    if makefile_region is None and makebat_region is None:
        _log.info(
            "wrapper_drift_gate: %s: no managed wrapper block present, skipping", root
        )
        return ()

    known = _known_names(root)
    makefile_targets = _parse_makefile_targets(makefile_region or "")
    makebat_targets = _parse_makebat_targets(makebat_region or "")
    violations: list[Violation] = [
        *_drift_for_file(makefile_targets, known, file="Makefile", is_makebat=False),
        *_drift_for_file(makebat_targets, known, file="make.bat", is_makebat=True),
    ]

    if makefile_region is not None and makebat_region is not None:
        makefile_names = frozenset(makefile_targets)
        makebat_names = frozenset(makebat_targets)
        if makefile_names != makebat_names:
            only_makefile = sorted(makefile_names - makebat_names)
            only_makebat = sorted(makebat_names - makefile_names)
            violations.append(
                Violation(
                    rule="WRAP003",
                    severity=Severity.ERROR,
                    file="Makefile",
                    line=0,
                    message=(
                        "Makefile and make.bat wrapper target sets differ "
                        f"(only in Makefile: {only_makefile}, only in make.bat: "
                        f"{only_makebat}) -- run frob scaffold apply to "
                        "regenerate both"
                    ),
                )
            )

    return tuple(violations)
