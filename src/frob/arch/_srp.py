"""SRP/cohesion checks (ARCH1xx, T-0616, EPIC T-0329's ARCH1xx family): LCOM4
low-cohesion class, god-module (unrelated exports clustered by naming/usage
disjointness), and mixed-concern function (I/O + pure compute + string-
formatting in one body).

WHY here, not `_python.py`/`_cpp.py`: every check in this module is written
ONCE against `frob.arch._normalized.NormalizedModule` (T-0609) instead of a
per-language tree-sitter walk, so it fires identically for every adapter
that exists today (`PythonAdapter`, `TypeScriptAdapter`, `RustAdapter`,
`KotlinAdapter`) with no per-language branch in the check itself -- the
whole point of the normalized model (see its module docstring). Nothing
here parses a `tree_sitter.Tree` directly.

Each check is advisory (`ArchCategory`/`ArchSeverity` from `_models.py`),
never build-blocking on its own, and waivable via the existing T-0289
reasoned-override mechanism (`frob:waive ARCHxxx reason="..." [ceiling=N]`)
the same way `long-function`/`god-class` already are.

Thresholds are plain keyword arguments with calibrated module-level
defaults (mirroring `_patterns.py`'s `_MIN_*` constants and `_python.py`'s
`analyze_project(max_function_lines=30, ...)` convention) so a future
wiring ticket can thread them through `frob.toml`'s `[arch]` table
(`frob.app.config.load_arch_config`) exactly like the existing five
knobs -- that wiring itself is out of this ticket's scope (`_srp.py`,
`_models.py`, `docs/modules/arch.md`, tests only; `analyze_project`'s
orchestration and `frob.app.config` are untouched here).
"""
# frob:waive INV006 reason="T-1023 INV006 burn-down: this file's \
# exclusivity-vocabulary hit is source-level design-rationale/scope-cut prose (a \
# docstring or comment describing already-implemented internal behavior, verifiable by \
# reading the code it annotates) rather than a separate cross-module contract needing \
# its own tracked invariant; disposed as a calibration batch, not claim-by-claim, same \
# INV006 first-turn-on-pool disposition this repo already applies elsewhere (T-0585)"

from __future__ import annotations

from frob.arch._models import ArchSuggestion
from frob.arch._normalized import NormalizedClass, NormalizedFunction, NormalizedModule

# ---------------------------------------------------------------------------
# ARCH101: LCOM4 low-cohesion class
# ---------------------------------------------------------------------------

#: Minimum method count (T-0616) before a class is even considered for
#: LCOM4 -- a small class (a handful of methods) naturally has some methods
#: that do not share fields (a `__repr__`, a trivial getter); only a class
#: big enough to have a real "should this be two classes" question is worth
#: the connectivity analysis.
# frob:doc docs/modules/arch.md#srp-cohesion-checks
LCOM4_MIN_METHODS = 6

#: Minimum FIELD-USING methods (methods that read/write at least one
#: `self.<field>`) required before the connectivity graph is built at all
#: -- a class where most methods touch no field (a thin dataclass-like
#: shell with a couple of helpers) is not a cohesion smell candidate.
# frob:doc docs/modules/arch.md#srp-cohesion-checks
LCOM4_MIN_FIELD_USING_METHODS = 4


def _field_using_methods(
    methods: list[NormalizedFunction],
) -> list[tuple[NormalizedFunction, frozenset[str]]]:
    """Every method in `methods` paired with the set of field names it
    reads or writes (`self.<field>` accesses) -- methods touching no field
    at all are dropped, since LCOM4's connectivity graph is defined over
    field-using methods only (T-0616)."""
    out: list[tuple[NormalizedFunction, frozenset[str]]] = []
    for m in methods:
        fields = frozenset(fa.name for fa in m.field_accesses)
        if fields:
            out.append((m, fields))
    return out


def _lcom4_components(
    field_using: list[tuple[NormalizedFunction, frozenset[str]]],
) -> int:
    """The number of disjoint connected components in the LCOM4 graph: one
    node per field-using method, an edge between two methods that share at
    least one field name (T-0616's "connectivity graph over self-field
    reads/writes"). Computed via a plain union-find over method indices --
    the graph is small (per-class method count) so no library dependency
    is warranted."""
    n = len(field_using)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    for i in range(n):
        for j in range(i + 1, n):
            if field_using[i][1] & field_using[j][1]:
                union(i, j)

    return len({find(i) for i in range(n)})


# frob:doc docs/modules/arch.md#srp-cohesion-checks
# T-1020: the catalog's own static proxy for "Large Class" is literally
# "field/method count or LOC threshold, or low cohesion (LCOM) at large
# size" (docs/design/architecture-check-catalog.md sec 2.1) -- this is
# that LCOM check. "Single Responsibility" (sec 1.1) names a different
# proxy (churn-reason count / fan-out outlier, not yet built), but LCOM4
# disjoint-component detection is a standard, direct SRP-violation signal
# in its own right (a class whose methods partition into unrelated field-
# usage clusters IS doing more than one job) -- the disposition is kept,
# not downgraded, on that basis.
# frob:enforces ACC-1-1-1
# frob:enforces ACC-2-1-LARGE-CLASS
# frob:tests tests/unit/test_arch_srp.py::TestLcom4.test_disjoint_field_groups_trigger_lcom4  # noqa: E501
# frob:tests tests/unit/test_arch_srp.py::TestLcom4.test_shared_fields_do_not_trigger_lcom4  # noqa: E501
def check_lcom4(
    module: NormalizedModule,
    out: list[ArchSuggestion],
    *,
    min_methods: int = LCOM4_MIN_METHODS,
    min_field_using_methods: int = LCOM4_MIN_FIELD_USING_METHODS,
) -> None:
    """ARCH101: flag every class in `module` whose field-using methods
    partition into 2+ disjoint field-usage components (T-0616) -- the class
    is doing two (or more) unrelated jobs bundled into one name, each job
    visible as its own cluster of methods that never touch the other
    cluster's fields. Skips classes below `min_methods` (too small to be a
    real SRP question) or with fewer than `min_field_using_methods`
    field-touching methods (nothing for the connectivity graph to analyze).
    Written once against `NormalizedModule` -- fires identically for every
    `LanguageAdapter` (python, TypeScript, Rust, Kotlin) with no per-
    language branch here."""
    for c in module.classes:
        if len(c.methods) < min_methods:
            continue
        field_using = _field_using_methods(c.methods)
        if len(field_using) < min_field_using_methods:
            continue
        n_components = _lcom4_components(field_using)
        if n_components < 2:
            continue
        out.append(
            ArchSuggestion(
                file=module.path,
                line=c.line,
                category="low-cohesion-class",
                severity="warning",
                message=(
                    f"class `{c.name}` splits into {n_components} disjoint"
                    f" field-usage groups across {len(field_using)}"
                    " field-touching methods (LCOM4)"
                ),
                detail=(
                    "methods that never share a field form independent"
                    " responsibilities -- consider splitting the class along"
                    " those groups"
                ),
                symref=f"{module.path}::{c.name}",
                metric=n_components,
            )
        )


# ---------------------------------------------------------------------------
# ARCH102: god-module (unrelated exports clustered by naming/usage disjointness)
# ---------------------------------------------------------------------------

#: Minimum number of top-level exports (free functions + classes) before a
#: module is even considered for the god-module check (T-0616) -- a module
#: with a handful of exports is not a "everything and the kitchen sink"
#: candidate regardless of how unrelated they look.
# frob:doc docs/modules/arch.md#srp-cohesion-checks
GOD_MODULE_MIN_EXPORTS = 10

#: Minimum number of disjoint naming/usage clusters those exports must form
#: before the module counts as a god-module (T-0616) -- 2 clusters is
#: common (e.g. a small helper plus the main API); 3+ unrelated clusters is
#: the "does everything" shape this check targets.
# frob:doc docs/modules/arch.md#srp-cohesion-checks
GOD_MODULE_MIN_CLUSTERS = 3


def _is_data_only_class(c: NormalizedClass) -> bool:
    """Whether `c` is a pure data container (T-0977, audit finding 4 on
    T-0970/T-0399): a class with zero methods -- a pydantic `BaseModel`, a
    `dataclass`, a `StrEnum`, an `ErrorSet` variant bundle, or any other
    fields-only declaration. Such a class cannot participate in a "usage"
    edge (it calls nothing) and its only naming signal is its own name, so
    a file that is a deliberate flat catalogue of many unrelated DTOs
    (a conventional `_models.py`) inevitably clusters into
    `len(classes)`-many singleton groups -- maximal fragmentation by
    construction, not evidence of god-module sprawl. Excluding data-only
    classes from the export/cluster count entirely (rather than just
    de-weighting them) is the fix: measured against this repo's own
    `_models.py`-shaped files, it removes exactly the false-positive class
    (`cve/_models.py`, `dup/_models.py`, `gates/_models.py`,
    `strata/_ast.py` all drop out at zero non-data-only exports) while
    leaving files that mix real behavior across many classes/functions
    (`gates/__init__.py`, `tickets/_models.py`) untouched."""
    return len(c.methods) == 0


def _export_name_and_prefix(module: NormalizedModule) -> list[tuple[str, str]]:
    """`(name, naming_prefix)` for every top-level export (free function or
    method-bearing class) in `module` -- `naming_prefix` is the first
    `_`-delimited token of a `snake_case` name lowercased (a `CamelCase`
    class name is split on its first internal capital run instead), the
    cheap naming-cluster signal T-0616 calls for ("clustered by naming ...
    disjointness"). T-0977 excludes data-only classes (`_is_data_only_class`)
    from this list entirely -- see that helper's docstring for why."""

    def _prefix(name: str) -> str:
        if "_" in name:
            return name.split("_", 1)[0].lower()
        # CamelCase: take the leading capitalized run as one token, e.g.
        # "HTTPClient" -> "http", "UserRepo" -> "user".
        i = 1
        while i < len(name) and name[i].islower():
            i += 1
        return name[:i].lower() or name.lower()

    out: list[tuple[str, str]] = []
    for f in module.functions:
        out.append((f.name, _prefix(f.name)))
    for c in module.classes:
        if _is_data_only_class(c):
            continue
        out.append((c.name, _prefix(c.name)))
    return out


def _god_module_usage_edges(module: NormalizedModule) -> set[frozenset[str]]:
    """Every unordered pair of top-level export names where one calls the
    other (a `NormalizedCall.callee` matching another export's bare name,
    or a `Class.method`-style dotted callee whose head matches a class
    name) -- the "usage" half of T-0616's "naming/usage disjointness"
    clustering: two exports that call each other are related regardless of
    naming, so they must not land in different clusters."""
    export_names = {n for n, _ in _export_name_and_prefix(module)}
    edges: set[frozenset[str]] = set()

    def _walk(func: NormalizedFunction, owner: str) -> None:
        for call in func.calls:
            callee = call.callee.split(".", 1)[0]
            if callee in export_names and callee != owner:
                edges.add(frozenset({owner, callee}))
        for nested in func.nested_functions:
            _walk(nested, owner)

    for f in module.functions:
        _walk(f, f.name)
    for c in module.classes:
        for m in c.methods:
            _walk(m, c.name)
    return edges


def _god_module_clusters(module: NormalizedModule) -> int:
    """Number of disjoint clusters `module`'s top-level exports form once
    both naming-prefix groups and usage edges are unioned together
    (T-0616): exports sharing a naming prefix, OR connected by a call edge,
    land in the same cluster; everything else is its own cluster."""
    pairs = _export_name_and_prefix(module)
    names = [n for n, _ in pairs]
    prefix_of = dict(pairs)
    parent = {n: n for n in names}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    by_prefix: dict[str, list[str]] = {}
    for n in names:
        by_prefix.setdefault(prefix_of[n], []).append(n)
    for group in by_prefix.values():
        for other in group[1:]:
            union(group[0], other)

    for edge in _god_module_usage_edges(module):
        a, b = tuple(edge)
        if a in parent and b in parent:
            union(a, b)

    return len({find(n) for n in names})


# frob:doc docs/modules/arch.md#srp-cohesion-checks
# frob:tests tests/unit/test_arch_srp.py::TestGodModule.test_unrelated_export_clusters_trigger_god_module  # noqa: E501
# frob:tests tests/unit/test_arch_srp.py::TestGodModule.test_related_exports_do_not_trigger_god_module  # noqa: E501
def check_god_module(
    module: NormalizedModule,
    out: list[ArchSuggestion],
    *,
    min_exports: int = GOD_MODULE_MIN_EXPORTS,
    min_clusters: int = GOD_MODULE_MIN_CLUSTERS,
) -> None:
    """ARCH102: flag `module` when its top-level exports (free functions +
    classes) number at least `min_exports` AND partition into at least
    `min_clusters` disjoint naming/usage clusters (T-0616) -- the module
    bundles several unrelated concerns under one file instead of one
    cohesive API. Written once against `NormalizedModule`, so it fires for
    every `LanguageAdapter`."""
    pairs = _export_name_and_prefix(module)
    if len(pairs) < min_exports:
        return
    n_clusters = _god_module_clusters(module)
    if n_clusters < min_clusters:
        return
    out.append(
        ArchSuggestion(
            file=module.path,
            line=None,
            category="god-module",
            severity="warning",
            message=(
                f"module has {len(pairs)} top-level exports split across"
                f" {n_clusters} unrelated naming/usage clusters"
            ),
            detail=(
                "exports that never call each other and share no naming"
                " family look like separate concerns filed under one"
                " module -- consider splitting along the clusters"
            ),
            metric=n_clusters,
        )
    )


# ---------------------------------------------------------------------------
# ARCH103: mixed-concern function (I/O + pure compute + string-formatting)
# ---------------------------------------------------------------------------

#: Callee-name signals for an I/O-capability call (T-0616): a bare builtin
#: known to touch the filesystem/console/network, or a dotted call whose
#: head module/attribute is a well-known I/O-capability surface, or a
#: dotted call whose tail method name is a common stream verb.
_IO_BUILTINS = frozenset({"open", "input", "print"})
_IO_MODULE_PREFIXES = (
    "os.",
    "sys.",
    "socket.",
    "subprocess.",
    "requests.",
    "urllib.",
    "shutil.",
    "logging.",
)
_IO_METHOD_SUFFIXES = (".write", ".read", ".send", ".recv", ".flush", ".close")

#: Callee-name signals for a string-formatting call (T-0616): `.format`/
#: `.join` method calls, or the `str`/`repr` builtins used as a formatting
#: step.
_FORMAT_BUILTINS = frozenset({"str", "repr"})
_FORMAT_METHOD_SUFFIXES = (".format", ".join")

#: Minimum cyclomatic-proxy (branch/loop count) a function's body events
#: must show before its I/O + formatting calls also count as "pure compute"
#: mixed in -- a function with zero decision points around its I/O and
#: formatting calls is doing straight-line orchestration, not the
#: mixed-concern shape this check targets (T-0616's STRONG-HALLMARK-ONLY
#: posture, matching `_patterns.py`'s existing detectors).
# frob:doc docs/modules/arch.md#srp-cohesion-checks
MIXED_CONCERN_MIN_DECISION_POINTS = 2


def _is_io_call(callee: str) -> bool:
    """Whether `callee` (a `NormalizedCall.callee` string) looks like an
    I/O-capability call by name (T-0616) -- a bare I/O builtin, a call into
    a well-known I/O-surface module, or a call ending in a common stream
    verb method."""
    if callee in _IO_BUILTINS:
        return True
    if any(callee.startswith(p) for p in _IO_MODULE_PREFIXES):
        return True
    return any(callee.endswith(s) for s in _IO_METHOD_SUFFIXES)


def _is_format_call(callee: str) -> bool:
    """Whether `callee` looks like a string-formatting call by name
    (T-0616) -- `str`/`repr`, or a `.format`/`.join` method call."""
    if callee in _FORMAT_BUILTINS:
        return True
    return any(callee.endswith(s) for s in _FORMAT_METHOD_SUFFIXES)


def _decision_points(func: NormalizedFunction) -> int:
    """A cheap cyclomatic-style proxy for `func`'s OWN body events
    (branches + loops, not recursing into nested functions/classes, which
    become their own `NormalizedFunction`) -- the "pure compute" half of
    the mixed-concern signal (T-0616)."""
    return len(func.branches) + len(func.loops)


# frob:doc docs/modules/arch.md#srp-cohesion-checks
# frob:tests tests/unit/test_arch_srp.py::TestMixedConcernFunction.test_io_compute_and_formatting_together_trigger  # noqa: E501
# frob:tests tests/unit/test_arch_srp.py::TestMixedConcernFunction.test_single_concern_does_not_trigger  # noqa: E501
def check_mixed_concern_function(
    module: NormalizedModule,
    out: list[ArchSuggestion],
    *,
    min_decision_points: int = MIXED_CONCERN_MIN_DECISION_POINTS,
) -> None:
    """ARCH103: flag every function/method in `module` whose body mixes all
    three of: an I/O-capability call, a string-formatting call, and enough
    of its own decision points (`min_decision_points`) to count as real
    pure-compute logic rather than straight-line orchestration (T-0616).
    Any one or two of the three alone is ordinary code (a function that
    just prints a formatted string, or a function that reads a file and
    returns it raw, is not a smell) -- only all three together is the
    "one body, three unrelated concerns" shape this check targets.
    Written once against `NormalizedModule`, so it fires for every
    `LanguageAdapter`."""

    def _walk(func: NormalizedFunction, qualname: str) -> None:
        has_io = any(_is_io_call(c.callee) for c in func.calls)
        has_format = any(_is_format_call(c.callee) for c in func.calls)
        has_compute = _decision_points(func) >= min_decision_points
        if has_io and has_format and has_compute:
            out.append(
                ArchSuggestion(
                    file=module.path,
                    line=func.line,
                    category="mixed-concern-function",
                    severity="suggestion",
                    message=(
                        f"`{qualname}` mixes I/O, string-formatting, and"
                        f" {_decision_points(func)} decision points in one body"
                    ),
                    detail=(
                        "split the I/O, the formatting, and the compute"
                        " logic into separate functions so each has one"
                        " reason to change"
                    ),
                    symref=f"{module.path}::{qualname}",
                    metric=_decision_points(func),
                )
            )
        for nested in func.nested_functions:
            _walk(nested, f"{qualname}.<nested {nested.name}>")

    for f in module.functions:
        _walk(f, f.name)
    for c in module.classes:
        for m in c.methods:
            _walk(m, f"{c.name}.{m.name}")


# frob:doc docs/modules/arch.md#srp-cohesion-checks
# frob:tests tests/unit/test_arch_srp.py::TestRunSrpChecks.test_combines_all_three_checks  # noqa: E501
def run_srp_checks(module: NormalizedModule) -> list[ArchSuggestion]:
    """Run every ARCH1xx SRP/cohesion check (T-0616: `check_lcom4`,
    `check_god_module`, `check_mixed_concern_function`) against one
    `NormalizedModule` and return the combined suggestions -- the single
    entry point a future orchestration-wiring ticket (`analyze_project`,
    out of this ticket's scope) will call per parsed file, mirroring how
    `frob.arch._patterns`'s detectors are each called individually today."""
    out: list[ArchSuggestion] = []
    check_lcom4(module, out)
    check_god_module(module, out)
    check_mixed_concern_function(module, out)
    return out
