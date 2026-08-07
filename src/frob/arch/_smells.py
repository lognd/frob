"""Miscellaneous design-smell checks (ARCH1xx, T-0624, EPIC T-0330's
catch-all family): mutable default argument, feature envy, data clumps,
magic literal, dead private code, deep inheritance, temporal coupling.
Also hosts module dependency cycle detection (T-0625, `module-dependency-
cycle`) -- a project-wide check, per T-0625's own declared scope naming
this module rather than a new one.

WHY here, not `_fallibility.py`/`_smells.py`'s siblings: this is the
epic's own catch-all bucket for smells that do not belong to a single
SOLID/type-design/logging/fallibility family, so it gets its own module
per the sibling-module-per-family convention `_solid.py`/`_layering.py`/
`_typedesign.py`/`_logging_checks.py`/`_fallibility.py` already
established. Every check here is written once against
`frob.arch._normalized.NormalizedModule` (T-0609), same convention as
those siblings -- nothing here parses a `tree_sitter.Tree` directly.

SCOPE NOTE: `src/frob/arch/_models.py`'s scope lease was free at
implementation time, so all seven categories below extend the SHARED
`frob.arch._models.ArchCategory`/`ArchSuggestion` directly -- no local
literal needed. `src/frob/arch/_normalized.py`'s lease was ALSO free;
`NormalizedParam.default_text` (a raw source-text default value) was
added there because `check_mutable_default_arg` cannot recognize a
list/dict/set literal default without it -- see that field's own
docstring.

PER-MODULE SCOPING DISCLOSURE (not routed around): `check_dead_private_
code` and `check_deep_inheritance` are described in this ticket's own
body as needing project-wide analysis (the T-0288 call graph for dead-
code; cross-file base-class resolution for inheritance depth) that a
single `NormalizedModule` cannot provide -- `frob.graph.callgraph`'s
project-wide reachability index is a SEPARATE subsystem this ticket's
`_smells.py`-only scope does not integrate with. Both checks below are
therefore disclosed PER-MODULE proxies (dead-private-code: unreferenced
within the SAME file's own calls; deep-inheritance: base-chain depth
resolvable within the SAME file's own class definitions), not the true
project-wide versions -- a genuine cross-file integration is a follow-up,
not silently narrowed here."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

from frob.arch._models import ArchSuggestion
from frob.arch._normalized import (
    NormalizedCall,
    NormalizedClass,
    NormalizedFunction,
    NormalizedModule,
)
from frob.logging import get_logger

_log = get_logger(__name__)

if TYPE_CHECKING:
    from frob.cycle.graph import DependencyGraph


def _qualname(
    module: NormalizedModule, cls: NormalizedClass | None, func: NormalizedFunction
) -> str:
    """`path::Class.method`/`path::function` symref (T-0289's shape,
    T-0624) for `func`, optionally scoped to `cls`."""
    if cls is None:
        return f"{module.path}::{func.name}"
    return f"{module.path}::{cls.name}.{func.name}"


# ---------------------------------------------------------------------------
# mutable default argument (T-0624)
# ---------------------------------------------------------------------------

#: Raw `default_text` prefixes (T-0624) counted as a mutable-literal
#: default -- a list/dict/set literal, or a same-type constructor call
#: with no arguments (`list()`, `dict()`, `set()`).
_MUTABLE_DEFAULT_PREFIXES = ("[", "{", "list(", "dict(", "set(")


def _is_mutable_default(text: str) -> bool:
    """True when `text` (a `NormalizedParam.default_text`, T-0624) looks
    like a mutable-literal default (`_MUTABLE_DEFAULT_PREFIXES`) -- a bare-
    text heuristic over unparsed source text, same convention as every
    other `*_text` field this model exposes."""
    stripped = text.strip()
    return any(stripped.startswith(p) for p in _MUTABLE_DEFAULT_PREFIXES)


# frob:doc docs/modules/arch.md#misc-design-smells
# frob:tests tests/unit/test_arch.py::TestMutableDefaultArg.test_list_literal_default_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestMutableDefaultArg.test_none_default_not_flagged  # noqa: E501
def check_mutable_default_arg(module: NormalizedModule) -> list[ArchSuggestion]:
    """Mutable default argument (T-0624): flag a parameter whose
    `default_text` looks like a list/dict/set literal or no-arg
    constructor call (`_is_mutable_default`) -- a mutable default is
    shared across every call that omits the argument, a classic
    surprising-aliasing bug. Written once against `NormalizedModule`, so
    it fires for every `LanguageAdapter`."""
    out: list[ArchSuggestion] = []

    def _scan(func: NormalizedFunction, qualname: str) -> None:
        for p in func.params:
            if not p.has_default or p.default_text is None:
                continue
            if not _is_mutable_default(p.default_text):
                continue
            out.append(
                ArchSuggestion(
                    file=module.path,
                    line=func.line,
                    category="mutable-default-arg",
                    severity="warning",
                    message=(
                        f"`{qualname}` param `{p.name}` defaults to a mutable"
                        f" literal `{p.default_text}`"
                    ),
                    detail=(
                        "a mutable default value is created ONCE and shared"
                        " across every call that omits the argument -- use"
                        " `None` and construct the mutable value inside the"
                        " function body instead"
                    ),
                    symref=qualname,
                )
            )

    for f in module.functions:
        _scan(f, f.name)
    for c in module.classes:
        for m in c.methods:
            _scan(m, _qualname(module, c, m))
    return out


# ---------------------------------------------------------------------------
# feature envy (T-0624)
# ---------------------------------------------------------------------------

#: Receiver names (T-0624) that count as "this method's own object" --
#: never counted as a foreign-receiver call for feature-envy purposes.
_SELF_RECEIVERS = frozenset({"self", "this", "cls"})


def _call_receiver(call: NormalizedCall) -> str | None:
    """The dotted receiver prefix of `call`'s callee (T-0624) --
    `"other.method"` -> `"other"`; a bare `"method"` (no dot) -> `None`
    (module-level function call, not a method call on some receiver)."""
    if "." not in call.callee:
        return None
    return call.callee.rsplit(".", 1)[0]


# frob:doc docs/modules/arch.md#misc-design-smells
# frob:tests tests/unit/test_arch.py::TestFeatureEnvy.test_method_calling_other_receiver_more_than_self_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestFeatureEnvy.test_method_calling_self_more_than_others_not_flagged  # noqa: E501
def check_feature_envy(module: NormalizedModule) -> list[ArchSuggestion]:
    """Feature envy (T-0624): tally each method's calls by receiver
    (`_call_receiver`); flag when some single non-self receiver's call
    count is STRICTLY GREATER than the `self`/`this`/`cls` call count AND
    at least 2 -- a method that talks to another object's interface more
    than its own is a classic feature-envy candidate (the method probably
    belongs on the other object). Written once against `NormalizedModule`,
    so it fires for every `LanguageAdapter`."""
    out: list[ArchSuggestion] = []

    for c in module.classes:
        for m in c.methods:
            receiver_counts: dict[str, int] = {}
            self_count = 0
            for call in m.calls:
                receiver = _call_receiver(call)
                if receiver is None:
                    continue
                if receiver in _SELF_RECEIVERS:
                    self_count += 1
                else:
                    receiver_counts[receiver] = receiver_counts.get(receiver, 0) + 1
            if not receiver_counts:
                continue
            envied_receiver, envied_count = max(
                receiver_counts.items(), key=lambda kv: kv[1]
            )
            if envied_count < 2 or envied_count <= self_count:
                continue
            out.append(
                ArchSuggestion(
                    file=module.path,
                    line=m.line,
                    category="feature-envy",
                    severity="suggestion",
                    message=(
                        f"`{_qualname(module, c, m)}` calls `{envied_receiver}`"
                        f" {envied_count} time(s), more than its own `self`"
                        f" ({self_count})"
                    ),
                    detail=(
                        "a method that calls another object's interface"
                        " more than its own is a feature-envy candidate --"
                        " consider moving this behavior onto the envied"
                        " object"
                    ),
                    symref=_qualname(module, c, m),
                    metric=envied_count,
                )
            )
    return out


# ---------------------------------------------------------------------------
# data clumps (T-0624)
# ---------------------------------------------------------------------------

#: Minimum keyword-argument-name group size (T-0624) counted as a
#: candidate "data clump" -- 1-2 shared keyword args together is
#: ordinary; 3+ repeated together is the "these clearly belong to one
#: parameter object" smell.
# frob:doc docs/modules/arch.md#misc-design-smells
DATA_CLUMP_MIN_GROUP_SIZE = 3

#: Minimum number of DISTINCT call sites (T-0624) the same keyword-arg
#: group must repeat at before it counts as a clump, not a coincidence.
# frob:doc docs/modules/arch.md#misc-design-smells
DATA_CLUMP_MIN_SITES = 3


# frob:doc docs/modules/arch.md#misc-design-smells
# frob:ticket T-0972
# frob:tests tests/unit/test_arch.py::TestDataClumps.test_same_three_keyword_group_at_three_sites_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestDataClumps.test_group_at_two_sites_not_flagged  # noqa: E501
def check_data_clumps(module: NormalizedModule) -> list[ArchSuggestion]:
    """Data clumps (T-0624): build the set of keyword-argument names
    (`NormalizedCallArg.keyword`) per call site across the whole module;
    for any call whose keyword-arg-name set has `DATA_CLUMP_MIN_GROUP_SIZE`
    (3) or more members, count how many DISTINCT call sites use that
    EXACT same set. A set repeated at `DATA_CLUMP_MIN_SITES` (3) or more
    sites is flagged once, at the first such site -- the same group of
    3+ params passed together, over and over, usually belongs in its own
    type. Per-module only (this model does not resolve cross-file call
    sites); positional-only call sites are invisible to this proxy since
    `NormalizedCallArg.keyword` is unset for them. Written once against
    `NormalizedModule`, so it fires for every `LanguageAdapter`."""
    out: list[ArchSuggestion] = []
    sites_by_group: dict[frozenset[str], list[tuple[str, int]]] = {}

    def _scan(func: NormalizedFunction) -> None:
        for call in func.calls:
            names = {a.keyword for a in call.args if a.keyword is not None}
            if len(names) < DATA_CLUMP_MIN_GROUP_SIZE:
                continue
            group = frozenset(names)
            sites_by_group.setdefault(group, []).append((call.callee, call.line))

    for f in module.functions:
        _scan(f)
    for c in module.classes:
        for m in c.methods:
            _scan(m)

    for group, sites in sites_by_group.items():
        if len(sites) < DATA_CLUMP_MIN_SITES:
            continue
        callee, line = sites[0]
        out.append(
            ArchSuggestion(
                file=module.path,
                line=line,
                category="data-clumps",
                severity="suggestion",
                message=(
                    # frob:waive PERF004 reason="group is this loop's own per-clump distinct set, not a shared re-sort"  # noqa: E501
                    f"keyword args {sorted(group)} passed together at"
                    f" {len(sites)} call sites (first: `{callee}`)"
                ),
                detail=(
                    "the same group of 3+ keyword args repeated across"
                    " several call sites is usually one domain concept --"
                    " give it its own type (a dataclass/NamedTuple) instead"
                    " of passing the fields separately"
                ),
                metric=len(sites),
            )
        )
    return out


# ---------------------------------------------------------------------------
# magic literal (T-0624)
# ---------------------------------------------------------------------------

#: Numeric literal text (T-0624) EXCLUDED from `check_magic_literal` --
#: 0/1/-1 are conventional (empty-check, single-step, off-by-one/reverse
#: indexing), not a "magic" unexplained constant.
_ALLOWED_BARE_NUMBERS = frozenset({"0", "1", "-1"})

#: Matches a bare, non-allowed numeric literal (T-0624) inside a branch
#: condition's raw text -- deliberately does not attempt full expression
#: parsing, same convention as every other `*_text`-scanning check in
#: this package.
_MAGIC_NUMBER_RE = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?(?![\w.])")


# frob:doc docs/modules/arch.md#misc-design-smells
# frob:tests tests/unit/test_arch.py::TestMagicLiteral.test_bare_number_in_condition_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestMagicLiteral.test_zero_and_one_not_flagged  # noqa: E501
def check_magic_literal(module: NormalizedModule) -> list[ArchSuggestion]:
    """Magic literal (T-0624): scan every branch's `condition_text` for a
    bare numeric literal not in `_ALLOWED_BARE_NUMBERS` (`_MAGIC_NUMBER_RE`)
    -- an unexplained constant threshold inside a comparison/branch
    condition should usually be a named constant instead. String literals
    are out of scope for this proxy (a branch's raw condition text cannot
    reliably distinguish a magic string from an identifier/attribute name
    without a real tokenizer). Written once against `NormalizedModule`,
    so it fires for every `LanguageAdapter`."""
    out: list[ArchSuggestion] = []

    def _scan(func: NormalizedFunction, qualname: str) -> None:
        for b in func.branches:
            for match in _MAGIC_NUMBER_RE.finditer(b.condition_text):
                literal = match.group(0)
                if literal in _ALLOWED_BARE_NUMBERS:
                    continue
                out.append(
                    ArchSuggestion(
                        file=module.path,
                        line=b.line,
                        category="magic-literal",
                        severity="suggestion",
                        message=(f"`{qualname}` branches on magic literal `{literal}`"),
                        detail=(
                            "an unexplained numeric literal in a branch"
                            " condition should be a named constant so its"
                            " meaning is documented at the definition site"
                        ),
                        symref=qualname,
                    )
                )

    for f in module.functions:
        _scan(f, f.name)
    for c in module.classes:
        for m in c.methods:
            _scan(m, _qualname(module, c, m))
    return out


# ---------------------------------------------------------------------------
# dead private code (T-0624, per-module proxy -- see module docstring)
# ---------------------------------------------------------------------------


def _referenced_names(module: NormalizedModule) -> set[str]:
    """Bare trailing names (T-0624) of every call callee anywhere in
    `module` -- the same-module reference set `check_dead_private_code`
    checks a private symbol's own name against."""
    names: set[str] = set()

    def _collect(func: NormalizedFunction) -> None:
        for call in func.calls:
            names.add(call.callee.rsplit(".", 1)[-1])

    for f in module.functions:
        _collect(f)
    for c in module.classes:
        for m in c.methods:
            _collect(m)
    return names


# frob:doc docs/modules/arch.md#misc-design-smells
# frob:tests tests/unit/test_arch.py::TestDeadPrivateCode.test_unreferenced_private_function_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestDeadPrivateCode.test_referenced_private_function_not_flagged  # noqa: E501
def check_dead_private_code(module: NormalizedModule) -> list[ArchSuggestion]:
    """Dead private code (T-0624, PER-MODULE proxy -- see this module's
    docstring): flag a private (name starts with `_`, not a dunder) top-
    level function whose bare name never appears as a call callee
    anywhere else in the SAME module (`_referenced_names`). This is
    deliberately NOT the ticket's own "using the T-0288 call graph"
    project-wide version -- `frob.graph.callgraph` is a separate
    subsystem this module does not integrate with; a private symbol
    called only from ANOTHER file (re-exported, or called via a package
    `__init__`) is invisible to this proxy and will false-positive here,
    disclosed rather than silently narrowed. Written once against
    `NormalizedModule`, so it fires for every `LanguageAdapter`."""
    out: list[ArchSuggestion] = []
    referenced = _referenced_names(module)
    for f in module.functions:
        if not f.name.startswith("_") or f.name.startswith("__"):
            continue
        if f.name in referenced:
            continue
        out.append(
            ArchSuggestion(
                file=module.path,
                line=f.line,
                category="dead-private-code",
                severity="suggestion",
                message=f"`{f.name}` is private and never called in this file",
                detail=(
                    "a private symbol with no in-file caller is either"
                    " dead code or called only from another file -- this"
                    " is a per-module proxy (no project-wide call-graph"
                    " reachability check here), so confirm before deleting"
                ),
                symref=f"{module.path}::{f.name}",
            )
        )
    return out


# ---------------------------------------------------------------------------
# deep inheritance (T-0624, per-module proxy -- see module docstring)
# ---------------------------------------------------------------------------

#: Depth-of-inheritance-tree threshold (T-0624) beyond which
#: `check_deep_inheritance` fires -- configurable via this module
#: constant, same convention as `PRIMITIVE_OBSESSION_MIN_PARAMS`.
# frob:doc docs/modules/arch.md#misc-design-smells
DEEP_INHERITANCE_THRESHOLD = 3


def _inheritance_depth(cls_name: str, bases_by_name: dict[str, list[str]]) -> int:
    """Depth of `cls_name`'s base chain resolvable within the SAME module
    (T-0624, `bases_by_name`) -- a base class not defined in this module
    (an external/stdlib base) terminates the walk at depth 1 for that
    branch, since this model does not resolve imports."""
    depth = 0
    seen: set[str] = set()
    current = cls_name
    while current in bases_by_name and current not in seen:
        seen.add(current)
        bases = bases_by_name[current]
        if not bases:
            break
        depth += 1
        current = bases[0]
    return depth


# frob:doc docs/modules/arch.md#misc-design-smells
# frob:tests tests/unit/test_arch.py::TestDeepInheritance.test_chain_beyond_threshold_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestDeepInheritance.test_shallow_chain_not_flagged  # noqa: E501
def check_deep_inheritance(module: NormalizedModule) -> list[ArchSuggestion]:
    """Deep inheritance (T-0624, PER-MODULE proxy -- see this module's
    docstring): resolves each class's base-class chain (`_inheritance_
    depth`) using only classes DEFINED IN THE SAME FILE -- a chain that
    continues in another file is invisible to this proxy and under-counts
    (disclosed, not silently narrowed: full DIT needs cross-file class
    resolution this ticket's scope does not add). Flags any class whose
    same-file-resolvable depth exceeds `DEEP_INHERITANCE_THRESHOLD` (3).
    Written once against `NormalizedModule`, so it fires for every
    `LanguageAdapter`."""
    bases_by_name = {c.name: list(c.bases) for c in module.classes}
    out: list[ArchSuggestion] = []
    for c in module.classes:
        depth = _inheritance_depth(c.name, bases_by_name)
        if depth <= DEEP_INHERITANCE_THRESHOLD:
            continue
        out.append(
            ArchSuggestion(
                file=module.path,
                line=c.line,
                category="deep-inheritance",
                severity="suggestion",
                message=(
                    f"`{c.name}` has an in-file-resolvable inheritance depth"
                    f" of {depth} (threshold: {DEEP_INHERITANCE_THRESHOLD})"
                ),
                detail=(
                    "a deep inheritance chain couples every subclass to"
                    " every ancestor's implementation details -- prefer"
                    " composition, or flatten the hierarchy"
                ),
                symref=f"{module.path}::{c.name}",
                metric=depth,
            )
        )
    return out


# ---------------------------------------------------------------------------
# temporal coupling (T-0624)
# ---------------------------------------------------------------------------

#: Field-name substrings (T-0624) that suggest a call-order-gating flag
#: (an initialization/readiness/open state tracked at runtime instead of
#: the type system) -- the target of `check_temporal_coupling`.
_TEMPORAL_FLAG_MARKERS = ("initialized", "ready", "started", "setup", "_open")


def _looks_like_temporal_flag(name: str) -> bool:
    """True when `name` (a `NormalizedField.name`, T-0624) contains one of
    `_TEMPORAL_FLAG_MARKERS` -- a bare-text heuristic over the field's
    declared name."""
    lowered = name.lower()
    return any(marker in lowered for marker in _TEMPORAL_FLAG_MARKERS)


# frob:doc docs/modules/arch.md#misc-design-smells
# frob:ticket T-0972
# frob:tests tests/unit/test_arch.py::TestTemporalCoupling.test_guard_clause_on_initialized_flag_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestTemporalCoupling.test_field_not_guarded_not_flagged  # noqa: E501
def check_temporal_coupling(module: NormalizedModule) -> list[ArchSuggestion]:
    """Temporal coupling (T-0624): flag a class with a `bool`-typed field
    whose name looks like a call-order gate (`_looks_like_temporal_flag`:
    contains `initialized`/`ready`/`started`/`setup`/`_open`) when some
    OTHER method's own body has a branch mentioning that field's name
    immediately followed (within 2 lines) by a raise -- the same guard-
    clause line-adjacency proxy `frob.arch._typedesign`'s illegal-states-
    representable check uses. Enforcing call order via a runtime flag
    instead of the type system (a builder/state-machine type that makes
    the un-initialized state unrepresentable) is the temporal-coupling
    smell. Written once against `NormalizedModule`, so it fires for every
    `LanguageAdapter`."""
    out: list[ArchSuggestion] = []
    for cls in module.classes:
        flag_fields = {f.name for f in cls.fields if f.type == "bool"}
        flag_fields = {n for n in flag_fields if _looks_like_temporal_flag(n)}
        if not flag_fields:
            continue
        for m in cls.methods:
            raise_lines = {r.line for r in m.raises}
            for b in m.branches:
                if not any(0 <= rl - b.line <= 2 for rl in raise_lines):
                    continue
                mentioned = {n for n in flag_fields if n in b.condition_text}
                if not mentioned:
                    continue
                out.append(
                    ArchSuggestion(
                        file=module.path,
                        line=b.line,
                        category="temporal-coupling",
                        severity="suggestion",
                        message=(
                            # frob:waive PERF004 reason="mentioned is this loop's own per-method distinct set, not a shared re-sort"  # noqa: E501
                            f"`{cls.name}.{m.name}` guards call order on runtime"
                            f" flag(s) {sorted(mentioned)}"
                        ),
                        detail=(
                            "call-order enforced by a runtime bool flag can"
                            " be forgotten by a future caller -- model the"
                            " states as distinct types (a builder/state-"
                            " machine) so the invalid order cannot be"
                            " expressed at all"
                        ),
                        symref=_qualname(module, cls, m),
                    )
                )
    return out


# ---------------------------------------------------------------------------
# module dependency cycle detection (T-0625)
# ---------------------------------------------------------------------------


# frob:doc docs/modules/arch.md#module-dependency-cycles
# frob:tests tests/unit/test_arch.py::TestModuleDependencyCycles.test_two_file_import_cycle_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestModuleDependencyCycles.test_acyclic_imports_not_flagged  # noqa: E501
def check_module_dependency_cycles(root: Path) -> list[ArchSuggestion]:
    """Module dependency cycle detection (T-0625): builds one project-wide
    import graph under `root` using the SAME primitives `frob.app.
    cycle_runner._build_graph` and `frob.arch._layering.check_layering_
    violations` already use (`frob.lang.extract_imports`/
    `resolve_local_import`), then finds strongly-connected components via
    the EXISTING `frob.cycle.graph.DependencyGraph`/`find_cycles` (Tarjan's
    algorithm) -- no second graph builder or cycle-finder is forked here,
    per this ticket's own body text. Each cycle (2+ distinct files, or a
    self-importing file) becomes one `ArchSuggestion` whose `message`
    reports the full cycle path (`a -> b -> c -> a`). Unlike every other
    check in this module, this one is NOT written against a single
    `NormalizedModule` -- a cycle is inherently a project-wide property,
    the same reason `check_layering_violations` also takes `root` instead
    of a `NormalizedModule`."""
    from frob.cycle.graph import find_cycles

    graph = _build_project_import_graph(root)
    return [_module_dependency_cycle_finding(cycle) for cycle in find_cycles(graph)]


# frob:ticket T-0976
def _build_project_import_graph(root: Path) -> "DependencyGraph":
    """One project-wide `DependencyGraph` under `root`, using the same
    `frob.lang.extract_imports`/`resolve_local_import` primitives `frob.
    app.cycle_runner._build_graph` and `frob.arch._layering.check_
    layering_violations` already use -- `check_module_dependency_cycles`'s
    graph-building half, split from its cycle-reporting half."""
    from frob.cycle.graph import DependencyGraph
    from frob.excludes import (
        is_excluded,
        is_skipped_dir,
        iter_files,
        load_exclude_globs,
    )
    from frob.lang import extract_imports, resolve_local_import

    graph = DependencyGraph()
    exclude_globs = load_exclude_globs(root)
    for path in iter_files(root, suffix=".py"):
        try:
            rel_path = path.relative_to(root)
        except ValueError:
            continue
        try:
            if any(is_skipped_dir(part) for part in rel_path.parts):
                continue
            rel = rel_path.as_posix()
            if exclude_globs and is_excluded(rel, exclude_globs):
                continue
            graph.add_node(rel)
            result = extract_imports(path)
            if result.is_err:
                continue
            for spec in result.danger_ok:
                resolved = resolve_local_import(
                    spec, "python", file_dir=path.parent, root=root
                )
                if resolved is not None:
                    graph.add_edge(rel, resolved)
        except Exception as exc:  # noqa: BLE001 -- one bad file must not abort the scan
            _log.debug("_build_project_import_graph: %s failed: %s", rel_path, exc)
            continue
    return graph


# frob:ticket T-0976
def _module_dependency_cycle_finding(cycle: list[str]) -> ArchSuggestion:
    """The `module-dependency-cycle` `ArchSuggestion` for one `find_cycles`
    result `cycle` (a list of file paths forming the cycle)."""
    path_text = " -> ".join([*cycle, cycle[0]])
    return ArchSuggestion(
        file=cycle[0],
        line=None,
        category="module-dependency-cycle",
        severity="warning",
        message=f"import cycle: {path_text}",
        detail=(
            "a module import cycle couples every file in the cycle"
            " to every other -- break it by extracting the shared"
            " symbols both sides need into a new module neither"
            " side of the cycle needs to import from the other"
        ),
        symref=cycle[0],
        metric=len(cycle),
    )


# frob:doc docs/modules/arch.md#misc-design-smells
# frob:tests tests/unit/test_arch.py::TestRunSmellChecks.test_combines_all_seven_checks  # noqa: E501
def run_smell_checks(module: NormalizedModule) -> list[ArchSuggestion]:
    """Run every ARCH1xx misc design-smell check (T-0624:
    `check_mutable_default_arg`, `check_feature_envy`,
    `check_data_clumps`, `check_magic_literal`, `check_dead_private_code`,
    `check_deep_inheritance`, `check_temporal_coupling`) against one
    `NormalizedModule` and return the combined suggestions, mirroring
    `frob.arch._fallibility.run_fallibility_checks`'s convention.
    `check_module_dependency_cycles` (T-0625) is NOT included here -- it
    is project-wide (takes `root`, not a `NormalizedModule`) and is called
    separately, the same split `_layering.check_layering_violations`
    already has relative to `_layering.check_no_di_construction`."""
    out: list[ArchSuggestion] = []
    out.extend(check_mutable_default_arg(module))
    out.extend(check_feature_envy(module))
    out.extend(check_data_clumps(module))
    out.extend(check_magic_literal(module))
    out.extend(check_dead_private_code(module))
    out.extend(check_deep_inheritance(module))
    out.extend(check_temporal_coupling(module))
    return out
