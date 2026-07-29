"""LSP (Liskov Substitution Principle) and ISP (Interface Segregation
Principle) checks (ARCH1xx, T-0618/T-0619, EPIC T-0330's SOLID catalog):
override raises `NotImplementedError` where the base is concrete, override
signature variance violation, override strengthens a precondition, override
weakens a postcondition, no-op override of a value-returning base method
(LSP), plus a fat interface whose resolved implementers mostly stub it out
and a narrow-client injected with a wide interface it barely uses (ISP).

WHY here, not `_python.py`/`_cpp.py`: every check in this module is written
ONCE against `frob.arch._normalized.NormalizedModule` (T-0609), mirroring
`frob.arch._srp`'s precedent (T-0616) -- a check fires identically for every
`LanguageAdapter` that exists (`PythonAdapter`, `TypeScriptAdapter`,
`RustAdapter`, `KotlinAdapter`) with no per-language branch in the check
itself. Nothing here parses a `tree_sitter.Tree` directly.

BASE<->OVERRIDE LINKAGE: `NormalizedFunction.overrides` (T-0609) is
populated by adapters for languages with an explicit override keyword/
annotation (Kotlin's `override` modifier, TypeScript's `override` modifier,
Rust's trait-impl methods) -- python has none, so `PythonAdapter` leaves it
unset (see its own module docstring). Rather than leave python's LSP checks
permanently blind, this module resolves the base<->override linkage itself,
PRECISION-DISCIPLINE style (matching `frob.arch._ocp`'s fail-toward-silence
posture): a class's `bases` (as written in source) are looked up against
every OTHER class defined in the SAME `NormalizedModule` -- a base class
defined in another file, or a dynamically-resolved base, makes the linkage
unresolvable from this file alone, and the pair is silently skipped rather
than risked as a false positive. A method name shared between a class and a
same-file base class serves as the override relationship for every check
below, whether or not the adapter also set `overrides` explicitly.

Each check is advisory (`ArchCategory`/`ArchSeverity` from `_models.py`),
never build-blocking on its own, and waivable via the existing T-0289
reasoned-override mechanism the same way every other `frob.arch._srp`/
`_ocp` category already is -- no real ARCH1xx gate is wired in this
ticket's scope (`_solid.py`, `_models.py`, docs, tests only); `symref`/
`metric` are populated on every finding so that wiring is a gate-side
addition later, not a re-instrumentation of these checks.
"""
# frob:waive INV006 reason="this module's 'only' occurrences are source-level \
# design-rationale/scope-cut prose describing already-implemented behavior (the \
# same-file-only override resolution, this ticket's own declared scope cut) verifiable \
# by reading the functions/docstrings they annotate, not a separate cross-module \
# contract needing its own tracked invariant -- the same INV006 first-turn-on-pool \
# disposition frob.arch._protocol_excuse's own module docstring already carries"

from __future__ import annotations

from frob.arch._models import ArchSuggestion
from frob.arch._normalized import NormalizedClass, NormalizedFunction, NormalizedModule

#: Exception type names (T-0618) read as "this override is not actually
#: implemented" -- a concrete override whose body raises one of these
#: (with the base method NOT itself raising the same type) is the textbook
#: LSP violation: a subtype callers cannot substitute for the base without
#: the call blowing up.
_NOT_IMPLEMENTED_EXCEPTIONS = frozenset({"NotImplementedError", "NotImplemented"})


def _same_module_base_lookup(module: NormalizedModule) -> dict[str, NormalizedClass]:
    """Every class defined in `module`, keyed by name (T-0618's
    same-file-only resolvability corpus for base<->override linkage --
    mirrors `frob.arch._ocp._collect_enum_classes`'s fail-toward-silence
    posture: a base class defined elsewhere is simply absent from this
    map, and any lookup against it fails closed rather than guesses)."""
    return {c.name: c for c in module.classes}


def _iter_override_pairs(
    module: NormalizedModule,
) -> list[tuple[NormalizedClass, NormalizedFunction, NormalizedFunction]]:
    """Every `(subclass, base_method, override_method)` triple resolvable
    from `module` alone (T-0618): for each class with a same-file base
    class, every method name the two share names a base<->override pair.
    A base class not defined in this module, or a subclass method with no
    same-named base method, is not resolvable and is not yielded -- the
    fail-toward-silence gate every check below relies on."""
    by_name = _same_module_base_lookup(module)
    pairs: list[tuple[NormalizedClass, NormalizedFunction, NormalizedFunction]] = []
    for cls in module.classes:
        base_methods_by_name: dict[str, NormalizedFunction] = {}
        for base_name in cls.bases:
            base_cls = by_name.get(base_name)
            if base_cls is None:
                continue
            for m in base_cls.methods:
                # First same-file base wins on a name collision across
                # multiple bases -- multiple inheritance's real MRO is out
                # of scope for a syntactic proxy; ambiguity is rare enough
                # not to special-case (matches `_ocp`'s "fail toward
                # silence on the genuinely hard case, not the common one").
                base_methods_by_name.setdefault(m.name, m)
        for m in cls.methods:
            base_m = base_methods_by_name.get(m.name)
            if base_m is not None and base_m is not m:
                pairs.append((cls, base_m, m))
    return pairs


def _qualname(
    cls: NormalizedClass, func: NormalizedFunction, module: NormalizedModule
) -> str:
    """`path::Class.method` symref (T-0289's shape) for `func` on `cls`
    inside `module`, so a future ARCH1xx gate can bind a `frob:waive` to
    the exact override the way `ARCH001` already does for `long-function`."""
    return f"{module.path}::{cls.name}.{func.name}"


# ---------------------------------------------------------------------------
# ARCH104: override raises NotImplementedError where base is concrete
# ---------------------------------------------------------------------------


# frob:doc docs/modules/arch.md#lsp-checks
# frob:tests tests/unit/test_arch.py::TestOverrideRaisesNotImplemented.test_concrete_override_raising_not_implemented_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestOverrideRaisesNotImplemented.test_base_itself_raising_not_implemented_is_not_flagged  # noqa: E501
def check_override_raises_not_implemented(
    module: NormalizedModule, out: list[ArchSuggestion]
) -> None:
    """ARCH104: flag every override (T-0618) that raises
    `NotImplementedError`/`NotImplemented` when its same-file base method
    does NOT itself raise the same exception type anywhere in its own
    body -- a subtype callers cannot actually substitute for the base
    without a call blowing up, the textbook LSP violation. A base method
    that is itself abstract (also raises `NotImplementedError`, e.g. a
    hand-rolled ABC method without `@abstractmethod`) is not flagged: the
    base already documents "override me", so the override doing exactly
    that is not a violation. Written once against `NormalizedModule`, so
    it fires for every `LanguageAdapter`."""
    for cls, base_m, override_m in _iter_override_pairs(module):
        base_raises = {r.exception_type for r in base_m.raises}
        if _NOT_IMPLEMENTED_EXCEPTIONS & base_raises:
            continue  # base is itself abstract-shaped -- not a violation
        override_raises = {r.exception_type for r in override_m.raises}
        if not (_NOT_IMPLEMENTED_EXCEPTIONS & override_raises):
            continue
        out.append(
            ArchSuggestion(
                file=module.path,
                line=override_m.line,
                category="lsp-not-implemented-override",
                severity="warning",
                message=(
                    f"`{cls.name}.{override_m.name}` overrides a concrete base"
                    " method but raises NotImplementedError"
                ),
                detail=(
                    "callers holding a base-typed reference cannot substitute"
                    " this subtype without the call blowing up -- either"
                    " implement it, or make the base method abstract too"
                ),
                symref=_qualname(cls, override_m, module),
            )
        )


# ---------------------------------------------------------------------------
# ARCH105: override signature variance violation
# ---------------------------------------------------------------------------


def _required_param_count(func: NormalizedFunction) -> int:
    """Count of `func`'s parameters with no default value (T-0618) --
    excludes a leading `self`/`this`-style receiver param by name so a
    method-vs-method comparison is apples to apples regardless of
    language convention."""
    return sum(
        1
        for p in func.params
        if not p.has_default and p.name not in ("self", "this", "cls")
    )


# frob:doc docs/modules/arch.md#lsp-checks
# frob:tests tests/unit/test_arch.py::TestOverrideSignatureVariance.test_narrower_required_params_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestOverrideSignatureVariance.test_wider_return_type_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestOverrideSignatureVariance.test_same_shape_signature_not_flagged  # noqa: E501
def check_override_signature_variance(
    module: NormalizedModule, out: list[ArchSuggestion]
) -> None:
    """ARCH105: flag every override (T-0618) whose signature is a variance
    violation against its same-file base method: it accepts FEWER required
    (no-default) parameters than the base (a caller substituting the
    override with base-typed arguments can no longer supply what the base
    accepted), OR its declared return-type text differs from the base's
    while the base's return type is itself annotated (a wider/different
    return contract the base's callers were not promised). Only compares
    when both sides carry the signal being compared (an unannotated return
    type on either side is not resolvable, so that half is skipped --
    fail-toward-silence). Written once against `NormalizedModule`, so it
    fires for every `LanguageAdapter`."""
    for cls, base_m, override_m in _iter_override_pairs(module):
        base_required = _required_param_count(base_m)
        override_required = _required_param_count(override_m)
        if override_required < base_required:
            out.append(
                ArchSuggestion(
                    file=module.path,
                    line=override_m.line,
                    category="lsp-signature-variance",
                    severity="warning",
                    message=(
                        f"`{cls.name}.{override_m.name}` accepts"
                        f" {override_required} required param(s) but base"
                        f" `{base_m.name}` requires {base_required}"
                    ),
                    detail=(
                        "a narrower override cannot be substituted for the"
                        " base wherever the base's full parameter contract"
                        " is called"
                    ),
                    symref=_qualname(cls, override_m, module),
                    metric=base_required - override_required,
                )
            )
            continue  # one variance finding per pair is enough signal
        if (
            base_m.return_type is not None
            and override_m.return_type is not None
            and base_m.return_type != override_m.return_type
        ):
            out.append(
                ArchSuggestion(
                    file=module.path,
                    line=override_m.line,
                    category="lsp-signature-variance",
                    severity="warning",
                    message=(
                        f"`{cls.name}.{override_m.name}` returns"
                        f" `{override_m.return_type}` but base `{base_m.name}`"
                        f" returns `{base_m.return_type}`"
                    ),
                    detail=(
                        "a caller holding a base-typed reference expects the"
                        " base's return type -- a different return type is a"
                        " variance violation, not a safe substitution"
                    ),
                    symref=_qualname(cls, override_m, module),
                )
            )


# ---------------------------------------------------------------------------
# ARCH106: override strengthens a precondition
# ---------------------------------------------------------------------------


def _param_names(func: NormalizedFunction) -> set[str]:
    """Bare parameter names of `func` (T-0618), receiver params excluded --
    the corpus a precondition-strengthening branch/raise is checked
    against for mentioning a shared param."""
    return {p.name for p in func.params if p.name not in ("self", "this", "cls")}


def _raise_or_assert_param_mentions(
    func: NormalizedFunction, params: set[str]
) -> set[str]:
    """Every name in `params` that appears in the condition text of one of
    `func`'s OWN branches (T-0618's proxy for `assert cond` / `if cond:
    raise ...` -- both normalize to a `NormalizedBranch` whose
    `condition_text` mentions the param) immediately followed by a raise
    on the same/next line, OR is named by one of `func`'s raises' nearby
    branch. Kept intentionally coarse (line-adjacency, not full data flow,
    matching `_ocp`'s syntactic-proxy posture): a branch mentioning a
    shared param whose body is a guard clause is the shape being detected,
    not a proof of causality."""
    mentioned: set[str] = set()
    raise_lines = {r.line for r in func.raises}
    for b in func.branches:
        # A guard clause reads as `if <cond mentioning param>: raise ...`
        # -- the raise line sits at or just after the branch's own line.
        if not any(0 <= rl - b.line <= 2 for rl in raise_lines):
            continue
        for p in params:
            if p in b.condition_text:
                mentioned.add(p)
    return mentioned


# frob:doc docs/modules/arch.md#lsp-checks
# frob:ticket T-0972
# frob:tests tests/unit/test_arch.py::TestOverrideStrengthenedPrecondition.test_added_guard_raise_on_shared_param_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestOverrideStrengthenedPrecondition.test_guard_raise_present_in_base_too_not_flagged  # noqa: E501
def check_override_strengthened_precondition(
    module: NormalizedModule, out: list[ArchSuggestion]
) -> None:
    """ARCH106: flag every override (T-0618) that adds a guard-clause raise
    (`if <cond mentioning a shared param>: raise ...`) on a parameter the
    base method also declares, when the base method's OWN body has no such
    guard on that same parameter name -- the override accepts a narrower
    input range than the base promised, so a caller substituting the
    override with an input the base accepted now gets an exception. A
    guard present on BOTH sides is not flagged: the precondition is not
    strengthened, just inherited. Written once against `NormalizedModule`,
    so it fires for every `LanguageAdapter`."""
    for cls, base_m, override_m in _iter_override_pairs(module):
        shared_params = _param_names(base_m) & _param_names(override_m)
        if not shared_params:
            continue
        base_guarded = _raise_or_assert_param_mentions(base_m, shared_params)
        override_guarded = _raise_or_assert_param_mentions(override_m, shared_params)
        new_guards = override_guarded - base_guarded
        if not new_guards:
            continue
        out.append(
            ArchSuggestion(
                file=module.path,
                line=override_m.line,
                category="lsp-strengthened-precondition",
                severity="warning",
                message=(
                    f"`{cls.name}.{override_m.name}` adds a guard raise on"
                    f" {sorted(new_guards)} the base `{base_m.name}` does not"
                    " have"
                ),
                detail=(
                    "a stricter precondition than the base promised breaks"
                    " substitutability -- callers relying on the base's"
                    " wider accepted range now get an exception"
                ),
                symref=_qualname(cls, override_m, module),
                metric=len(new_guards),
            )
        )


# ---------------------------------------------------------------------------
# ARCH107: override weakens a postcondition
# ---------------------------------------------------------------------------


def _always_returns_a_value(func: NormalizedFunction) -> bool:
    """Whether every `return` statement directly in `func`'s OWN body
    (T-0618, not counting nested functions) carries a value, AND there is
    at least one such return -- the syntactic proxy for "the base promises
    to always hand back a real value on every return path" this check's
    postcondition signal is built on. A function with zero returns, or any
    bare `return`/`return None`, does not make this promise."""
    if not func.returns:
        return False
    return all(
        r.value_text is not None and r.value_text != "None" for r in func.returns
    )


def _has_a_bare_return(func: NormalizedFunction) -> bool:
    """Whether `func`'s OWN body contains at least one bare `return`/
    `return None` (T-0618) -- the syntactic proxy for "this path hands the
    caller nothing", the postcondition-weakening signal when the base
    promised a value on every path (`_always_returns_a_value`)."""
    return any(r.value_text is None or r.value_text == "None" for r in func.returns)


# frob:doc docs/modules/arch.md#lsp-checks
# frob:tests tests/unit/test_arch.py::TestOverrideWeakenedPostcondition.test_bare_return_where_base_always_returns_value_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestOverrideWeakenedPostcondition.test_override_also_always_returning_value_not_flagged  # noqa: E501
def check_override_weakened_postcondition(
    module: NormalizedModule, out: list[ArchSuggestion]
) -> None:
    """ARCH107: flag every override (T-0618) whose same-file base method
    always returns a real value on every return path
    (`_always_returns_a_value`) while the override has at least one bare
    `return`/`return None` path (`_has_a_bare_return`) -- the base's
    postcondition ("you always get a value back") is weakened by the
    subtype, so a caller trusting the base's contract can receive `None`
    unexpectedly. Written once against `NormalizedModule`, so it fires for
    every `LanguageAdapter`."""
    for cls, base_m, override_m in _iter_override_pairs(module):
        if not _always_returns_a_value(base_m):
            continue
        if not _has_a_bare_return(override_m):
            continue
        out.append(
            ArchSuggestion(
                file=module.path,
                line=override_m.line,
                category="lsp-weakened-postcondition",
                severity="warning",
                message=(
                    f"`{cls.name}.{override_m.name}` can return nothing, but"
                    f" base `{base_m.name}` always returns a value"
                ),
                detail=(
                    "callers trusting the base's always-a-value contract can"
                    " now receive None from this subtype -- either always"
                    " return a value here too, or weaken the base's own"
                    " contract explicitly"
                ),
                symref=_qualname(cls, override_m, module),
            )
        )


# ---------------------------------------------------------------------------
# ARCH108: no-op override of a value-returning base method
# ---------------------------------------------------------------------------


# frob:doc docs/modules/arch.md#lsp-checks
# frob:tests tests/unit/test_arch.py::TestNoOpOverride.test_empty_body_override_of_value_returning_base_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestNoOpOverride.test_override_with_real_body_not_flagged  # noqa: E501
def check_noop_override(module: NormalizedModule, out: list[ArchSuggestion]) -> None:
    """ARCH108: flag every override (T-0618) whose OWN body is empty of any
    structural event (no branches/loops/calls/field-accesses/raises/
    catches, and either no returns at all or only a bare `return`/`return
    None`) when the same-file base method it overrides DOES return a real
    value on at least one path -- a no-op stand-in (`pass`/bare `return`)
    for a base method callers rely on for its actual value, silently
    breaking every caller substituting the subtype in. Written once
    against `NormalizedModule`, so it fires for every `LanguageAdapter`."""
    for cls, base_m, override_m in _iter_override_pairs(module):
        base_has_value_return = any(
            r.value_text is not None and r.value_text != "None" for r in base_m.returns
        )
        if not base_has_value_return:
            continue
        override_is_empty_shell = (
            not override_m.branches
            and not override_m.loops
            and not override_m.calls
            and not override_m.field_accesses
            and not override_m.raises
            and not override_m.catches
            and all(
                r.value_text is None or r.value_text == "None"
                for r in override_m.returns
            )
        )
        if not override_is_empty_shell:
            continue
        out.append(
            ArchSuggestion(
                file=module.path,
                line=override_m.line,
                category="lsp-noop-override",
                severity="warning",
                message=(
                    f"`{cls.name}.{override_m.name}` is a no-op override of"
                    f" value-returning base `{base_m.name}`"
                ),
                detail=(
                    "an empty override of a method callers rely on for its"
                    " actual return value silently breaks substitutability"
                    " -- implement it, or remove the override"
                ),
                symref=_qualname(cls, override_m, module),
            )
        )


# frob:doc docs/modules/arch.md#lsp-checks
# frob:tests tests/unit/test_arch.py::TestRunLspChecks.test_combines_multiple_checks  # noqa: E501
def run_lsp_checks(module: NormalizedModule) -> list[ArchSuggestion]:
    """Run every ARCH1xx LSP check (T-0618: `check_override_raises_
    not_implemented`, `check_override_signature_variance`,
    `check_override_strengthened_precondition`,
    `check_override_weakened_postcondition`, `check_noop_override`)
    against one `NormalizedModule` and return the combined suggestions --
    the single entry point a future orchestration-wiring ticket
    (`analyze_project`, out of this ticket's scope, mirroring T-0616's own
    disclosed cut) will call per parsed file, matching `frob.arch._srp.
    run_srp_checks`'s convention."""
    out: list[ArchSuggestion] = []
    check_override_raises_not_implemented(module, out)
    check_override_signature_variance(module, out)
    check_override_strengthened_precondition(module, out)
    check_override_weakened_postcondition(module, out)
    check_noop_override(module, out)
    return out


# ---------------------------------------------------------------------------
# ARCH109: fat interface (ISP, T-0619)
# ---------------------------------------------------------------------------

#: Base-class names (T-0619) that mark a class as an interface-shaped type
#: (python ABC/Protocol conventions -- the languages with an explicit
#: interface/trait keyword instead, Rust/TypeScript/Kotlin, are read from
#: `NormalizedClass.bases` the same way once an adapter surfaces that
#: keyword as a base name; no adapter changes are in this ticket's scope).
_INTERFACE_MARKER_BASES = frozenset(
    {"ABC", "abc.ABC", "ABCMeta", "abc.ABCMeta", "Protocol", "typing.Protocol"}
)

#: Minimum method count (T-0619) an interface-marked class must declare
#: before it is even considered a fat-interface candidate -- a 2-3 method
#: interface is not "fat" regardless of how implementers treat it.
# frob:doc docs/modules/arch.md#isp-checks
FAT_INTERFACE_MIN_METHODS = 4

#: Minimum number of same-file classes that name the interface as a base
#: (T-0619) before the aggregate stub ratio below is even computed -- the
#: check is "measured over resolved implementers, not per-class" per the
#: ticket, so a single implementer is not a big-enough sample.
# frob:doc docs/modules/arch.md#isp-checks
FAT_INTERFACE_MIN_IMPLEMENTERS = 2

#: Minimum fraction (T-0619) of resolved (interface-method, implementer)
#: override slots that must be stub bodies before the interface is flagged
#: fat -- aggregated across every resolvable implementer combined, not
#: per-implementer, matching the ticket's "measured over resolved
#: implementers" framing.
# frob:doc docs/modules/arch.md#isp-checks
FAT_INTERFACE_STUB_FRACTION = 0.5


def _is_stub_method(func: NormalizedFunction) -> bool:
    """Whether `func`'s OWN body is a stub implementation (T-0619): either
    it raises `NotImplementedError`/`NotImplemented` (the explicit
    "not implemented" shape `check_override_raises_not_implemented`
    already detects for LSP), OR it is a structurally empty shell (no
    branches/loops/calls/field-accesses/catches, and no value-returning
    `return`) -- the same "empty shell" test `check_noop_override` uses,
    reused here rather than re-derived (T-0619's implementer sample is the
    same NormalizedFunction shape LSP's no-op check already reads)."""
    if _NOT_IMPLEMENTED_EXCEPTIONS & {r.exception_type for r in func.raises}:
        return True
    return (
        not func.branches
        and not func.loops
        and not func.calls
        and not func.field_accesses
        and not func.catches
        and all(r.value_text is None or r.value_text == "None" for r in func.returns)
    )


def _resolved_implementers(
    interface: NormalizedClass, module: NormalizedModule
) -> list[NormalizedClass]:
    """Every OTHER class in `module` that names `interface` as a base
    (T-0619's same-file resolvability corpus, matching `_iter_override_
    pairs`'s fail-toward-silence posture: an implementer defined in
    another file is not resolvable from this module alone and is not
    counted)."""
    return [
        c for c in module.classes if c is not interface and interface.name in c.bases
    ]


# frob:doc docs/modules/arch.md#isp-checks
# frob:tests tests/unit/test_arch.py::TestFatInterface.test_mostly_stubbed_implementers_flag_fat_interface  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestFatInterface.test_mostly_implemented_methods_not_flagged  # noqa: E501
def check_fat_interface(module: NormalizedModule, out: list[ArchSuggestion]) -> None:
    """ARCH109: flag every same-file interface-marked class (`ABC`/
    `Protocol`-family base, T-0619) with at least `FAT_INTERFACE_MIN_
    METHODS` methods and at least `FAT_INTERFACE_MIN_IMPLEMENTERS`
    resolvable implementers, whose AGGREGATE (interface-method,
    implementer) override slots are stubbed (`_is_stub_method`) at or
    above `FAT_INTERFACE_STUB_FRACTION` -- measured over the whole
    resolved-implementer pool combined, not per implementer, per the
    ticket's "not per-class" framing: a handful of implementers each
    stubbing most of a wide interface is the classic "implement everything
    or nothing" ISP smell, not any single implementer's own problem.
    Written once against `NormalizedModule`, so it fires for every
    `LanguageAdapter`."""
    for interface in module.classes:
        if not (set(interface.bases) & _INTERFACE_MARKER_BASES):
            continue
        if len(interface.methods) < FAT_INTERFACE_MIN_METHODS:
            continue
        implementers = _resolved_implementers(interface, module)
        if len(implementers) < FAT_INTERFACE_MIN_IMPLEMENTERS:
            continue
        interface_method_names = {m.name for m in interface.methods}
        total_slots = 0
        stub_slots = 0
        for impl in implementers:
            impl_methods = {m.name: m for m in impl.methods}
            for name in interface_method_names:
                m = impl_methods.get(name)
                if m is None:
                    continue  # not overridden here -- unresolvable, skip
                total_slots += 1
                if _is_stub_method(m):
                    stub_slots += 1
        if total_slots == 0:
            continue
        fraction = stub_slots / total_slots
        if fraction < FAT_INTERFACE_STUB_FRACTION:
            continue
        out.append(
            ArchSuggestion(
                file=module.path,
                line=interface.line,
                category="fat-interface",
                severity="warning",
                message=(
                    f"`{interface.name}` ({len(interface.methods)} methods,"
                    f" {len(implementers)} implementers) is"
                    f" {round(fraction * 100)}% stubbed across its resolved"
                    " implementers"
                ),
                detail=(
                    "most implementers leave most of this interface"
                    " unimplemented -- split it along what each implementer"
                    " actually provides instead of one wide contract"
                ),
                symref=interface.name,
                metric=stub_slots,
            )
        )


# ---------------------------------------------------------------------------
# ARCH110: narrow-client usage (ISP, T-0619)
# ---------------------------------------------------------------------------

#: Minimum method count (T-0619) a same-file class must declare before it
#: is even considered a "wide interface" a client parameter could be
#: injected with -- mirrors `FAT_INTERFACE_MIN_METHODS`'s calibration.
# frob:doc docs/modules/arch.md#isp-checks
NARROW_CLIENT_MIN_INTERFACE_METHODS = 4

#: Maximum fraction (T-0619) of a wide interface's methods a client
#: function/method may actually call before it stops reading as a
#: "narrow" consumer of that interface -- a client using MORE than a third
#: of a wide interface is using enough of it that splitting the interface
#: would not obviously help this particular client.
# frob:doc docs/modules/arch.md#isp-checks
NARROW_CLIENT_MAX_USED_FRACTION = 0.34


def _called_method_names(func: NormalizedFunction, receiver: str) -> set[str]:
    """Bare method names called as `<receiver>.<name>(...)` anywhere in
    `func`'s OWN body (T-0619, not counting nested functions) -- the
    "actually used" half of the narrow-client signal, read straight off
    `NormalizedCall.callee`'s dotted `obj.method` text (T-0609's adapter
    contract)."""
    prefix = f"{receiver}."
    names: set[str] = set()
    for call in func.calls:
        if call.callee.startswith(prefix):
            names.add(call.callee[len(prefix) :].split(".", 1)[0])
    return names


def _iter_wide_param_clients(
    module: NormalizedModule,
) -> list[tuple[str, NormalizedFunction, NormalizedClass]]:
    """Every `(qualname, func, interface_class)` triple (T-0619) where
    `func` (module-level or a method, not recursing into nested functions)
    declares a parameter whose annotated `type` text names a same-file
    class with at least `NARROW_CLIENT_MIN_INTERFACE_METHODS` methods --
    the injected-wide-interface corpus `check_narrow_client_usage` scans
    for actual per-method call usage. A parameter typed with an unresolvable
    (not same-file, or unannotated) type is not yielded -- fail toward
    silence, matching every other check in this module."""
    classes_by_name = {
        c.name: c
        for c in module.classes
        if len(c.methods) >= NARROW_CLIENT_MIN_INTERFACE_METHODS
    }

    def _scan(
        func: NormalizedFunction, qualname: str
    ) -> list[tuple[str, NormalizedFunction, NormalizedClass]]:
        found: list[tuple[str, NormalizedFunction, NormalizedClass]] = []
        for p in func.params:
            if p.type is None:
                continue
            iface = classes_by_name.get(p.type)
            if iface is None:
                continue
            found.append((qualname, func, iface))
        return found

    out: list[tuple[str, NormalizedFunction, NormalizedClass]] = []
    for f in module.functions:
        out.extend(_scan(f, f.name))
    for c in module.classes:
        for m in c.methods:
            out.extend(_scan(m, f"{c.name}.{m.name}"))
    return out


# frob:doc docs/modules/arch.md#isp-checks
# frob:tests tests/unit/test_arch.py::TestNarrowClientUsage.test_client_using_small_method_subset_flagged  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestNarrowClientUsage.test_client_using_most_of_interface_not_flagged  # noqa: E501
def check_narrow_client_usage(
    module: NormalizedModule, out: list[ArchSuggestion]
) -> None:
    """ARCH110: flag every function/method (T-0619) injected with a
    same-file parameter typed as a wide interface (`NARROW_CLIENT_MIN_
    INTERFACE_METHODS`+ methods) that calls at most `NARROW_CLIENT_MAX_
    USED_FRACTION` of that interface's methods on the parameter -- a
    client depending on a wide contract for a narrow slice of it is the
    ISP split candidate the ticket calls out. A client calling ZERO of the
    interface's methods is a different smell (an unused/dead parameter,
    not a narrow-usage one) and is not flagged here. Written once against
    `NormalizedModule`, so it fires for every `LanguageAdapter`."""
    for qualname, func, iface in _iter_wide_param_clients(module):
        param_name = next(p.name for p in func.params if p.type == iface.name)
        iface_method_names = {m.name for m in iface.methods}
        used = _called_method_names(func, param_name) & iface_method_names
        if not used:
            continue
        fraction = len(used) / len(iface_method_names)
        if fraction > NARROW_CLIENT_MAX_USED_FRACTION:
            continue
        out.append(
            ArchSuggestion(
                file=module.path,
                line=func.line,
                category="narrow-client-usage",
                severity="suggestion",
                message=(
                    f"`{qualname}` calls only {len(used)}/"
                    f"{len(iface_method_names)} methods of `{iface.name}`"
                    f" on `{param_name}`"
                ),
                detail=(
                    "a narrow slice of a wide injected interface is an ISP"
                    " split candidate -- depend on a smaller interface"
                    " naming only the methods this client actually calls"
                ),
                symref=qualname,
                metric=len(iface_method_names) - len(used),
            )
        )


# frob:doc docs/modules/arch.md#isp-checks
# frob:tests tests/unit/test_arch.py::TestRunIspChecks.test_combines_both_checks  # noqa: E501
def run_isp_checks(module: NormalizedModule) -> list[ArchSuggestion]:
    """Run every ARCH1xx ISP check (T-0619: `check_fat_interface`,
    `check_narrow_client_usage`) against one `NormalizedModule` and return
    the combined suggestions -- the single entry point a future
    orchestration-wiring ticket (`analyze_project`, out of this ticket's
    scope, mirroring T-0616/T-0618's own disclosed cuts) will call per
    parsed file, matching `run_lsp_checks`'s convention."""
    out: list[ArchSuggestion] = []
    check_fat_interface(module, out)
    check_narrow_client_usage(module, out)
    return out
