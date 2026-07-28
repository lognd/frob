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
specifically for an observed outbound HTTP POST to `https://stripe.com/...`
made through a client library) need a first-class capability grammar to
parse targets out of both the declaration and the call site; that is a
surface-grammar follow-up, not a kernel change, exactly as
`_code_binding.py` defers the `code` keyword.

T-0769: the paragraph above used to spell a matching HTTP-client-call
needle literally, which this same file's `net` needle table
(`frob.vet._capability._PATTERNS`) matched as a real observation on THIS
module's own docstring -- a self-inflicted instance of the exact false-
positive class this ticket fixes (docstring prose, not code, T-0769's
module-docstring entry in `frob.vet._capability`). Reworded to describe
the shape without spelling a matching needle, same mitigation precedent as
T-0695's `_concurrency.py` docstring reword.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/strata/_effects.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

from datetime import date
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger
from frob.vet._capability import (
    _PATTERNS,
    is_self_pattern_path,
    language_for,
    non_executable_line_numbers,
)
from frob.vet._capability_modes import (
    CAPABILITY_MODE_KINDS,
    LEGACY_CAPABILITY_ALIASES,
    canonical_declared_kind,
    expand_declared_kind,
    resolve_capability_kind,
)

from ._code_binding import FOREIGN, CodeBinding
from ._models import KernelModel, Node

_log = get_logger(__name__)

#: vet capability-table key -> tier-2 effect kind. net-connect/net-listen/
#: fs-write/fs-read/exec/env-read/env-write are in this ticket's scope
#: (T-0079's title, T-0717/T-0771/T-1075's mode split); eval/ffi/
#: install-hook are vet-specific dependency-vetting signals with no
#: `may`-capability analog yet. T-0717: `fs-write`/`fs-read` normalize to
#: the precise, mode-qualified `fs.write`/`fs.read` spellings
#: (`frob.vet._capability_modes`) instead of the old ambiguous bare `fs`
#: -- `fs-read` is promoted here from `_selfconform.py::_EXTENDED_KINDS`
#: (it now has a real tier-2/THREAT004 analog, closing that module's old
#: SYS100 gap statement for this one kind) so both directions of the
#: fs-read/fs-write join share ONE normalization site instead of two.
#: T-0771 does the same for `net`: the registry's `net-connect`/
#: `net-listen` scanner kinds (T-0771's needle split, `frob.vet.
#: _capability_registry`) now normalize to the precise `net.connect`/
#: `net.listen` spellings and `net` is added to `WIRED_MODE_FAMILIES`
#: (`frob.vet._capability_modes`) so a coarse `may "net"` declaration
#: still covers both -- the old bare `"net": "net"` entry is retired
#: since no registry entry emits the unqualified `"net"` vet-kind anymore
#: (mirrors fs's own retirement of a bare `"fs"` entry). T-1075 does the
#: SAME for `env`: `env-read`/`env-write` normalize to `env.read`/
#: `env.write` and `env` joins `WIRED_MODE_FAMILIES`, promoted here from
#: `_selfconform.py::_EXTENDED_KINDS` (it now has a real tier-2/THREAT004
#: analog, same promotion `fs-read` got); `_selfconform.py`'s own
#: `_UNWIRED_ENV_MODE_ALIASES` transitional fold (which existed only to
#: keep a coarse `may "env"` declaration matching an env-read/env-write
#: observation while no tier-2 join existed) is removed now that this
#: join makes it redundant.
_KIND_MAP: dict[str, str] = {
    "net-connect": "net.connect",
    "net-listen": "net.listen",
    "fs-write": "fs.write",
    "fs-read": "fs.read",
    "exec": "exec",
    "env-read": "env.read",
    "env-write": "env.write",
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
    `.` or `:` (`"net.out:stripe.com"` -> `"net"`, `"exec:*"` -> `"exec"`),
    EXCEPT a T-0717 mode-qualified `family.mode` id (`"fs.read"`,
    `CAPABILITY_MODE_KINDS`) is recognized whole -- its own `.` is the
    family/mode separator, not a target-scoping separator, so it must not
    be split. Only the segment up to a `:` (a target, e.g. `"fs.read:app-
    data"`) is stripped before that whole-id check, so a mode-qualified
    atom WITH a target still resolves correctly."""
    kind_part = atom.split(":", 1)[0]
    if kind_part in CAPABILITY_MODE_KINDS:
        return kind_part
    for sep in (".", ":"):
        if sep in atom:
            return atom.split(sep, 1)[0]
    return atom


def _declared_kinds(node: Node) -> frozenset[str]:
    """Every PRECISE capability kind `node`'s `may` atoms cover (T-0717):
    each atom's raw kind (`_may_kind`) is canonicalized through the legacy-
    alias table (`canonical_declared_kind` -- pure, sunset-independent;
    the sunset ITSELF is a separate gate finding, `check_legacy_capability_
    aliases`) and then expanded (`expand_declared_kind`) -- a precise
    `family.mode` id covers only itself, a bare coarse family name covers
    the UNION of that family's modes (mandate point 2: "a coarse declarer
    answers for everything"). The union across every atom is this node's
    full declared-coverage set, which is what every SYS100/THREAT004
    observed-vs-declared join in this module and `_selfconform.py` reads."""
    declared: set[str] = set()
    for atom in node.may:
        kind = canonical_declared_kind(_may_kind(atom))
        declared |= expand_declared_kind(kind)
    return frozenset(declared)


# frob:doc docs/strata/selfconform.md#fs-read-fs-write
class LegacyCapabilityAliasViolation(BaseModel):
    """One node `may` atom spelled with a T-0717 deprecated legacy
    capability alias (`fs-write`/`fs-read`): `is_error=False` while inside
    the alias's sunset window (a WARNING -- T-0717 acceptance clause 2,
    legacy spellings keep working), `is_error=True` once `today` is on or
    past the alias's sunset date (T-0717 acceptance clause 3 -- a gate
    ERROR)."""

    model_config = ConfigDict(frozen=True)

    node: str
    atom: str
    kind: str
    target: str
    sunset: str
    ticket: str
    is_error: bool


# frob:doc docs/strata/selfconform.md#fs-read-fs-write
# frob:ticket T-0717
# frob:tests tests/unit/strata/test_effects.py::TestLegacyCapabilityAliases kind="unit"
def check_legacy_capability_aliases(
    model: KernelModel, *, today: date | None = None
) -> tuple[LegacyCapabilityAliasViolation, ...]:
    """Every `may` atom across `model`'s nodes spelled with a T-0717
    legacy capability alias (`LEGACY_CAPABILITY_ALIASES`), each resolved
    through `resolve_capability_kind` (which does the actual WARN-vs-ERROR
    sunset decision and logging) -- this is the model-wide GATE surface a
    `frob check`/`frob sys audit` caller wires up to fail a release once an
    alias's sunset has passed (acceptance clause 3), while leaving it a
    visible-but-passing WARNING before that (acceptance clause 2)."""
    found: list[LegacyCapabilityAliasViolation] = []
    for node in model.nodes:
        for atom in node.may:
            kind = _may_kind(atom)
            alias = LEGACY_CAPABILITY_ALIASES.get(kind)
            if alias is None:
                continue
            resolved = resolve_capability_kind(kind, today=today)
            found.append(
                LegacyCapabilityAliasViolation(
                    node=node.id,
                    atom=atom,
                    kind=kind,
                    target=alias.target,
                    sunset=alias.sunset,
                    ticket=alias.ticket,
                    is_error=resolved.is_err,
                )
            )
    _log.info(
        "strata effects: %d legacy capability alias declaration(s) found (%d past "
        "sunset)",
        len(found),
        sum(1 for v in found if v.is_error),
    )
    return tuple(found)


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


def _needle_matches(
    rel: str,
    text: str,
    table: dict[str, tuple[str, ...]],
    non_executable_lines: frozenset[int],
) -> list[ObservedEffect]:
    """Every (line, kind, needle) substring match of `table` against `text`,
    `rel` filled into the `file` field on each `ObservedEffect`. T-0769: a
    line reported in `non_executable_lines` (a comment or python docstring
    line, `frob.vet._capability.non_executable_line_numbers`) is skipped
    entirely -- this is the line-level sibling of the comment/docstring
    exclusion `frob.vet._capability`'s own raw-text scanners already apply;
    before this fix, this function had NO such exclusion at all, so needle
    prose in a `#` comment or docstring (fork/subprocess hazard
    documentation, e.g.) was observed as a real effect."""
    found: list[ObservedEffect] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if lineno in non_executable_lines:
            continue
        for vet_kind, kind in _KIND_MAP.items():
            for needle in table.get(vet_kind, ()):
                if needle in line:
                    found.append(
                        ObservedEffect(file=rel, line=lineno, kind=kind, needle=needle)
                    )
    return found


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
    caller. T-0769: also excludes any line `non_executable_line_numbers`
    reports as comment/docstring prose, closing the false-positive class
    that let `_concurrency.py`'s fork/pool-hazard documentation trip
    THREAT004/SYS100 (docstrings) as well as a plain `#:` comment line
    (this function previously had zero comment awareness at all)."""
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
    non_executable_lines = non_executable_line_numbers(path)
    return _needle_matches(rel, text, table, non_executable_lines)


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
    "LegacyCapabilityAliasViolation",
    "ObservedEffect",
    "check_capability_conformance",
    "check_legacy_capability_aliases",
    "extract_effects",
    "node_may_kinds",
]
