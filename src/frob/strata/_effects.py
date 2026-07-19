"""strata tier-2 effect extraction: net/fs/exec facts vs `may` capabilities
(docs/strata/surface.md#code-binding-tier-2-v0-implementation, T-0079).

This is the capability half of tier-2 conformance, the sibling check to
`_code_binding.py::check_import_conformance` (imports): where import
conformance joins declared `Flow`s against real cross-component imports,
`check_capability_conformance` joins declared `Node.may` capability atoms
against real net/fs/exec effects observed in a node's own bound code.
Same deny-by-default posture (charter law 2): an observed effect with no
matching `may` declaration is a violation with file/line evidence, not a
silent pass.

Detection reuses `frob.vet._capability`'s per-language pattern tables
(`_PATTERNS`, `language_for`) rather than duplicating them -- those tables
already encode the net/fs-write/exec substring vocabulary for
python/typescript/rust (docs/modules/vet.md "Capability taxonomy"). This
module adds the one thing `frob.vet` does not need: line numbers, since a
dependency-vetting capability scan only needs a file-level yes/no while a
kernel violation needs file:line evidence like every other strata report.

The `may` capability grammar is not yet finalized in the surface language
(`docs/strata/surface.md`'s `comp_item := ... | "may" capability` leaves
`capability` unspecified, same deferral `_code_binding.py` notes for the
`code` keyword). v0 treats a `may` atom's leading segment up to the first
`.` or `:` as its capability KIND (`"net.out:stripe.com"` -> `"net"`,
matching the existing `may` docstring example in `_models.py::Node`) and
joins on kind only -- a node with any `may` atom of kind `net` is allowed
any net-effect anywhere in its bound code, a node with none is not. Finer
joins (destination-scoped, e.g. requiring `net.out:stripe.com`
specifically for an observed `requests.post("https://stripe.com/...")`)
need a first-class capability grammar to parse targets out of both the
declaration and the call site; that is a surface-grammar follow-up, not a
kernel change, exactly as `_code_binding.py` defers the `code` keyword.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger
from frob.vet._capability import _PATTERNS, is_self_pattern_path, language_for

from ._code_binding import FOREIGN, CodeBinding
from ._models import KernelModel, Node

_log = get_logger(__name__)

#: vet capability-table key -> tier-2 effect kind. Only net/fs/exec are in
#: this ticket's scope (T-0079's title); eval/env/ffi/install-hook are vet-
#: specific dependency-vetting signals with no `may`-capability analog yet.
_KIND_MAP: dict[str, str] = {
    "net": "net",
    "fs-write": "fs",
    "exec": "exec",
}


# frob:doc docs/strata/surface.md#code-binding-tier-2-v0-implementation
class ObservedEffect(BaseModel):
    """One net/fs/exec effect substring observed at `file`:`line`."""

    model_config = ConfigDict(frozen=True)

    file: str
    line: int
    kind: str
    needle: str


# frob:doc docs/strata/surface.md#code-binding-tier-2-v0-implementation
class CapabilityViolation(BaseModel):
    """One observed effect with no matching `may` declaration on its owning node."""

    model_config = ConfigDict(frozen=True)

    file: str
    line: int
    kind: str
    component: str
    needle: str


# frob:doc docs/strata/surface.md#code-binding-tier-2-v0-implementation
class EffectReport(BaseModel):
    """Every tier-2 capability-conformance violation, in file-then-line order."""

    model_config = ConfigDict(frozen=True)

    violations: tuple[CapabilityViolation, ...] = ()


def _may_kind(atom: str) -> str:
    """The capability KIND of one `may` atom: the segment before the first
    `.` or `:` (`"net.out:stripe.com"` -> `"net"`, `"exec:*"` -> `"exec"`)."""
    for sep in (".", ":"):
        if sep in atom:
            return atom.split(sep, 1)[0]
    return atom


def _declared_kinds(node: Node) -> frozenset[str]:
    """Every capability kind `node` declares via its `may` atoms."""
    return frozenset(_may_kind(atom) for atom in node.may)


# frob:doc docs/strata/surface.md#code-binding-tier-2-v0-implementation
# frob:tests tests/unit/strata/test_effects.py::TestNodeMayKinds.test_kinds kind="unit"
def node_may_kinds(node: Node) -> frozenset[str]:
    """Public alias of `_declared_kinds`: every capability KIND `node`
    declares via its `may` atoms. Exposed for `frob.deploy` (T-0257),
    which derives a generated systemd unit's `CapabilityBoundingSet=`
    from the SAME kind join `export_seccomp`'s `SystemCallFilter=`
    already uses (`_export.py::node_allowed_syscalls`) -- one join, two
    renderings, never a duplicated `may`-kind derivation."""
    return _declared_kinds(node)


def _line_effects(path: Path, root: Path) -> list[ObservedEffect]:
    """Every net/fs/exec effect needle match in `path`, one per (line, kind)
    pair matched, `path`-relative-to-`root` in the `file` field so reports
    read the same way `_code_binding.py`'s violations do. Excludes
    `is_self_pattern_path` (T-0201): a pattern-catalog data file's needle
    literals are not code exercising the effect, the same self-match class
    `frob.vet._capability`'s own directory aggregation already excludes --
    without this, `_cve_fingerprint.py`'s `CveFingerprint.needles` table
    trivially "observes" every fs needle it stores as a literal string.
    `root` (T-0253) doubles as `is_self_pattern_path`'s scan-target
    discriminator: self-conformance always passes frob's own repo root
    here, so the exclusion fires exactly when it always has for this
    caller."""
    if is_self_pattern_path(path, root):
        return []
    language = language_for(path)
    if language is None:
        return []
    table = _PATTERNS[language]
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        _log.warning("strata effects: could not read %s: %s", path, exc)
        return []

    rel = path.relative_to(root).as_posix()
    found: list[ObservedEffect] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for vet_kind, kind in _KIND_MAP.items():
            for needle in table.get(vet_kind, ()):
                if needle in line:
                    found.append(
                        ObservedEffect(file=rel, line=lineno, kind=kind, needle=needle)
                    )
    return found


def _sorted_owned_files(binding: CodeBinding) -> list[str]:
    """Every non-`FOREIGN` bound file path, in deterministic order (hoisted
    out of the loops below so the sort runs once, not per iteration --
    mirrors `_code_binding.py::_sorted_owned_files`)."""
    all_files = sorted(binding.owner)
    return [rel for rel in all_files if binding.owner[rel] != FOREIGN]


# frob:doc docs/strata/surface.md#code-binding-tier-2-v0-implementation
def extract_effects(binding: CodeBinding, root: Path) -> tuple[ObservedEffect, ...]:
    """Every net/fs/exec effect observed in every non-`FOREIGN` bound file
    under `root`, in `binding.owner`'s deterministic (sorted-path) order.

    `FOREIGN` files are skipped: like `check_import_conformance`, an
    unclassified file names no kernel node to attest a capability against
    (docs/strata/surface.md#code-binding-tier-2-v0-implementation, same
    v0 scope cut as tier-2 import conformance).
    """
    effects: list[ObservedEffect] = []
    for rel in _sorted_owned_files(binding):
        effects.extend(_line_effects(root / rel, root))
    _log.info("strata effects: %d effect(s) observed under %s", len(effects), root)
    return tuple(effects)


def _file_capability_violations(
    rel: str, owner: str, kinds: frozenset[str], root: Path
) -> list[CapabilityViolation]:
    """Every undeclared-capability effect inside one bound file `rel`."""
    found: list[CapabilityViolation] = []
    for effect in _line_effects(root / rel, root):
        if effect.kind in kinds:
            continue
        _log.warning(
            "strata effects: undeclared capability effect %s:%d %s (%s) on %s",
            effect.file,
            effect.line,
            effect.kind,
            effect.needle,
            owner,
        )
        found.append(
            CapabilityViolation(
                file=effect.file,
                line=effect.line,
                kind=effect.kind,
                component=owner,
                needle=effect.needle,
            )
        )
    return found


# frob:doc docs/strata/surface.md#code-binding-tier-2-v0-implementation
def check_capability_conformance(
    model: KernelModel, binding: CodeBinding, root: Path
) -> EffectReport:
    """Every observed net/fs/exec effect in `binding`'s bound code whose
    owning node declares no `may` atom of the matching capability kind --
    "undeclared capability effect" (T-0079), deny-by-default exactly like
    `check_import_conformance`'s undeclared-import join."""
    declared: dict[str, frozenset[str]] = {
        node.id: _declared_kinds(node) for node in model.nodes
    }
    violations: list[CapabilityViolation] = []
    for rel in _sorted_owned_files(binding):
        owner = binding.owner[rel]
        violations.extend(
            _file_capability_violations(
                rel, owner, declared.get(owner, frozenset()), root
            )
        )
    return EffectReport(violations=tuple(violations))


__all__ = [
    "CapabilityViolation",
    "EffectReport",
    "ObservedEffect",
    "check_capability_conformance",
    "extract_effects",
    "node_may_kinds",
]
