# frob:waive LARGE001 reason="T-2826 (T-1651-grade review): the capability-effect \
# checking family (check_capability_conformance/check_stale_via_symbols/ \
# capability_ratchet_violations) all share the same via-glob/via-symbol matching \
# substrate defined once near the top (_via_glob_and_symbol/_via_matches/ \
# _via_matches_site) and the same ObservedEffect/CapabilityViolation models -- three \
# checks over one shared capability-declaration grammar, not independent features. \
# Splitting any one check out would either duplicate the via-matching substrate or \
# leave it importing back from wherever the substrate stayed, the same shared- helper \
# shape T-2829's _new.py/_verify.py waivers already established as not a real seam."
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
import functools
import hashlib
import json
import os
import re
from contextlib import contextmanager
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

from ._code_binding import FOREIGN, CodeBinding, bind_code
from ._models import KernelModel, MayGrant, Node

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
    """One net/fs/exec effect substring observed at `file`:`line`.

    T-1478: `argument` is a best-effort extraction of the first quoted
    string literal appearing on the same line AFTER `needle` (e.g. the
    `"FROB_TOKEN"` in `os.environ["FROB_TOKEN"]`, or the `"cfg.json"` in
    `open("cfg.json")`) -- `None` when no such literal is present (a
    dynamic/computed argument, or a needle with none, e.g. bare `exec`).
    This is a textual heuristic over the SAME line `_needle_matches`
    already scans, not a real parse of the call expression's arguments
    (matching this module's existing needle-substring detection posture,
    docs/strata/surface.md#code-binding-tier-2-v0-implementation's own v0
    scope cut) -- good enough for `of`'s glob join
    (`_of_matches_effect`), not a guarantee of resolving every dynamic
    argument shape."""

    model_config = ConfigDict(frozen=True)

    file: str
    line: int
    kind: str
    needle: str
    argument: str | None = None


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


# frob:ticket T-3458
@functools.lru_cache(maxsize=4096)
def _compiled_via_entries(
    via: tuple[str, ...],
) -> tuple[tuple[re.Pattern[str], str | None], ...]:
    """Precompiled `(glob-regex, symbol-or-None)` pairs for one `via`
    tuple, cached per unique via-list content (T-3458): `_via_matches`/
    `_via_matches_site` are called once per OBSERVATION SITE, and a node's
    via-list can carry 250+ entries (e.g. `testsuite`'s `may "exec" via
    ...`) -- re-deriving/re-splitting/re-translating every entry's glob on
    every call was measured as the dominant cost of `check_capability_
    conformance` (4.5M `fnmatch.fnmatch` calls, ~40s cumulative under
    `test_sys_gate_zero_violations`, with `os.path.normcase` alone
    accounting for ~17s of that -- called once per (via-list, entry, call)
    triple instead of once per call). `via` tuples come from an already-
    parsed, immutable `KernelModel` (never mutated post-parse), so caching
    by the tuple's own value is safe, and identical via-lists shared
    across nodes/grants collapse to one cache entry for free. Each glob is
    `os.path.normcase`'d before `fnmatch.translate`, matching `fnmatch.
    fnmatch`'s own `normcase(name)`-vs-`normcase(pat)` semantics bit for
    bit -- only the PATTERN side's normcase moves here (computed once);
    the NAME side's normcase still happens once per call in the two
    functions below, not per entry."""
    compiled: list[tuple[re.Pattern[str], str | None]] = []
    for entry in via:
        glob, want_symbol = _via_glob_and_symbol(entry)
        pattern = re.compile(fnmatch.translate(os.path.normcase(glob)))
        compiled.append((pattern, want_symbol))
    return tuple(compiled)


# frob:ticket T-1627
def _via_matches(rel: str, via: tuple[str, ...]) -> bool:
    """`True` if `rel` (a binding-relative file path) matches at least one
    glob in `via` (T-1440), same matching semantics `fnmatch.fnmatch`
    gives `_code_binding.py` for a node's own `code` globs -- one shared
    matching convention across both the node-level and grant-level glob
    surfaces, now routed through `_compiled_via_entries`'s cache (T-3458)
    instead of a raw `fnmatch.fnmatch` call per entry.

    T-1627: a symbol-form via entry (`"glob::symbol"`) still matches here
    on its glob half alone -- this function answers "does `rel` fall
    inside this grant's FILE surface at all", which is what `_selfconform.
    py`'s per-file joins (unaware of symbols) still need; the stricter
    per-SYMBOL join a capability observation needs is `_via_matches_site`,
    below, not this function."""
    normalized = os.path.normcase(rel)
    return any(
        pattern.match(normalized) is not None
        for pattern, _want_symbol in _compiled_via_entries(via)
    )


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
    compare against a bare top-level effect. T-3458: iterates
    `_compiled_via_entries(via)`'s cached, precompiled entries instead of
    re-splitting/re-translating each one per call -- same short-circuit
    order and semantics as before, just faster per entry."""
    normalized = os.path.normcase(rel)
    for pattern, want_symbol in _compiled_via_entries(via):
        if pattern.match(normalized) is None:
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
# tests/unit/strata/test_effects.py::TestScopedMayViaConformance.test_observation_outside_via_surface_is_a_violation kind="unit"  # noqa: E501
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


# frob:ticket T-1478
def _of_matches_effect(of: tuple[str, ...], argument: str | None) -> bool:
    """`True` if `grant.of` covers an effect whose extracted `argument` is
    `argument` (T-1478's argument-level join): an empty `of` (the
    pre-T-1478 default) covers every argument, matching `via`'s own
    empty-means-unscoped convention. A non-empty `of` covers ONLY an
    effect whose `argument` matches at least one of its globs
    (`fnmatch`) -- an effect with `argument=None` (no literal could be
    extracted, `_first_string_literal`) never matches a non-empty `of`,
    the same fail-CLOSED posture `_via_matches_site` already takes for an
    unresolvable symbol: a grant narrowed to specific argument VALUES
    must not silently cover an observation whose actual value could not
    even be read."""
    if not of:
        return True
    if argument is None:
        return False
    return any(fnmatch.fnmatch(argument, pattern) for pattern in of)


# frob:ticket T-1627
# frob:ticket T-1478
def _declared_kinds_for_effect(
    node: Node, rel: str, symbol: str | None, argument: str | None = None
) -> frozenset[str]:
    """The precise capability kinds `node` declares that cover an
    observation at `rel`, enclosed by `symbol`, carrying `argument`
    (T-1627's per-SYMBOL SYS100 join, the sibling of
    `_declared_kinds_for_file`'s per-FILE join; T-1478 adds the
    per-ARGUMENT narrowing on top): a grant with no `via` covers every
    file/symbol, exactly like `_declared_kinds_for_file`; a file-form
    `via` entry covers every symbol in a matching file (unchanged
    migration behavior); a symbol-form `via` entry (`"glob::qualname"`)
    covers ONLY an observation whose `symbol` is `qualname` or nested
    inside it (`_via_matches_site`) -- an effect sitting anywhere else in
    that same file, even one line away, is no longer covered, which is
    the whole point of naming a symbol instead of a file. T-1478: ON TOP
    of the site join, a grant's `of` (if non-empty) must ALSO match
    `argument` (`_of_matches_effect`) -- `via` and `of` are independent
    axes (SITE vs VALUE), both must pass for a grant to cover a given
    effect. `node.may_grants` empty falls back to `_declared_kinds`'s
    whole-node join, same as `_declared_kinds_for_file`."""
    if not node.may_grants:
        return _declared_kinds(node)
    declared: set[str] = set()
    for grant in node.may_grants:
        if grant.via and not _via_matches_site(rel, symbol, grant.via):
            continue
        if not _of_matches_effect(grant.of, argument):
            continue
        kind = canonical_declared_kind(_may_kind(grant.atom))
        declared |= expand_declared_kind(kind)
    return frozenset(declared)


# ---------------------------------------------------------------------------
# T-2503: ambient (via-less) vs enumerated (via-populated) `may` grants.
#
# MEASURED motivation: the `testsuite` node's enumerated `via` lists ran to
# ~745 sites across 14 capability kinds, 91% of them (fs.write/exec/fs.read)
# carrying zero decision content -- "a test suite reads files, writes files,
# and runs subprocesses" is a tautology, and the enumeration bought nothing
# but merge-conflict churn and a stale SELFAUDIT001 ratchet bump every time a
# new test file did what every other test file already does.
#
# One syntax was doing two jobs, and the fix does not need a new grammar
# keyword: the EXISTING `via`-less/`via`-populated split (T-1440) already
# means exactly "whole-node ambient grant" vs "closed-set enumerated grant"
# -- `_declared_kinds`/`_declared_kinds_for_file`/`_declared_kinds_for_effect`
# already join a via-less `MayGrant` (or a flat `Node.may` atom) against
# EVERY site, and a via-populated grant against ONLY its listed sites,
# unconditionally REFUSING anything outside that list. Converting a node's
# fs.write/exec/fs.read grants from enumerated to via-less collapses the
# churn without touching the kernel join at all -- the property that must
# survive (an unlisted/undeclared kind is still a hard finding) is preserved
# by construction, since it was never the via-list mechanism that provided
# it; deny-by-default on a MISSING atom is unchanged, and a via-populated
# grant's closed-set refusal for its OWN unenumerated sites is unchanged.
#
# What is new here is GUARD 1: an ambient (via-less) `may` atom must carry a
# written reason, or it is exactly the exemption-that-matches-the-normal-
# case failure (T-1967) -- an unexplained blanket grant. Since `MayGrant`
# has no `reason` field (a model change is out of this ticket's declared
# scope, `src/frob/strata/_models.py` is not in `scope`), the reason lives
# as a same-line trailing `// because: "..."` comment in the `.strata`
# source text, checked here by a plain text scan -- the same "read the raw
# source, not just the parsed model" posture `_line_effects` already uses
# for needle detection, applied to the declaration side of a grant instead
# of the observation side.
# ---------------------------------------------------------------------------

#: Matches a via-less (no `via`/`of` trailer) `may "ATOM";` declaration line,
#: optionally followed by a same-line `// because: "REASON"` comment. A
#: via-populated declaration never matches: any `via`/`of` trailer sits
#: between the atom string and the terminating `;`, which this pattern
#: requires to follow the atom directly (only whitespace between), so this
#: regex naturally excludes enumerated grants without needing to parse them
#: out -- absence of a match on the trailing-comment group is itself the
#: "no reason given" finding, not a separate lookup.
_AMBIENT_MAY_RE = re.compile(
    r'^\s*may\s+"(?P<atom>[^"]+)"\s*;'
    r'(?:\s*//\s*because:\s*"(?P<reason>[^"]*)"\s*)?\s*$'
)

#: Matches a `node ID : trust {` / `store ID : trust {` block header line --
#: used only to track which node "owns" a `may` line for reporting (T-2523),
#: the same coarse text-scan posture `_AMBIENT_MAY_RE` already takes. A
#: nested/multi-line header (rare, none in this repo's own design/ today)
#: degrades to "node unresolved" for any `may` line before the next header
#: match -- fail SOFT on the label only, never on the finding itself, since
#: the reason-missing violation is real regardless of whether its owning
#: node could be named.
_NODE_HEADER_RE = re.compile(r"^\s*(?:node|store)\s+(?P<node>[A-Za-z_][\w.]*)\s*:")


# frob:doc docs/strata/surface.md#may-scope
# tests/unit/strata/test_effects.py::TestAmbientCapabilityReason.test_missing_reason_is_flagged kind="unit"  # noqa: E501
class AmbientCapabilityReasonViolation(BaseModel):
    """One ambient (via-less) `may` capability atom declared with no
    `// because: "..."` justification (T-2503, GUARD 1): an unexplained
    blanket grant is the exemption-that-matches-the-normal-case failure
    (T-1967) -- the reason is what makes an ambient grant auditable, the
    same discipline `frob:waive reason="..."` already requires for a
    suppressed gate finding."""

    model_config = ConfigDict(frozen=True)

    file: str
    line: int
    atom: str
    #: Best-effort enclosing `node`/`store` id (T-2523), or `""` if the
    #: scan could not resolve one before this line (an unusual `.strata`
    #: layout, or a `may` line appearing before any header at all) --
    #: reporting-only, never load-bearing for the finding itself.
    node: str = ""


# frob:doc docs/strata/surface.md#may-scope
# tests/unit/strata/test_effects.py::TestAmbientCapabilityReason.test_missing_reason_is_flagged kind="unit"  # noqa: E501
# tests/unit/strata/test_effects.py::TestAmbientCapabilityReason.test_reason_present_is_silent kind="unit"  # noqa: E501
# tests/unit/strata/test_effects.py::TestAmbientCapabilityReason.test_enumerated_grant_needs_no_reason kind="unit"  # noqa: E501
def check_ambient_capability_reasons(
    paths: tuple[Path, ...],
) -> tuple[AmbientCapabilityReasonViolation, ...]:
    """Every via-less `may "ATOM";` declaration across `paths` (T-2503) with
    no same-line `// because: "..."` comment (GUARD 1) -- a plain text scan
    of the `.strata` source, not the parsed `KernelModel`, since the reason
    is not (and by this ticket's declared scope cannot become) a modeled
    field. A via-populated (`via`/`of`-bearing) declaration is never
    flagged: `_AMBIENT_MAY_RE` structurally cannot match one (module-level
    comment above explains why), matching this ticket's own framing --
    enumerated grants are already self-documenting through their explicit
    site list, only an ambient grant's blanket reach needs a written WHY."""
    found: list[AmbientCapabilityReasonViolation] = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            _log.warning(
                "strata effects: could not read %s for ambient-reason scan: %s",
                path,
                exc,
            )
            continue
        current_node = ""
        for lineno, line in enumerate(text.splitlines(), start=1):
            header = _NODE_HEADER_RE.match(line)
            if header is not None:
                current_node = header.group("node")
            m = _AMBIENT_MAY_RE.match(line)
            if m is None:
                continue
            reason = m.group("reason")
            if reason is not None and reason.strip():
                continue
            _log.warning(
                "strata effects: ambient may %r at %s:%d (node=%s) has no because "
                "reason",
                m.group("atom"),
                path,
                lineno,
                current_node,
            )
            found.append(
                AmbientCapabilityReasonViolation(
                    file=str(path),
                    line=lineno,
                    atom=m.group("atom"),
                    node=current_node,
                )
            )
    _log.info(
        "strata effects: %d ambient-capability-reason violation(s) found across "
        "%d path(s)",
        len(found),
        len(paths),
    )
    return tuple(found)


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
def node_may_kinds(node: Node) -> frozenset[str]:
    """Public alias of `_declared_kinds`: every capability KIND `node`
    declares via its `may` atoms. Exposed for `frob.deploy` (T-0257),
    which derives a generated systemd unit's `CapabilityBoundingSet=`
    from the SAME kind join `export_seccomp`'s `SystemCallFilter=`
    already uses (`_export.py::node_allowed_syscalls`) -- one join, two
    renderings, never a duplicated `may`-kind derivation."""
    return _declared_kinds(node)


#: T-1478: matches the FIRST single- or double-quoted string literal in a
#: line fragment -- used to pull a best-effort argument value out of the
#: text immediately following a matched needle (`_first_string_literal`).
#: Deliberately simple (no escape handling): a real parse of the call
#: expression belongs to a first-class capability grammar, the same v0
#: scope cut this module's docstring already documents for `may` targets.
_STRING_LITERAL_RE = re.compile(r"""(['"])((?:(?!\1).)*)\1""")


def _first_string_literal(line: str, start: int) -> str | None:
    """The first quoted string literal's inner text in `line[start:]`, or
    `None` if none is present (T-1478) -- `start` is the needle's own end
    offset, so the search begins right after the matched capability
    call/accessor, skipping over the needle text itself (which for a
    needle like `os.environ[` would otherwise never contain a quote to
    match against anyway, but a needle without a trailing bracket, e.g. a
    bare attribute access, still must not accidentally match a quote that
    is part of an EARLIER, unrelated literal on the same line)."""
    m = _STRING_LITERAL_RE.search(line, start)
    return m.group(2) if m else None


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
    documentation, e.g.) was observed as a real effect. T-1478: each
    `ObservedEffect` also carries `argument`, the first string literal
    found after the needle on the same line (`_first_string_literal`),
    feeding the `of` argument-level join (`_of_matches_effect`)."""
    found: list[ObservedEffect] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if lineno in non_executable_lines:
            continue
        for vet_kind, kind in _KIND_MAP.items():
            for needle in table.get(vet_kind, ()):
                idx = line.find(needle)
                if idx != -1:
                    argument = _first_string_literal(line, idx + len(needle))
                    found.append(
                        ObservedEffect(
                            file=rel,
                            line=lineno,
                            kind=kind,
                            needle=needle,
                            argument=argument,
                        )
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
            no_kinds
            if node is None
            else _declared_kinds_for_effect(node, rel, symbol, effect.argument)
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
# tests/unit/strata/test_effects.py::TestStaleViaSymbol.test_unresolvable_symbol_is_flagged kind="unit"  # noqa: E501
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


# ---------------------------------------------------------------------------
# T-1628: capability via-list one-way ratchet.
#
# A `MayGrant`'s scoped `via` list (glob or symbol form) only ever grows in
# practice: a new file starts making a net call, the fix is to append it to
# the grant's `via`, and nothing pushes back -- the self-model documents an
# ever-loosening posture while `frob check` stays green the whole time. The
# ratchet closes that: a via-list may SHRINK freely, but growing it past the
# ceiling a committed lock file records requires an explicit, non-empty,
# hand-written justification in that SAME lock file -- the same reason-
# bearing discipline `frob:waive` already enforces for a suppressed finding,
# applied to a capability's blast radius instead of a gate rule.
#
# ASYMMETRIC FAILURE MODE (this is a SECURITY control, not a style lint):
# wrongly BLOCKING a legitimate widening is an annoyance a human overrides
# by editing the lock file with a reason; wrongly ALLOWING an unjustified
# widening -- or a bypass that launders one as if it were new -- is the
# actual vulnerability. Two bypass shapes are closed structurally, not by a
# second check bolted on afterward:
#   1. Deleting a (node, atom)'s lock entry does NOT reset its ceiling to
#      "anything goes" -- a missing entry reads as accepted_count=0, so the
#      very next observation at any nonzero count re-triggers the growth
#      violation immediately. Rewriting the lock file to erase history is
#      exactly as loud as never having a baseline at all.
#   2. Shrinking then re-growing back UP TO (not beyond) a previously
#      justified ceiling stays silent -- that ceiling was already earned by
#      a real reason once; re-approaching it is not a new widening. Growing
#      PAST that ceiling, even after an intervening shrink, still requires a
#      fresh lock edit -- the ceiling is a high-water mark, not a moving
#      average, so "shrink to look small, then grow past the real high-water
#      mark" cannot quietly slip through camouflaged as ordinary movement.
#
# DISCLOSED SCOPE CUT (v1, not silently dropped): an UNSCOPED grant
# (`via=()`, the whole-node grant every capability atom can also carry) is
# not counted here at all -- it is a strictly broader, different-shaped risk
# (blanket node access, not an enumerable site list) this via-list-specific
# ratchet does not attempt to bound. Renaming a node/atom to dodge tracking
# under a new key is also not detected -- a genuinely new (node, atom) pair
# reads as a fresh, unratcheted baseline, same as any other first sighting.
# Both are real residual gaps, named here rather than assumed covered.
#
# T-4495 TESTSUITE-GLOB CARVE-OUT: the `testsuite` node's `via` lists used to
# enumerate every exercising test file by name (300-500 entries per atom),
# which made `len(grant.via)` a faithful site count but cost every new test
# file a hand edit to `design/frob.strata` plus a lock-file bump. `testsuite`
# may now declare `exec`/`fs.write`/`fs.read`/`env.read` with a single bare
# glob entry (`via "tests/**"`) instead -- `_via_matches`/`_via_matches_site`
# already match a glob generically (T-1627), so conformance needs no change.
# The ratchet DOES need one: `len(grant.via)` would collapse to 1 for a
# glob-form grant, silently defeating the ratchet (a 400-file jump inside one
# glob entry would never register as growth). `capability_via_site_counts`
# instead counts the number of DISTINCT files under `testsuite`'s own code
# binding that both match the glob and carry a REAL observed effect of that
# atom's kind (`_glob_via_observed_site_count`, an `extract_effects`-shaped
# scan), so the ratchet still tracks the true total. `capability_ratchet_
# violations` then auto-accepts (writes a fresh lock entry with reason
# "testsuite glob growth" instead of raising a violation) growth on a
# `testsuite`-node, glob-only-via `(node, atom)` pair ONLY -- this is the ONE
# narrow, disclosed exception to "never auto-written by any code path here"
# below: a glob-form via has no enumerable per-file diff for a human to
# review line-by-line the way a hand-edited via-list addition does, so
# requiring a hand lock-edit for every ordinary new test file would just
# reintroduce the exact friction this carve-out exists to remove. Every
# OTHER node/atom, and a non-glob (enumerated) via-list on `testsuite`
# itself, keeps the original fail-closed, hand-edited-only ratchet
# unchanged.
#
# T-4563 LAND-OWNED WRITE: the auto-accept write above landed
# (T-4495) with no check on WHO was running it -- the DETACHED post-land
# sweep (`frob.app.ticket_runner._rapid_sweep`) spawns its own `frob
# check` against the plain root checkout well after the land that
# triggered it has finished, so that write rewrote the lock file
# directly in the SHARED ROOT with no commit absorbing it: DirtyMain then
# refused every next land. `_land_commit_in_progress` (this module) now
# gates the write on `root`'s own `land.lock` actually being held --
# true only while a land's own pre-commit check is running, exactly the
# window whose result becomes part of that land's composed commit (the
# same land-owned posture the T-0731 version bump already has). Any
# other caller (interactive `frob check`, the post-land sweep) still
# OBSERVES the growth -- logged at WARNING and returned as an ordinary
# `CapabilityRatchetViolation` -- it just never writes; the next land's
# own check run auto-accepts and commits it instead.
# ---------------------------------------------------------------------------

# frob:doc docs/strata/surface.md#may-scope
#: Repo-relative path to the committed ratchet ceiling: `{"entries":
#: {"<node_id>::<atom>": {"accepted_count": N, "reason": "...", "ticket":
#: "T-####"}}}`. Committed, hand-edited (widening it IS the "explicit,
#: recorded justification" act the module-level docstring above
#: describes), read fresh on every check -- EXCEPT the T-4495
#: testsuite-glob carve-out (module docstring), the one narrow shape a
#: code path here (`capability_ratchet_violations`) writes on its own,
#: since a glob-form via has no per-file diff for a human to review --
#: and even that write only happens while `_land_commit_in_progress`
#: (T-4563) reads `True`, so it never lands outside a land's
#: own composed commit.
CAPABILITY_RATCHET_LOCK_REL = "docs/design/registry/capability-via-ratchet.lock.json"


# frob:doc docs/strata/surface.md#may-scope
# frob:ticket T-1628
class CapabilityRatchetViolation(BaseModel):
    """One capability-ratchet (T-1628) finding: a `(node, atom)` pair's
    scoped via-list site count exceeds the committed ratchet lock's
    `accepted_count` for that pair (unjustified growth), or that pair's
    lock entry itself carries no non-empty `reason` (a malformed
    justification -- the same WAIVE001 discipline `frob:waive` already
    applies, mirrored here since this
    mechanism's justification lives in a lock file rather than a source
    comment)."""

    model_config = ConfigDict(frozen=True)

    node: str
    atom: str
    observed_count: int
    accepted_count: int
    detail: str


# frob:ticket T-4495
def _via_is_bare_glob_only(via: tuple[str, ...]) -> bool:
    """`True` when every entry in `via` (T-4495) is a bare glob: no `::`
    symbol qualifier (`_via_glob_and_symbol`) and at least one wildcard
    character (`*`, `?`, or `[`). This is the shape `capability_via_site_
    counts`/`capability_ratchet_violations` require, together with
    `node.id == "testsuite"`, before treating a grant's via-list length as
    unrepresentative of its real site count -- an ENUMERATED via-list
    (every entry a literal path, no wildcard) still counts by `len(via)`
    exactly as before, on every node including `testsuite` itself."""
    if not via:
        return False
    for entry in via:
        glob, symbol = _via_glob_and_symbol(entry)
        if symbol is not None:
            return False
        if not any(ch in glob for ch in "*?["):
            return False
    return True


# frob:ticket T-4495
def _glob_via_observed_site_count(
    node: Node, grant: MayGrant, binding: CodeBinding, root: Path
) -> int:
    """T-4495: the number of DISTINCT files `node` owns (per `binding`)
    that both match `grant.via`'s glob(s) (`_via_matches`) and carry at
    least one REAL observed effect (`_line_effects`) of `grant.atom`'s
    capability kind -- the actual measured quantity a testsuite-glob-form
    grant ratchets by, since `len(grant.via)` would collapse to 1 for a
    single `via "tests/**"` entry (module docstring's T-4495 section).
    Restricted to files this SAME node owns (never a full-repo scan) so a
    glob shared in spirit with another node's code binding never double-
    counts sites that belong to that other node."""
    kinds = expand_declared_kind(canonical_declared_kind(_may_kind(grant.atom)))
    count = 0
    for rel, owner in binding.owner.items():
        if owner != node.id or not _via_matches(rel, grant.via):
            continue
        if any(effect.kind in kinds for effect in _line_effects(root / rel, root)):
            count += 1
    return count


#: T-4669 (SF-04): per-process cache for `capability_via_site_counts`,
#: keyed by `(str(root), digest)` where `digest` is a content hash of
#: every file `_glob_via_observed_site_count` would actually read for
#: `model` -- NOT mtime (worktrees and git checkouts rewrite mtimes on a
#: checkout with unchanged content, which would defeat the cache exactly
#: when it matters most: right after a land/rebase). Measured at HEAD
#: c8f56ef10: the uncached call costs 23.03s cold, 17.83s again on a
#: second call in the SAME process -- SYS111, the land pre-commit check,
#: the composed-tree check and the detached post-land sweep each pay
#: this per call, and `_fix_engine_sync.py:1313` pays it TWICE per call
#: (`current_counts` and `before_counts`). Never cleared explicitly: a
#: process-lifetime cache is exactly what "one scan per process" (the
#: ticket's acceptance criterion) means, and a stale hit is impossible by
#: construction since a change to any scanned file changes the digest.
# frob:ticket T-4669
_CAPABILITY_SITE_COUNT_CACHE: dict[tuple[str, str], dict[str, int]] = {}

#: T-4669: per-process cache of one file's content hash, keyed by absolute
#: path, valued `(size, mtime_ns, sha256_hex)`. `_capability_scan_digest`
#: trusts a cached hash WITHOUT re-reading the file's bytes only when
#: `size` AND `mtime_ns` still match what was stat'd last time -- `mtime`
#: is a FAST-PATH invalidation hint here, never the source of truth: a
#: `size`/`mtime_ns` mismatch always falls back to re-reading and
#: re-hashing that one file (never trusts a stale hash), so the only
#: thing this buys is skipping a re-read of a file whose stat is
#: unchanged since the last digest -- it cannot produce a false content
#: match. Needed because `capability_via_site_counts`'s candidate set can
#: run to hundreds of test files: re-reading every one of them on every
#: call (even a cache HIT on the outer `_CAPABILITY_SITE_COUNT_CACHE`)
#: was measured to cost ~1.3s by itself, well over the ticket's <0.5s
#: warm-call target -- this cache is what gets a warm call from "read
#: every candidate file's bytes" down to "stat every candidate file".
# frob:ticket T-4669
_FILE_CONTENT_HASH_CACHE: dict[str, tuple[int, int, str]] = {}


# frob:ticket T-4669
def _cached_file_sha256(path: Path) -> str:
    """`path`'s content SHA-256, reusing `_FILE_CONTENT_HASH_CACHE`'s
    entry when `path`'s current `(size, mtime_ns)` still matches the
    stat this process last hashed it at -- see that cache's docstring
    for why a stat mismatch always re-reads rather than ever trusting a
    stale hash. Returns the empty-string digest (`hashlib.sha256(b"")`)
    for a path that cannot be stat'd/read, exactly matching the
    unreadable-file case the direct read/hash loop used before this
    helper existed."""
    key = str(path)
    try:
        st = path.stat()
    except OSError as exc:
        _log.debug(
            "strata effects: capability scan digest: could not stat %s: %s", path, exc
        )
        return hashlib.sha256(b"").hexdigest()
    cached = _FILE_CONTENT_HASH_CACHE.get(key)
    if cached is not None and cached[0] == st.st_size and cached[1] == st.st_mtime_ns:
        return cached[2]
    try:
        content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        _log.debug(
            "strata effects: capability scan digest: could not read %s: %s", path, exc
        )
        content_hash = hashlib.sha256(b"").hexdigest()
    _FILE_CONTENT_HASH_CACHE[key] = (st.st_size, st.st_mtime_ns, content_hash)
    return content_hash


# frob:ticket T-4669
def _bind_code_or_none(model: KernelModel, root: Path | None) -> CodeBinding | None:
    """`bind_code(model, root)`'s `Ok` value, or `None` when `root` is
    `None` or binding failed (logged) -- hoisted out of
    `capability_via_site_counts` so that function stays under the
    long-function threshold (ARCH001) now that it also has cache-lookup
    logic to run."""
    if root is None:
        return None
    bound = bind_code(model, root)
    if bound.is_err:
        _log.warning(
            "strata effects: capability via-site count: bind_code failed "
            "(%s) -- falling back to via-list length for every grant",
            bound.danger_err,
        )
        return None
    return bound.danger_ok


# frob:ticket T-4669
def _capability_site_count_cache_lookup(
    model: KernelModel, root: Path | None, binding: CodeBinding | None
) -> tuple[tuple[str, str] | None, dict[str, int] | None]:
    """`(cache_key, cached_result)` for `capability_via_site_counts`:
    `cache_key` is `None` when there is nothing to key a cache entry on
    (no `root`/no successful `binding`, matching the pre-T-4669 always-
    rescan behavior for that shape); `cached_result` is the previously
    cached `dict` (a fresh copy, safe for the caller to return directly)
    on a cache HIT, `None` on a MISS -- the caller must run the real scan
    and store it under `cache_key` itself. Hoisted out of `capability_
    via_site_counts` for the same ARCH001 reason `_bind_code_or_none`
    was."""
    if binding is None:
        return None, None
    assert root is not None
    candidates = _capability_scan_candidates(model, binding)
    digest = _capability_scan_digest(model, root, candidates)
    cache_key = (str(root), digest)
    cached = _CAPABILITY_SITE_COUNT_CACHE.get(cache_key)
    if cached is not None:
        _log.debug(
            "strata effects: capability via-site count: cache HIT "
            "(root=%s digest=%s, %d candidate file(s))",
            root,
            digest,
            len(candidates),
        )
        return cache_key, dict(cached)
    _log.debug(
        "strata effects: capability via-site count: cache MISS "
        "(root=%s digest=%s, %d candidate file(s)) -- rescanning",
        root,
        digest,
        len(candidates),
    )
    return cache_key, None


# frob:ticket T-4669
def _capability_scan_candidates(model: KernelModel, binding: CodeBinding) -> list[str]:
    """Every `rel` path `capability_via_site_counts` would hand to
    `_glob_via_observed_site_count` for `model` against `binding` --
    the exact file set whose CONTENT the cache digest must cover, in
    deterministic order. Kept as its own function so the digest and the
    real scan can never drift onto two different predicates (the same
    single-join discipline `unbound_constructs`'s docstring names)."""
    candidates: list[str] = []
    for node in model.nodes:
        if node.id != "testsuite":
            continue
        for grant in node.may_grants:
            if not grant.via or not _via_is_bare_glob_only(grant.via):
                continue
            for rel, owner in binding.owner.items():
                if owner == node.id and _via_matches(rel, grant.via):
                    candidates.append(rel)
    return sorted(set(candidates))


# frob:ticket T-4669
def _capability_scan_digest(
    model: KernelModel, root: Path, candidates: list[str]
) -> str:
    """SHA-256 over `model`'s own grant signature (every `node.id`,
    `grant.atom`, `grant.via` triple, in declaration order) followed by
    `(rel, content)` for every path in `candidates` (already
    sorted+deduped by `_capability_scan_candidates`). `model`'s own
    signature must be IN the digest, not just the candidate files: two
    calls sharing one `root` but different `via`-list lengths on a
    non-`testsuite` (or non-glob) grant produce different `counts` from
    an IDENTICAL candidate file set (`_capability_scan_candidates` only
    covers the `testsuite`-bare-glob scan path), so the file-content hash
    alone cannot tell those two calls apart -- caught by a real test
    regression (`TestCapabilityRatchet.
    test_growth_beyond_justified_ceiling_fails_even_after_a_prior_shrink`)
    reusing one `tmp_path` across a shrunk and a regrown model. Digest
    changes iff `model`'s grant shape OR a scanned file's CONTENT
    changes -- a checkout that only touches mtimes (the reason this is
    not mtime-keyed, see `_CAPABILITY_SITE_COUNT_CACHE`) leaves it
    unchanged. A candidate file that vanishes or cannot be read still
    contributes its path to the digest (the loop below reads nothing
    further on `OSError`) so a delete still invalidates instead of
    silently reusing a stale hit."""
    digest = hashlib.sha256()
    for node in model.nodes:
        for grant in node.may_grants:
            digest.update(f"{node.id}\0{grant.atom}\0{grant.via}\0".encode("utf-8"))
    for rel in candidates:
        digest.update(rel.encode("utf-8"))
        digest.update(_cached_file_sha256(root / rel).encode("ascii"))
    return digest.hexdigest()


# frob:doc docs/strata/surface.md#may-scope
# frob:ticket T-1628
# frob:ticket T-4495
# frob:ticket T-4669
# tests/unit/strata/test_effects.py::TestCapabilityRatchet.test_shrink_is_silent
# tests/unit/strata/test_strata_scan_cache.py::TestCapabilityViaSiteCountsCache.test_second_call_in_process_is_a_cache_hit_under_one_second  # noqa: E501
# tests/unit/strata/test_strata_scan_cache.py::TestCapabilityViaSiteCountsCache.test_changed_tracked_file_invalidates_the_cache  # noqa: E501
def capability_via_site_counts(
    model: KernelModel, root: Path | None = None
) -> dict[str, int]:
    """`{"<node_id>::<atom>": total scoped site count}` across every
    `MayGrant` in `model` -- the ratchet's own measured quantity (module
    docstring's T-1628 section). A grant with an EMPTY `via` (the unscoped,
    whole-node form) contributes nothing: only scoped grants have an
    enumerable site count to ratchet.

    T-4495: for a `testsuite`-node grant whose `via` is bare-glob-only
    (`_via_is_bare_glob_only`), the count is the REAL observed site count
    (`_glob_via_observed_site_count`) instead of `len(grant.via)` (which
    would read as 1 for a single `via "tests/**"` entry) -- this needs
    `root` to scan real files, so it activates only when `root` is given;
    every OTHER grant, and every grant when `root` is `None` (the
    pre-T-4495 call shape every existing caller/test still uses), counts
    by `len(grant.via)` exactly as before. `root`'s own `bind_code` is
    computed at most once per call, shared across every glob-form grant;
    a `bind_code` failure is logged and this call falls back to `len(via)`
    for every grant rather than raising, matching this module's existing
    best-effort-on-binding-failure posture elsewhere."""
    binding = _bind_code_or_none(model, root)
    cache_key, cached = _capability_site_count_cache_lookup(model, root, binding)
    if cached is not None:
        return cached

    counts: dict[str, int] = {}
    for node in model.nodes:
        for grant in node.may_grants:
            if not grant.via:
                continue
            key = f"{node.id}::{grant.atom}"
            if (
                binding is not None
                and node.id == "testsuite"
                and _via_is_bare_glob_only(grant.via)
            ):
                assert root is not None
                count = _glob_via_observed_site_count(node, grant, binding, root)
            else:
                count = len(grant.via)
            counts[key] = counts.get(key, 0) + count
    if cache_key is not None:
        _CAPABILITY_SITE_COUNT_CACHE[cache_key] = dict(counts)
    return counts


# frob:ticket T-4495
def _testsuite_glob_ratcheted_keys(model: KernelModel) -> frozenset[str]:
    """`{"<node_id>::<atom>"}` for every `testsuite`-node `MayGrant` whose
    `via` is bare-glob-only (T-4495) -- the ONLY keys `capability_ratchet_
    violations` may auto-accept growth for instead of raising a
    violation. Deliberately narrower than `_via_is_bare_glob_only` alone:
    a bare-glob `via` on any node OTHER than `testsuite` still ratchets
    the ordinary, fail-closed, hand-edited-lock way (module docstring's
    T-4495 section: the carve-out is `testsuite`-specific by design, not
    a blanket "glob-form vias auto-accept" rule)."""
    return frozenset(
        f"{node.id}::{grant.atom}"
        for node in model.nodes
        if node.id == "testsuite"
        for grant in node.may_grants
        if grant.via and _via_is_bare_glob_only(grant.via)
    )


#: T-4583 (this ticket): the T-1514 pre-commit unscoped sweep's own
#: composed-tree `frob check` runs with `root` set to the land's
#: PERSISTENT warm sweep stage (`_ensure_warm_sweep_stage`,
#: `<primary root>/.frob/warm-sweep-stage`) or a disposable squash
#: worktree, NEVER the primary checkout `_land_lock` is actually
#: acquired against -- so `root / LAND_LOCK_REL` inside that spawned
#: subprocess never resolves to the real lock file no matter how the
#: nested stage path is walked. `_land_cmd.py`'s land-side spawn sets
#: this env var to the primary checkout's own path (str) for the
#: DURATION of that one spawn (mirrors `_land_internal_git_env`'s
#: restore-on-exit precedent for the identically-shaped FROB_LAND_
#: INTERNAL marker) whenever it is spawning the pre-commit sweep's
#: composed-tree check; `_land_commit_in_progress` below prefers it over
#: `root` whenever it is set and non-empty, so this file never needs a
#: path heuristic reconstructing the primary checkout from a warm
#: stage's nested layout -- the land is the only caller that knows its
#: own primary root, so it says so explicitly instead of this probe
#: guessing.
FROB_LAND_LOCK_ROOT_ENV = "FROB_LAND_LOCK_ROOT"


#: T-4633 (SYS111 ratchet ceiling land race, measured T-4508 x2,
#: T-4111): env var carrying the id of the ticket currently landing, set by
#: `frob.tickets._land_squash._refuse_if_selfaudit_findings_in_touched_
#: files` for the duration of its in-process SYS111 gate call. Threaded via
#: environ, not a parameter, for the exact same reason `FROB_LAND_LOCK_
#: ROOT_ENV` above is: `frob.gates._sys.sys111_findings_touching`'s fixed
#: `(root, files)` signature lives in a module leased by another in-
#: progress ticket (T-4212) for this ticket's whole duration, so its
#: signature cannot grow a new parameter here. Read only by `_branch_own_
#: via_growth_reason` to NAME the landing ticket in an auto-accepted lock
#: entry's reason; absent/blank reads as "no ticket id available" and
#: falls back to a generic reason, never as "skip the auto-accept".
# frob:doc docs/modules/gate-sys111-ratchet-auto-accept.md#fix-branch-own-via-growth-auto-accept-at-land-composed-tree-check-time  # noqa: E501
# frob:ticket T-4633
FROB_LAND_TICKET_ENV = "FROB_LAND_TICKET_ID"


# frob:ticket T-4633
# frob:waive SEC110 reason="FROB_LAND_TICKET_ENV is this same-process \
# in-flight-land-id handoff seam (T-4633) -- it carries a ticket id, never a secret, \
# and this function IS the seam's own set/restore implementation"
@contextmanager
def _land_ticket_id_env(ticket_id: str | None):
    """Context manager: while `ticket_id` is truthy, sets `FROB_LAND_
    TICKET_ENV` in `os.environ` to it for the duration of the `with`
    block and restores the prior value (or clears it) on exit; a no-op
    when `ticket_id` is falsy. Mirrors `_land_lock_root_env`'s own env-
    set/restore shape exactly -- same caller (`frob.tickets._land_squash.
    _refuse_if_selfaudit_findings_in_touched_files`), same T-4596
    precedent, one ticket later (T-4633)."""
    if not ticket_id:
        yield
        return
    prior = os.environ.get(FROB_LAND_TICKET_ENV)
    os.environ[FROB_LAND_TICKET_ENV] = ticket_id
    try:
        yield
    finally:
        if prior is None:
            os.environ.pop(FROB_LAND_TICKET_ENV, None)
        else:
            os.environ[FROB_LAND_TICKET_ENV] = prior


# frob:ticket T-4596
# frob:waive SEC110 reason="FROB_LAND_LOCK_ROOT_ENV is this same-process \
# in-flight-land primary-root handoff seam (T-4596/T-4583) -- it carries a filesystem \
# path, never a secret, and this function IS the seam's own set/restore implementation"
@contextmanager
def _land_lock_root_env(land_lock_root: Path | None):
    """Context manager: while `land_lock_root` is not `None`, sets
    `FROB_LAND_LOCK_ROOT_ENV` in `os.environ` to it for the duration of
    the `with` block and restores the prior value (or clears it) on
    exit; a no-op when `land_lock_root` is `None`. Private, single-caller
    helper (`frob.tickets._land_squash._refuse_if_selfaudit_findings_in_
    touched_files`, T-3324/T-4596) extracted only to keep that
    function under ARCH001's threshold -- the env-set/restore dance
    `_land_commit_in_progress` (below) trusts. T-4583's SUBPROCESS spawn
    (`frob.app.ticket_runner._land_cmd`) builds its own `env=` dict
    inline instead, since it needs a full `os.environ.copy()` for the
    child process, not a same-process mutation; if a future caller wants
    that same shape, promote this to a public `land_lock_root_env` with
    its own frob:doc/frob:tests edges first (COV002)."""
    if land_lock_root is None:
        yield
        return
    prior = os.environ.get(FROB_LAND_LOCK_ROOT_ENV)
    os.environ[FROB_LAND_LOCK_ROOT_ENV] = str(land_lock_root)
    try:
        yield
    finally:
        if prior is None:
            os.environ.pop(FROB_LAND_LOCK_ROOT_ENV, None)
        else:
            os.environ[FROB_LAND_LOCK_ROOT_ENV] = prior


# frob:ticket T-4563
# frob:ticket T-4583
# frob:waive SEC110 reason="reads the FROB_LAND_LOCK_ROOT_ENV seam this same module \
# owns (T-4596/T-4583) -- a filesystem path, never a secret"
def _land_commit_in_progress(root: Path) -> bool:
    """`True` when a `frob ticket land` run currently holds its own
    `land.lock` (T-4563). The T-4495 testsuite-glob auto-accept
    (`_capability_ratchet_growth_finding`) may only WRITE the committed
    ratchet lock file when this is `True` -- a land's own pre-commit
    `frob check` spawn holds this lock for its whole run, so the write
    lands inside that SAME not-yet-committed changeset (exactly like the
    T-0731 version bump, land-owned). A `frob check` spawned any other
    way -- an interactive run, or the DETACHED post-land sweep
    (`frob.app.ticket_runner._rapid_sweep`), which by design runs only
    AFTER the land that spawned it has already finished and released
    this lock -- observes `False` here and must never write: that write
    would land in the plain root working tree with no commit absorbing
    it, leaving it dirty and DirtyMain-blocking the next land (the exact
    regression this ticket fixes).

    T-4583: probes `FROB_LAND_LOCK_ROOT_ENV` FIRST (see its own comment
    above) -- when the land-side spawn set it, this is the ONLY
    trustworthy answer, since `root` here is the warm sweep stage or a
    disposable squash worktree, never the primary checkout the lock
    actually lives under. Only when that env var is absent/blank does
    this fall back to probing `root / LAND_LOCK_REL` directly (the
    pre-T-4583 behavior, still correct for every caller that IS handed
    its own primary root, e.g. an interactive `frob check`).

    Lazily imports `LAND_LOCK_REL` from `frob.tickets._leases` (never at
    module level) to avoid a `frob.strata` <-> `frob.tickets` import
    cycle -- this module has no other reason to depend on
    `frob.tickets`. Best-effort: any OSError probing the path reads as
    `False` (fail toward "not a land," the safer side: refusing to
    write is recoverable, an errant write to the shared root is not)."""
    import os

    from frob.tickets._leases import LAND_LOCK_REL

    env_root = os.environ.get(FROB_LAND_LOCK_ROOT_ENV, "").strip()
    probe_root = Path(env_root) if env_root else root
    # frob:ticket T-4596
    _log.info(
        "strata effects: _land_commit_in_progress: %s=%r -> probing %s/%s",
        FROB_LAND_LOCK_ROOT_ENV,
        env_root or None,
        probe_root,
        LAND_LOCK_REL,
    )
    try:
        found = (probe_root / LAND_LOCK_REL).is_file()
        # frob:ticket T-4596
        _log.info(
            "strata effects: _land_commit_in_progress: lock file %s -> %s",
            probe_root / LAND_LOCK_REL,
            found,
        )
        return found
    except OSError as exc:
        _log.warning(
            "strata effects: capability ratchet: could not probe %s for an "
            "active land lock under %s (%s) -- treating as no land in "
            "progress",
            LAND_LOCK_REL,
            probe_root,
            exc,
        )
        return False


# frob:ticket T-4495
def _write_capability_ratchet_lock_entry(
    root: Path, key: str, accepted_count: int, reason: str
) -> None:
    """T-4495: writes/updates exactly one entry of the committed ratchet
    lock (`CAPABILITY_RATCHET_LOCK_REL`) -- the ONE narrow, disclosed
    exception to this module's "committed, hand-edited, never auto-
    written" lock discipline (module docstring's T-4495 section): a
    `testsuite`-node glob-form via has no enumerable per-file diff for a
    human to review line-by-line, so ordinary growth (a new matching test
    file) is recorded here mechanically instead of demanding a hand lock
    edit every time. Preserves every OTHER field already in the document
    (`generated_by`, `schema_version`, every other entry) -- only `key`'s
    own entry is replaced. Best-effort: any read/parse/write failure is
    logged and swallowed, never raised -- a failed write here must not
    turn a passing check into a crashing one; the growth simply reappears
    as a live `CapabilityRatchetViolation` on the next run if this write
    did not actually land."""
    path = root / CAPABILITY_RATCHET_LOCK_REL
    try:
        raw = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (OSError, ValueError) as exc:
        _log.warning(
            "strata effects: capability ratchet: could not read %s for the "
            "T-4495 testsuite-glob auto-accept write: %s",
            path,
            exc,
        )
        return
    if not isinstance(raw, dict):
        raw = {}
    entries = raw.get("entries")
    if not isinstance(entries, dict):
        entries = {}
    entries[key] = {"accepted_count": accepted_count, "reason": reason}
    raw["entries"] = dict(sorted(entries.items()))
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        _log.warning(
            "strata effects: capability ratchet: could not write %s: %s", path, exc
        )
        return
    _log.info(
        "strata effects: capability ratchet: auto-accepted %s -> accepted_count=%d "
        "(%s)",
        key,
        accepted_count,
        reason,
    )


def _load_capability_ratchet_lock(root: Path) -> dict:
    """The committed ratchet lock's `entries` mapping, or `{}` if the file
    is absent/unparseable/malformed -- deny-by-default (module docstring's
    bypass-1 discussion): a missing or corrupt lock reads as "nothing is
    accepted yet", never as "nothing to check"."""
    path = root / CAPABILITY_RATCHET_LOCK_REL
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    entries = data.get("entries") if isinstance(data, dict) else None
    return entries if isinstance(entries, dict) else {}


# frob:ticket T-4563
def _testsuite_glob_growth_finding(
    root: Path, key: str, node_id: str, atom: str, count: int, accepted: int
) -> CapabilityRatchetViolation | None:
    """T-4563: the outcome for one testsuite-glob-ratcheted `key`
    that has grown, split out of `_capability_ratchet_growth_finding` to
    keep it under ARCH001's line threshold. Writes the lock (returning
    `None`, auto-accepted) only when `_land_commit_in_progress` reads
    `True` -- a land's own pre-commit check, whose write lands inside
    that SAME composed commit. Any other caller (an interactive `frob
    check`, or the detached post-land sweep, which by design runs only
    after its triggering land has already released this lock) observes
    the growth without writing anything: logged at WARNING as a pending
    acceptance and returned as an ordinary `CapabilityRatchetViolation`
    (the pre-T-4495 shape) so it stays visible rather than silently
    swallowed -- the next land's own check run sees the same growth,
    finds `_land_commit_in_progress` `True`, and writes+clears it then."""
    if _land_commit_in_progress(root):
        _write_capability_ratchet_lock_entry(root, key, count, "testsuite glob growth")
        return None
    _log.warning(
        "strata effects: capability ratchet: %s %s testsuite-glob growth "
        "to %d site(s) observed outside a land's own composed tree -- "
        "NOT writing %s (pending: only a land's own commit may write "
        "it); the next land's check run auto-accepts and commits it",
        node_id,
        atom,
        count,
        CAPABILITY_RATCHET_LOCK_REL,
    )
    return CapabilityRatchetViolation(
        node=node_id,
        atom=atom,
        observed_count=count,
        accepted_count=accepted,
        detail=(
            f"{atom} testsuite-glob via-list on {node_id} grew to "
            f"{count} site(s) -- pending auto-accept: only a land's own "
            f"composed-tree check run may write {CAPABILITY_RATCHET_LOCK_REL} "
            "for this glob-form pair; a bare check outside a land never "
            "writes it (T-4563)"
        ),
    )


#: T-4633: the one file this auto-accept diffs -- matches
#: `CAPABILITY_RATCHET_LOCK_REL`'s own single-file disclosed-scope
#: precedent (module docstring's T-4495 section) rather than walking
#: every `.strata` file under the design dir; every measured land-race
#: incident (T-4508 x2, T-4111) grew this same file.
# frob:ticket T-4633
_BRANCH_VIA_GROWTH_STRATA_REL = "design/frob.strata"


# frob:ticket T-4633
def _via_len_counts_from_module(module) -> dict[str, int]:
    """`{"<node_id>::<atom>": summed len(via)}` across every `MayGrantDecl`
    in a parsed `frob.strata._ast.Module`'s `nodes` AND `extends`
    (T-4633) -- the raw, unmerged, single-file counterpart to
    `capability_via_site_counts` (which needs a fully cross-file-
    elaborated `KernelModel`); used only to diff one file's via-list
    length before/after a branch's own edits, never to evaluate an
    actual ratchet ceiling itself."""
    counts: dict[str, int] = {}
    for node in module.nodes:
        for grant in node.may_grants:
            if not grant.via:
                continue
            key = f"{node.id}::{grant.atom}"
            counts[key] = counts.get(key, 0) + len(grant.via)
    for extend in module.extends:
        for grant in extend.may_grants:
            if not grant.via:
                continue
            key = f"{extend.id}::{grant.atom}"
            counts[key] = counts.get(key, 0) + len(grant.via)
    return counts


# frob:ticket T-4633
#: T-4633, split out of `_branch_own_via_growth` (ARCH001, the
#: 60-line function-length threshold): the two text-acquisition halves,
#: `_read_new_strata_text` (plain file read, best-effort) and
#: `_git_show_head_strata_text` (the `HEAD`-blob half, via `frob.gitio.
#: run_argv` -- never a bare `subprocess` call in THIS file, since
#: `stratamod`'s own node declaration has no `exec` grant and this
#: module's scope does not cover `design/frob.strata`, leased by T-4111
#: for this ticket's whole duration; `run_argv`'s spawn lives inside
#: `gitio.py`, a node whose `exec` capability IS already declared, so
#: routing through it needs no new via-site declaration at all -- and
#: gets the `FROB_DISABLE_EXEC` kill-switch and spawn-recorder
#: integration every other git call in the codebase already has, for
#: free), and `_via_growth_from_texts` (the pure diff: parse both,
#: subtract, keep only positive deltas). All three are best-effort:
#: any git/read/parse failure reads as "nothing to diff" (`""`/`{}`),
#: fail closed -- no key gets auto-accepted -- matching this module's
#: existing best-effort-on-infra-failure posture (`_write_capability_
#: ratchet_lock_entry`, `_land_commit_in_progress`).
def _read_new_strata_text(root: Path) -> str | None:
    """The current working-tree content of `_BRANCH_VIA_GROWTH_STRATA_
    REL` under `root`, or `None` if it does not exist or cannot be
    read."""
    path = root / _BRANCH_VIA_GROWTH_STRATA_REL
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        _log.warning(
            "strata effects: branch-own via growth: could not read %s: %s",
            path,
            exc,
        )
        return None


# frob:ticket T-4633
def _git_show_head_strata_text(root: Path) -> str:
    """`git show HEAD:_BRANCH_VIA_GROWTH_STRATA_REL` under `root`, via
    `frob.gitio.run_argv` -- `""` (never a parse target) on any spawn
    failure or nonzero exit."""
    from frob.gitio import run_argv

    shown = run_argv(["git", "show", f"HEAD:{_BRANCH_VIA_GROWTH_STRATA_REL}"], cwd=root)
    if shown.is_err:
        _log.warning(
            "strata effects: branch-own via growth: could not git-show "
            "HEAD:%s under %s: %s",
            _BRANCH_VIA_GROWTH_STRATA_REL,
            root,
            shown.danger_err,
        )
        return ""
    completed = shown.danger_ok
    return completed.stdout if completed.returncode == 0 else ""


# frob:ticket T-4633
def _via_growth_from_texts(old_text: str, new_text: str) -> dict[str, int]:
    """`{"<node_id>::<atom>": N}` for every POSITIVE via-list-length
    delta between `old_text` and `new_text` (both raw `design/
    frob.strata`-shaped source), via `_via_len_counts_from_module`.
    `{}` if `new_text` fails to parse; an unparseable `old_text` (or
    `""`, the no-prior-blob case) reads as zero prior counts, so every
    entry in `new_text` counts as newly added."""
    from ._parse import parse_module

    new_parsed = parse_module(new_text)
    if new_parsed.is_err:
        return {}
    old_parsed = parse_module(old_text) if old_text else None
    old_counts = (
        _via_len_counts_from_module(old_parsed.danger_ok)
        if old_parsed is not None and old_parsed.is_ok
        else {}
    )
    new_counts = _via_len_counts_from_module(new_parsed.danger_ok)
    return {
        key: new_count - old_counts.get(key, 0)
        for key, new_count in new_counts.items()
        if new_count - old_counts.get(key, 0) > 0
    }


# frob:ticket T-4633
def _branch_own_via_growth(root: Path) -> dict[str, int]:
    """T-4633 (SYS111 ratchet ceiling land race, measured
    T-4508 x2, T-4111): `{"<node_id>::<atom>": N}` for every via-list
    growth `_BRANCH_VIA_GROWTH_STRATA_REL` itself shows between its
    committed `HEAD` blob and the CURRENT working-tree content under
    `root` (`_git_show_head_strata_text` vs `_read_new_strata_text`,
    diffed by `_via_growth_from_texts`). A land's composed-tree check
    runs with `root`'s git `HEAD` still at the pre-squash tip
    (`_refuse_if_selfaudit_findings_in_touched_files`'s own docstring:
    "before-any-commit-exists shape") and the staged, not-yet-committed
    squash content already written into the working tree -- so this is
    exactly the diff the branch itself is about to introduce, with no
    base-ref parameter needing to thread through `frob.gates._sys.
    sys111_findings_touching`'s fixed signature (see `FROB_LAND_TICKET_
    ENV`'s own docstring above for why that module cannot grow one right
    now).

    Used ONLY to bound how much of an observed ratchet violation's
    growth `_capability_ratchet_growth_finding` may auto-accept -- never
    to widen a ceiling beyond what this diff itself shows; growth a land
    observes beyond what its OWN diff added (e.g. another ticket already
    landed on `dev` widened the same via-list) is not in this dict and
    so still refuses, unchanged."""
    new_text = _read_new_strata_text(root)
    if new_text is None:
        return {}
    return _via_growth_from_texts(_git_show_head_strata_text(root), new_text)


# frob:ticket T-4633
# frob:waive SEC110 reason="reads the FROB_LAND_TICKET_ENV seam this same module owns \
# (T-4633) -- a ticket id, never a secret"
def _branch_own_via_growth_reason() -> str:
    """T-4633: the lock-entry reason `_capability_ratchet_
    growth_finding` writes for a branch-own via-addition auto-accept --
    names the landing ticket via `FROB_LAND_TICKET_ENV` when set (the
    common case, `_land_ticket_id_env`'s own caller), else a generic
    fallback naming only the mechanism."""
    ticket_id = os.environ.get(FROB_LAND_TICKET_ENV, "").strip()
    if ticket_id:
        return f"branch-own via addition auto-accept ({ticket_id})"
    return "branch-own via addition auto-accept"


# frob:ticket T-4495
# frob:ticket T-4633
def _capability_ratchet_growth_finding(
    root: Path,
    key: str,
    node_id: str,
    atom: str,
    count: int,
    accepted: int,
    glob_ratcheted: frozenset[str],
    branch_growth: dict[str, int],
) -> CapabilityRatchetViolation | None:
    """T-4495/T-4633: one GROWN `(node, atom)` pair's outcome,
    split out of `capability_ratchet_violations` to keep it under
    ARCH001's line threshold -- `None` (auto-accepted, lock rewritten in
    place) when EITHER `key` is testsuite-glob-ratcheted and a land holds
    the write (`_testsuite_glob_growth_finding`, T-4563), OR (T-draft-
    213c1cfd) the growth beyond `accepted` is fully accounted for by the
    branch's OWN via additions (`_branch_own_via_growth`) and a land
    holds the write -- same auto-accept posture as the T-4596 testsuite-
    glob carve-out, generalized to any node/atom whose ceiling race is
    caused by the branch's own declared growth rather than a stale
    observation. Otherwise a real `CapabilityRatchetViolation` (the
    original, unchanged fail-closed behavior)."""
    if key in glob_ratcheted:
        return _testsuite_glob_growth_finding(root, key, node_id, atom, count, accepted)
    needed = count - accepted
    if (
        needed > 0
        and branch_growth.get(key, 0) >= needed
        and _land_commit_in_progress(root)
    ):
        reason = _branch_own_via_growth_reason()
        _write_capability_ratchet_lock_entry(root, key, count, reason)
        _log.info(
            "strata effects: capability ratchet: %s %s branch-own via "
            "growth to %d site(s) auto-accepted (%s)",
            node_id,
            atom,
            count,
            reason,
        )
        return None
    _log.warning(
        "strata effects: capability ratchet: %s %s grew to %d "
        "site(s), above the committed ceiling of %d",
        node_id,
        atom,
        count,
        accepted,
    )
    return CapabilityRatchetViolation(
        node=node_id,
        atom=atom,
        observed_count=count,
        accepted_count=accepted,
        detail=(
            f"{atom} via-list on {node_id} grew to {count} site(s), "
            f"above the committed ratchet ceiling of {accepted} -- "
            f"edit {CAPABILITY_RATCHET_LOCK_REL} to raise "
            "accepted_count with a non-empty reason, in the same diff"
        ),
    )


# frob:ticket T-4633
def _missing_reason_violation(
    key: str, node_id: str, atom: str, count: int, accepted: int, entry: dict | None
) -> CapabilityRatchetViolation | None:
    """One `(node, atom)` pair's outcome when it is NOT grown (`count <=
    accepted`): `None` unless `entry` exists with no non-empty `reason`,
    in which case a `CapabilityRatchetViolation` demanding one -- the
    same discipline `frob:waive` already requires. Split out of
    `capability_ratchet_violations` (ARCH001, T-4633) to keep
    that function under the 60-line threshold."""
    reason = entry.get("reason") if isinstance(entry, dict) else None
    if entry is None or (isinstance(reason, str) and reason.strip()):
        return None
    return CapabilityRatchetViolation(
        node=node_id,
        atom=atom,
        observed_count=count,
        accepted_count=accepted,
        detail=(
            f"{CAPABILITY_RATCHET_LOCK_REL} entry for {key!r} has no "
            "non-empty reason -- every ratchet entry must carry one, "
            "the same discipline frob:waive already requires"
        ),
    )


# frob:doc docs/strata/surface.md#may-scope
# frob:doc docs/modules/gate-sys111-ratchet-auto-accept.md#fix-branch-own-via-growth-auto-accept-at-land-composed-tree-check-time  # noqa: E501
# frob:ticket T-1628
# frob:ticket T-4495
# frob:ticket T-4633
# tests/unit/strata/test_effects.py::TestCapabilityRatchet.test_shrink_is_silent
# tests/unit/strata/test_effects.py::TestCapabilityRatchet.test_empty_reason_is_flagged
# T-1977: wired into frob sys audit's own CLI/gate surface (SYS111,
# src/frob/gates/_sys_selfaudit.py's _selfaudit_violations) -- the
# WIRE001 waiver that used to live here (T-1628's own disclosed scope
# cut) no longer applies now that a production Violation-producing gate
# path actually calls this.
def capability_ratchet_violations(
    model: KernelModel, root: Path
) -> tuple[CapabilityRatchetViolation, ...]:
    """T-1628: every `(node, atom)` pair whose current scoped via-list site
    count (`capability_via_site_counts`) exceeds the committed lock's
    `accepted_count` for that pair (module docstring: a missing entry is
    `accepted_count=0`), plus every EXISTING lock entry with no non-empty
    `reason` (`_missing_reason_violation`). Silent whenever the observed
    count is at or below the accepted ceiling, regardless of how it got
    there.

    Two land-only auto-accept exceptions, both applied inside
    `_capability_ratchet_growth_finding` rather than here: T-4495's
    testsuite-glob carve-out, and T-4633's branch-own-via-
    growth carve-out (the SYS111 ratchet-ceiling land race measured
    T-4508 x2, T-4111 -- see `_branch_own_via_growth`'s own docstring).
    `branch_growth` is computed once here, outside the per-key loop,
    since it does one `git show` regardless of how many keys grew."""
    observed = capability_via_site_counts(model, root)
    glob_ratcheted = _testsuite_glob_ratcheted_keys(model)
    branch_growth = (
        _branch_own_via_growth(root) if _land_commit_in_progress(root) else {}
    )
    lock = _load_capability_ratchet_lock(root)
    found: list[CapabilityRatchetViolation] = []
    for key, count in sorted(observed.items()):
        node_id, atom = key.split("::", 1)
        entry = lock.get(key)
        accepted_raw = entry.get("accepted_count") if isinstance(entry, dict) else None
        accepted = accepted_raw if isinstance(accepted_raw, int) else 0
        if count > accepted:
            growth = _capability_ratchet_growth_finding(
                root, key, node_id, atom, count, accepted, glob_ratcheted, branch_growth
            )
            if growth is not None:
                found.append(growth)
            continue
        missing_reason = _missing_reason_violation(
            key, node_id, atom, count, accepted, entry
        )
        if missing_reason is not None:
            found.append(missing_reason)
    return tuple(found)


__all__ = [
    "CAPABILITY_RATCHET_LOCK_REL",
    "AmbientCapabilityReasonViolation",
    "CapabilityRatchetViolation",
    "CapabilityViolation",
    "EffectReport",
    "LegacyCapabilityAliasViolation",
    "ObservedEffect",
    "StaleViaSymbolViolation",
    "capability_ratchet_violations",
    "capability_via_site_counts",
    "check_ambient_capability_reasons",
    "check_capability_conformance",
    "check_legacy_capability_aliases",
    "check_stale_via_symbols",
    "extract_effects",
    "node_may_kinds",
]
