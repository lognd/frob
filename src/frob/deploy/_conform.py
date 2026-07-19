"""DEPLOY002/DEPLOY003: bidirectional conformance between committed deploy
scripts' MUTATION SURFACE and the design model's `HostManifest` (T-0258,
deploy epic T-0254).

DEPLOY001 (`_drift.py`) catches a hand-edit by byte-diffing the WHOLE
script against a fresh regeneration. That is gameable in one specific
way: an operator (or an attacker with commit access) can regenerate a
clean script, then hand-append or hand-remove a step, and re-run `frob
deploy generate` never again -- the digest header in the tampered file
would no longer match `manifest_digest`, so DEPLOY001 still fires in that
case, but the FAILURE MESSAGE is only "does not match regeneration",
never "why". This module gives the structural "why": it parses each
committed script's actual MUTATION SURFACE -- the set of
(kind, target) system-mutating operations it performs (`useradd`/
`groupadd`/`userdel`/`groupdel`, `mkdir`/`install`/`cp`, `chown`/
`chmod`, `cat > ... <<EOF` unit-file writes, `rm -f`/`rm -rf`,
`systemctl enable`/`disable`/`start`/`stop`) -- and compares it
bidirectionally against the EXACT set `HostManifest` declares:

- **DEPLOY002** (extra): a mutation the script performs that the
  manifest does not declare -- a smuggled extra user, path, or unit.
  This is the red-team-relevant direction: it fires even when the rest
  of the script is byte-identical to a real regeneration, so bypassing
  `frob deploy generate` and hand-appending one rogue `useradd` still
  fails `frob check`.
- **DEPLOY003** (missing): a manifest entry the script implements no
  mutation for -- an incomplete install (a declared `owns` path never
  `mkdir`/`chown`/`chmod`'d) or incomplete uninstall (a declared
  `runs_as` user never `userdel`'d).

Extraction is STRUCTURED, not a blind grep: each regex is anchored to
the exact check-then-apply command shapes `_generate.py` emits (one
quoted target per mutating command, always the LAST quoted argument on
the line), so heredoc unit-file bodies (`ReadWritePaths=...`,
`Description=...`, unquoted `systemd` directives) never false-positive
as mutations. Reused for BOTH `install.sh` and `uninstall.sh`
independently -- a tamper that only touches one script (e.g. removing
uninstall's `userdel` while leaving install untouched) is caught at the
script it actually touched, not blurred into a single install+uninstall
union.

Wired into `frob check` the same "extra stage, not `frob.gates`'s
pluggable job table" shape DEPLOY001 already uses (`src/frob/gates/**`
stays out of this ticket's `scope`) -- `frob.app.check_runner` calls
`deploy_conformance_violations` directly.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger

from ._drift import _load_current_model
from ._generate import ManifestEntry, _unit_name, sorted_manifest_entries

_log = get_logger(__name__)

#: One mutating-command shape -> a compiled regex whose SOLE capture
#: group is the mutation's target (the last quoted argument on the
#: line) -- the ONE table `extract_mutation_surface` walks, so adding a
#: new recognized command shape never means touching the extraction
#: loop itself, only this table.
_RE_USERADD = re.compile(r'^\s*useradd\b.*"([^"]+)"\s*$')
_RE_USERDEL = re.compile(r'^\s*userdel\s+"([^"]+)"')
_RE_GROUPADD = re.compile(r'^\s*groupadd\b.*"([^"]+)"\s*$')
_RE_GROUPDEL = re.compile(r'^\s*groupdel\s+"([^"]+)"')
_RE_MKDIR = re.compile(r'^\s*mkdir\s+-p\s+"([^"]+)"')
_RE_CHOWN = re.compile(r'^\s*chown\s+"[^"]*":"[^"]*"\s+"([^"]+)"')
_RE_CHMOD = re.compile(r'^\s*chmod\s+"[^"]+"\s+"([^"]+)"')
_RE_INSTALL = re.compile(r'^\s*install\b.*\s"([^"]+)"\s*$')
_RE_CP = re.compile(r'^\s*cp\b.*\s"([^"]+)"\s*$')
_RE_RM = re.compile(r'^\s*rm\s+-r?f\s+"([^"]+)"')
_RE_CAT_HEREDOC = re.compile(r'^\s*cat\s+>\s+"([^"]+)"\s+<<')
_RE_SYSTEMCTL = re.compile(r'^\s*systemctl\s+(?:enable|disable|start|stop)\s+"([^"]+)"')

#: (kind, regex) pairs classified directly (kind is unambiguous from the
#: command itself) -- `_RE_RM`/`_RE_CAT_HEREDOC` are handled separately
#: below since their kind depends on the TARGET path, not the command.
_DIRECT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("user", _RE_USERADD),
    ("user", _RE_USERDEL),
    ("group", _RE_GROUPADD),
    ("group", _RE_GROUPDEL),
    ("path", _RE_MKDIR),
    ("path", _RE_CHOWN),
    ("path", _RE_CHMOD),
    ("path", _RE_INSTALL),
    ("path", _RE_CP),
    ("unit", _RE_SYSTEMCTL),
)


# frob:doc docs/strata/host.md#deploy002deploy003-conformance
class MutationTarget(BaseModel):
    """One system-mutating (kind, target) pair extracted from a script or
    declared by a `HostManifest` -- `kind` is `"user"`, `"group"`,
    `"unit"`, or `"path"`; `target` is the username, group name, systemd
    unit name, or filesystem path the mutation acts on. The single shape
    both `extract_mutation_surface` (script side) and
    `expected_mutation_surface` (manifest side) produce, so the two are
    directly set-comparable."""

    model_config = ConfigDict(frozen=True)

    kind: str
    target: str


def _classify_path(path: str) -> MutationTarget:
    """`rm -f`/`rm -rf` and `cat > ... <<EOF` both act on a bare path --
    this is the ONE place that path is classified as a systemd `"unit"`
    (under `/etc/systemd/system/`, `.service` suffix, matching
    `_generate.py::_unit_file_path`'s exact shape) vs. a plain `"path"`
    mutation, so `extract_mutation_surface`'s two callers of it can never
    classify the same shape two different ways."""
    if path.startswith("/etc/systemd/system/") and path.endswith(".service"):
        return MutationTarget(kind="unit", target=path.rsplit("/", 1)[-1])
    return MutationTarget(kind="path", target=path)


# frob:doc docs/strata/host.md#deploy002deploy003-conformance
# frob:tests tests/unit/deploy/test_conform.py::TestExtract.test_install kind="unit"
# frob:tests tests/unit/deploy/test_conform.py::TestExtract.test_no_heredoc kind="unit"
def extract_mutation_surface(text: str) -> frozenset[MutationTarget]:
    """Parse one script's text into its full `MutationTarget` set: every
    `useradd`/`groupadd`/`userdel`/`groupdel`/`mkdir`/`install`/`cp`/
    `chown`/`chmod`/`rm -f`/`rm -rf`/`systemctl enable|disable|start|
    stop`/unit-file heredoc-write line, matched against the exact
    check-then-apply command shapes `_generate.py` renders (module
    docstring) -- STRUCTURED extraction, not a blind grep: a heredoc unit
    file's own unquoted `systemd` directive lines (`ReadWritePaths=...`,
    `Description=...`) never match any pattern here, so they are never
    mistaken for a script-level mutation."""
    targets: set[MutationTarget] = set()
    for line in text.splitlines():
        matched = False
        for kind, pattern in _DIRECT_PATTERNS:
            m = pattern.match(line)
            if m:
                targets.add(MutationTarget(kind=kind, target=m.group(1)))
                matched = True
                break
        if matched:
            continue
        m = _RE_RM.match(line)
        if m:
            targets.add(_classify_path(m.group(1)))
            continue
        m = _RE_CAT_HEREDOC.match(line)
        if m:
            targets.add(_classify_path(m.group(1)))
            continue
    return frozenset(targets)


# frob:doc docs/strata/host.md#deploy002deploy003-conformance
# frob:tests tests/unit/deploy/test_conform.py::TestExpected.test_from_host kind="unit"
def expected_mutation_surface(
    entries: tuple[ManifestEntry, ...],
) -> frozenset[MutationTarget]:
    """The mutation surface a conformant install/uninstall script pair
    must exactly cover, derived straight from `HostManifest` facts: one
    `("user", <runs_as>)` per declared service user, one
    `("unit", <_unit_name(node_id)>)` per `is_unit`-marked entry (the
    SAME naming rule `_generate.py` renders scripts with -- never an
    independently re-derived name), and one `("path", <path>)` per
    declared `owns` entry."""
    targets: set[MutationTarget] = set()
    for entry in entries:
        if entry.manifest.runs_as is not None:
            targets.add(MutationTarget(kind="user", target=entry.manifest.runs_as))
        if entry.manifest.is_unit:
            targets.add(MutationTarget(kind="unit", target=_unit_name(entry.node_id)))
        for owns in entry.manifest.owns:
            targets.add(MutationTarget(kind="path", target=owns.path))
    return frozenset(targets)


# frob:doc docs/strata/host.md#deploy002deploy003-conformance
class ConformanceViolation(BaseModel):
    """One DEPLOY002 (script mutation not declared in the manifest) or
    DEPLOY003 (manifest entry no script mutation implements) finding,
    reported with the exact file/kind/target so the fix is unambiguous:
    either add the missing manifest declaration / regenerate (DEPLOY003),
    or remove the unauthorized script mutation (DEPLOY002)."""

    model_config = ConfigDict(frozen=True)

    code: str
    file: str
    kind: str
    target: str
    message: str


def _script_conformance(
    filename: str, text: str, declared: frozenset[MutationTarget]
) -> list[ConformanceViolation]:
    """DEPLOY002 (extras) + DEPLOY003 (misses) for one script's
    `extract_mutation_surface` against the manifest's `declared` set --
    the one comparison both `install.sh` and `uninstall.sh` are run
    through independently by `deploy_conformance_violations`, so a tamper
    isolated to one script is reported against that script, not
    laundered through a combined install+uninstall union."""
    found = extract_mutation_surface(text)
    violations: list[ConformanceViolation] = []
    for mt in sorted(found - declared, key=lambda t: (t.kind, t.target)):
        _log.error(
            "deploy conformance: deploy/%s mutates %s %r, not declared in "
            "HostManifest (DEPLOY002)",
            filename,
            mt.kind,
            mt.target,
        )
        violations.append(
            ConformanceViolation(
                code="DEPLOY002",
                file=f"deploy/{filename}",
                kind=mt.kind,
                target=mt.target,
                message=(
                    f"deploy/{filename} mutates {mt.kind} {mt.target!r}, which "
                    "is not declared anywhere in the design model's "
                    "HostManifest -- unauthorized/smuggled mutation"
                ),
            )
        )
    for mt in sorted(declared - found, key=lambda t: (t.kind, t.target)):
        _log.error(
            "deploy conformance: HostManifest declares %s %r but deploy/%s "
            "implements no mutation for it (DEPLOY003)",
            mt.kind,
            mt.target,
            filename,
        )
        violations.append(
            ConformanceViolation(
                code="DEPLOY003",
                file=f"deploy/{filename}",
                kind=mt.kind,
                target=mt.target,
                message=(
                    f"HostManifest declares {mt.kind} {mt.target!r} but "
                    f"deploy/{filename} implements no mutation for it -- "
                    "incomplete install/uninstall"
                ),
            )
        )
    return violations


# frob:doc docs/strata/host.md#deploy002deploy003-conformance
# frob:tests tests/unit/deploy/test_conform.py::TestConform.test_clean_pass kind="unit"
# frob:tests tests/unit/deploy/test_conform.py::TestConform.test_no_dir kind="unit"
# frob:tests tests/unit/deploy/test_conform.py::TestConform.test_extra_002 kind="unit"
# frob:tests tests/unit/deploy/test_conform.py::TestConform.test_missing_003 kind="unit"
def deploy_conformance_violations(root: Path) -> tuple[ConformanceViolation, ...]:
    """DEPLOY002/DEPLOY003: every committed `deploy/install.sh` and
    `deploy/uninstall.sh` mutation checked bidirectionally against the
    CURRENT design model's `HostManifest` set (module docstring). Opt-in
    on `deploy/` existing, mirroring DEPLOY001's posture (`_drift.py`);
    returns `()` (clean) when the directory is absent, when no design
    model loads, or when every present script's mutation surface matches
    the manifest exactly in both directions."""
    deploy_dir = root / "deploy"
    if not deploy_dir.is_dir():
        _log.debug("deploy conformance: no deploy/ directory, skipping")
        return ()

    model = _load_current_model(root)
    if model is None:
        return ()

    entries = sorted_manifest_entries(model)
    declared = expected_mutation_surface(entries)

    violations: list[ConformanceViolation] = []
    for filename in ("install.sh", "uninstall.sh"):
        path = deploy_dir / filename
        if not path.exists():
            _log.debug("deploy conformance: %s not committed, skipping", filename)
            continue
        text = path.read_text(encoding="utf-8")
        violations.extend(_script_conformance(filename, text, declared))

    _log.info(
        "deploy conformance: checked %d declared mutation target(s), %d violation(s)",
        len(declared),
        len(violations),
    )
    return tuple(violations)


__all__ = [
    "ConformanceViolation",
    "MutationTarget",
    "deploy_conformance_violations",
    "expected_mutation_surface",
    "extract_mutation_surface",
]
