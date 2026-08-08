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

from __future__ import annotations

import fnmatch
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    # T-1627: `frob.lang` is imported lazily at runtime (module-load-cycle
    # note on `_symbols_for_file`) but the static checker still needs a
    # real type for `RawSymbol.qualname`/`.span` accesses in this module,
    # not the loose `tuple[object, ...]` those two functions carry at
    # runtime for that same import-cycle reason.
    from frob.lang import RawSymbol

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


# frob:ticket T-1627
def _via_glob_and_symbol(entry: str) -> tuple[str, str | None]:
    """Split one `via` entry into its (file-glob, symbol-qualname-or-None)
    parts (T-1627): `"src/x.py"` (the pre-T-1627 whole-file shape) splits
    to `("src/x.py", None)`; `"src/x.py::run"` (symbol-form) splits to
    `("src/x.py", "run")`. `"::"` rather than a single `:` because a
    capability-atom-style target suffix already uses bare `:`
    (`"net.out:stripe.com"`) elsewhere in this grammar -- reusing that
    separator for the file/symbol split would be ambiguous. Only the
    FIRST `::` splits: a qualname itself may contain further `.`/`::`-free
    dotted segments (`Class.method`) that stay inside the symbol part
    untouched."""
    glob, sep, symbol = entry.partition("::")
    return (glob, symbol if sep else None)


# frob:ticket T-1627
def _via_matches(rel: str, via: tuple[str, ...]) -> bool:
    """`True` if `rel` (a binding-relative file path) matches at least one
    glob in `via` (T-1440), same `fnmatch.fnmatch` matcher `_code_binding.py`
    already uses for a node's own `code` globs -- one shared matching
    convention across both the node-level and grant-level glob surfaces.

    T-1627: a symbol-form via entry (`"glob::symbol"`) still matches here
    on its glob half alone -- this function answers "does `rel` fall
    inside this grant's FILE surface at all", which is what `_selfconform.
    py`'s per-file joins (unaware of symbols) still need; the stricter
    per-SYMBOL join a capability observation needs is `_via_matches_site`,
    below, not this function."""
    return any(fnmatch.fnmatch(rel, _via_glob_and_symbol(glob)[0]) for glob in via)


# frob:ticket T-1627
def _via_matches_site(rel: str, symbol: str | None, via: tuple[str, ...]) -> bool:
    """`True` if `rel`:`symbol` (T-1627: `symbol` is the qualname of the
    innermost declaration enclosing the observation site, or `None` if the
    site sits outside every declared symbol -- module level) is covered by
    at least one entry in `via`.

    A file-form entry (no `::`) covers every symbol in a matching file,
    exactly like pre-T-1627 `_via_matches` -- this is the backward-
    compatible half (docs/strata/surface.md#may-scope migration note). A
    symbol-form entry (`"glob::qualname"`) covers only an observation
    whose enclosing `symbol` IS `qualname` or is NESTED inside it
    (`symbol == qualname` or `symbol.startswith(qualname + ".")`, so a
    closure or nested `def` declared inside the granted function still
    counts as "at that site", not as an escape from it) -- an observation
    with `symbol=None` (module level, outside every declaration) never
    matches a symbol-form entry, since there is no symbol identity to
    compare against a bare top-level effect."""
    for entry in via:
        glob, want_symbol = _via_glob_and_symbol(entry)
        if not fnmatch.fnmatch(rel, glob):
            continue
        if want_symbol is None:
            return True
        if symbol is None:
            continue
        if symbol == want_symbol or symbol.startswith(want_symbol + "."):
            return True
    return False


# frob:doc docs/strata/surface.md#may-scope
# frob:ticket T-1440
# frob:tests \
# tests/unit/strata/test_effects.py::TestScopedMayViaConformance.test_observation_outsi\
# de_via_surface_is_a_violation kind="unit"
# frob:waive COV007 reason="T-1636: docs/strata/surface.md's may-scope section \
# (T-1440) names this exact private per-file join function BY NAME \
# ('_effects.py::_declared_kinds_for_file') in its own prose -- same T-0524/T-0529 \
# per-function architecture-doc precedent every other COV007 waiver in this repo \
# already carries, not accidental drift onto a private helper"
def _declared_kinds_for_file(node: Node, rel: str) -> frozenset[str]:
    """The precise capability kinds `node` declares that actually COVER
    `rel` (T-1440's per-file SYS100 join): a grant with no `via` (the
    pre-T-1440 shape, and the shape every legacy-constructed `Node` with an
    empty `may_grants` still has) covers every file, exactly like
    `_declared_kinds`; a grant WITH `via` covers only a file matching one of
    its globs. `node.may_grants` empty entirely (a `Node` built directly,
    bypassing the parser -- most unit-test fixtures) falls back to
    `_declared_kinds`'s whole-node join unconditionally, so this is a
    strict narrowing of that join, never a behavior change for anything
    that predates T-1440."""
    if not node.may_grants:
        return _declared_kinds(node)
    declared: set[str] = set()
    for grant in node.may_grants:
        if grant.via and not _via_matches(rel, grant.via):
            continue
        kind = canonical_declared_kind(_may_kind(grant.atom))
        declared |= expand_declared_kind(kind)
    return frozenset(declared)


# frob:ticket T-1627
def _declared_kinds_for_effect(
    node: Node, rel: str, symbol: str | None
) -> frozenset[str]:
    """The precise capability kinds `node` declares that cover an
    observation at `rel`, enclosed by `symbol` (T-1627's per-SYMBOL SYS100
    join, the sibling of `_declared_kinds_for_file`'s per-FILE join): a
    grant with no `via` covers everything, exactly like
    `_declared_kinds_for_file`; a file-form `via` entry covers every
    symbol in a matching file (unchanged migration behavior); a
    symbol-form `via` entry (`"glob::qualname"`) covers ONLY an
    observation whose `symbol` is `qualname` or nested inside it
    (`_via_matches_site`) -- an effect sitting anywhere else in that same
    file, even one line away, is no longer covered, which is the whole
    point of naming a symbol instead of a file. `node.may_grants` empty
    falls back to `_declared_kinds`'s whole-node join, same as
    `_declared_kinds_for_file`."""
    if not node.may_grants:
        return _declared_kinds(node)
    declared: set[str] = set()
    for grant in node.may_grants:
        if grant.via and not _via_matches_site(rel, symbol, grant.via):
            continue
        kind = canonical_declared_kind(_may_kind(grant.atom))
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


# frob:ticket T-1627
def _node_has_symbol_form_via(node: Node) -> bool:
    """`True` if any of `node`'s grants declares a symbol-form via entry
    (T-1627: an entry containing `"::"`) -- gates whether
    `_file_capability_violations` bothers paying for a real parse of each
    of the node's files to resolve enclosing symbols. A node with only
    file-form (or no) `via` entries never needs per-symbol resolution, so
    this keeps the pre-T-1627 file-only join's cost unchanged for every
    design that has not adopted symbol-form `via` yet."""
    return any("::" in entry for grant in node.may_grants for entry in grant.via)


# frob:ticket T-1627
def _enclosing_symbol(line: int, symbols: tuple[object, ...]) -> str | None:
    """Qualname of the deepest (narrowest-span) symbol whose 1-based
    inclusive line-range contains `line`, or `None` if none does (T-1627).

    Deliberately a small LOCAL reimplementation of `frob.lang._common.
    _find_enclosing_symbol`'s narrowest-span search rather than an import
    of it: that helper is a private module of a DIFFERENT package
    (`frob.lang`), and this ticket's declared scope does not include
    `src/frob/lang/**` -- reaching into another package's private surface
    from outside it would be a real architecture violation, not a style
    nit, and widening scope to add one public wrapper function belongs to
    a separate ticket, not folded silently into this one. The search
    itself is ~5 lines with no shared state to desync (RawSymbol's
    `.span`/`.qualname` fields are the only two ever forwarded to it,
    each read via a defensive `getattr` here rather than a `RawSymbol`
    type import at runtime, so this one small helper stays free of the
    `frob.lang` import-cycle concern `_symbols_for_file` documents for
    itself -- `symbols` is typed loosely as `tuple[object, ...]` for
    exactly that reason, unlike `_symbols_for_file`'s own return type,
    which IS `RawSymbol`-typed under `TYPE_CHECKING`)."""
    best_qualname: str | None = None
    best_width: int | None = None
    for sym in symbols:
        span = getattr(sym, "span", None)
        qualname = getattr(sym, "qualname", None)
        if span is None or qualname is None:
            continue
        start, end = span
        if start <= line <= end:
            width = end - start
            if best_width is None or width < best_width:
                best_width = width
                best_qualname = qualname
    return best_qualname


# frob:ticket T-1627
def _symbols_for_file(root: Path, rel: str) -> tuple[RawSymbol, ...]:
    """Every `RawSymbol` declared in `root / rel`, or `()` on any parse
    failure (T-1627): a file that fails to parse degrades to "no symbol
    resolved" for every effect in it, which `_via_matches_site` already
    treats as "does not match a symbol-form via entry" -- fail CLOSED
    (the observation stays undeclared) rather than silently trusting an
    unparseable file's symbol-form grants. Imports `frob.lang` lazily to
    avoid a module-load-time cycle (`frob.lang` -> `frob.check._memo` ->
    ... -> `frob.strata` in some call orders; every other `frob.strata`
    call site that needs `frob.lang` does the same lazy import) -- the
    RETURN type is still resolvable statically via the `TYPE_CHECKING`
    import above, only the runtime import is deferred."""
    from frob.lang import parse_file

    result = parse_file(root / rel)
    if result.is_err:
        _log.warning(
            "strata effects: could not parse %s for symbol-form via resolution: %s",
            rel,
            result.danger_err,
        )
        return ()
    return result.danger_ok.symbols


# frob:ticket T-1627
def _file_capability_violations(
    rel: str, owner: str, node: Node | None, root: Path
) -> list[CapabilityViolation]:
    """Every undeclared-capability effect inside one bound file `rel`,
    joined per-EFFECT against `node`'s grants (T-1627's per-symbol SYS100
    join, generalizing T-1440's per-file join): each effect's enclosing
    symbol is resolved via `frob.lang` ONLY when `node` actually declares
    a symbol-form `via` entry somewhere (`_node_has_symbol_form_via`) --
    otherwise every effect resolves with `symbol=None`, which
    `_declared_kinds_for_effect`'s file-form/via-less branches never
    consult, so a design with no symbol-form `via` pays no parse cost
    beyond what T-1440 already paid."""
    found: list[CapabilityViolation] = []
    no_kinds: frozenset[str] = frozenset()
    needs_symbols = node is not None and _node_has_symbol_form_via(node)
    symbols = _symbols_for_file(root, rel) if needs_symbols else ()
    for effect in _line_effects(root / rel, root):
        symbol = _enclosing_symbol(effect.line, symbols) if symbols else None
        kinds = (
            no_kinds if node is None else _declared_kinds_for_effect(node, rel, symbol)
        )
        if effect.kind in kinds:
            continue
        _log.warning(
            "strata effects: undeclared capability effect %s:%d %s (%s) on %s%s",
            effect.file,
            effect.line,
            effect.kind,
            effect.needle,
            owner,
            f" in {symbol}" if symbol else "",
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
# frob:doc docs/strata/surface.md#may-scope
# frob:ticket T-1455
# frob:ticket T-1627
def check_capability_conformance(
    model: KernelModel, binding: CodeBinding, root: Path
) -> EffectReport:
    """Every observed net/fs/exec effect in `binding`'s bound code whose
    owning node declares no `may` grant covering BOTH the matching
    capability kind AND that specific observation SITE -- "undeclared
    capability effect" (T-0079), deny-by-default exactly like
    `check_import_conformance`'s undeclared-import join.

    T-1440: the join is per-FILE, not per-node. T-1627: for a node with at
    least one symbol-form `via` entry, the join narrows FURTHER to
    per-SYMBOL -- `_declared_kinds_for_effect` (via
    `_file_capability_violations`) narrows a grant's coverage per its
    `via` glob(s) AND, when an entry names a symbol, per that symbol's own
    enclosing scope, so an observation in a file (or, T-1627, a different
    function of the SAME file) outside every `via` surface stays a
    violation even though the node nominally holds the capability
    elsewhere (acceptance clause 0), while a via-less grant (or a node
    with no `may_grants` at all, the legacy/direct-construction shape)
    still covers every file exactly as before (acceptance clause 1)."""
    nodes_by_id: dict[str, Node] = {node.id: node for node in model.nodes}
    violations: list[CapabilityViolation] = []
    for rel in _sorted_owned_files(binding):
        owner = binding.owner[rel]
        node = nodes_by_id.get(owner)
        violations.extend(_file_capability_violations(rel, owner, node, root))
    return EffectReport(violations=tuple(violations))


# frob:doc docs/strata/surface.md#may-scope
# frob:ticket T-1627
class StaleViaSymbolViolation(BaseModel):
    """One symbol-form `via` entry (T-1627) whose named symbol could not be
    found in any file matching its glob under the node's own bound code:
    the grant points at a symbol that has been renamed, moved, or deleted.
    This is DELIBERATELY its own violation kind, never folded into
    `CapabilityViolation` or silently dropped -- a `via` naming a symbol
    that no longer exists reads as a deliberate, narrow grant while
    actually authorizing NOTHING (every real effect in that file now
    falls outside every via surface and is separately flagged as
    undeclared) or, worse, is silently treated as unscoped by a careless
    reader. `frob sys audit`/`frob check` wires this to its own rule id
    (SYS109, docs/modules/gates.md) rather than reusing SYS100's, so a
    stale declaration is diagnosed as EXACTLY that -- not as a generic
    undeclared-capability finding whose real cause (a dangling
    declaration, not a missing one) would be invisible in the message."""

    model_config = ConfigDict(frozen=True)

    node: str
    atom: str
    via: str


# frob:doc docs/strata/surface.md#may-scope
# frob:ticket T-1627
# frob:tests \
# tests/unit/strata/test_effects.py::TestStaleViaSymbol.test_unresolvable_symbol_is_fla\
# gged kind="unit"
def check_stale_via_symbols(
    model: KernelModel, binding: CodeBinding, root: Path
) -> tuple[StaleViaSymbolViolation, ...]:
    """Every symbol-form `via` entry across `model`'s nodes whose named
    symbol resolves to NOTHING in the node's own bound files (T-1627): for
    each grant's symbol-form entries, every non-`FOREIGN` bound file
    matching the entry's glob is parsed (`_symbols_for_file`) and checked
    for a `RawSymbol` whose qualname is the entry's symbol or nests inside
    it (`_via_matches_site`'s own containment rule, reused so "resolves"
    means exactly what "covers an effect" means); if NO file under the
    node's binding matching that glob declares a symbol matching the
    entry, the entry is stale. A glob matching zero files at all (a typo'd
    path, or a file the node no longer binds) is stale by the same rule --
    zero candidate files trivially contain zero matching symbols."""
    found: list[StaleViaSymbolViolation] = []
    owned_by_node: dict[str, list[str]] = {}
    for rel in _sorted_owned_files(binding):
        owned_by_node.setdefault(binding.owner[rel], []).append(rel)
    for node in model.nodes:
        for grant in node.may_grants:
            for entry in grant.via:
                glob, symbol = _via_glob_and_symbol(entry)
                if symbol is None:
                    continue
                owned = owned_by_node.get(node.id, ())
                candidates = [rel for rel in owned if fnmatch.fnmatch(rel, glob)]
                resolved = any(
                    qualname == symbol or qualname.startswith(symbol + ".")
                    for rel in candidates
                    for qualname in (s.qualname for s in _symbols_for_file(root, rel))
                )
                if resolved:
                    continue
                _log.warning(
                    "strata effects: stale via symbol on node %s atom %s: %s does not "
                    "resolve against %d candidate file(s)",
                    node.id,
                    grant.atom,
                    entry,
                    len(candidates),
                )
                found.append(
                    StaleViaSymbolViolation(node=node.id, atom=grant.atom, via=entry)
                )
    _log.info("strata effects: %d stale via-symbol violation(s) found", len(found))
    return tuple(found)


__all__ = [
    "CapabilityViolation",
    "EffectReport",
    "LegacyCapabilityAliasViolation",
    "ObservedEffect",
    "StaleViaSymbolViolation",
    "check_capability_conformance",
    "check_legacy_capability_aliases",
    "check_stale_via_symbols",
    "extract_effects",
    "node_may_kinds",
]
