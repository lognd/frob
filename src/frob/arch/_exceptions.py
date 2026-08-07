"""errors-as-values advisory (T-0688, child 3 of T-0685's exception
may-raise umbrella; wires into T-0623's fallibility family
`frob.arch._fallibility`): a PUBLIC function/method whose computed
may-raise set (`frob.arch._mayraise.compute_may_raise`) contains a
clearly-recoverable exception type, with no caller in the same module
visibly discharging it, recommends a typani `Result[T, E]` signature
instead -- the raise sites named as the sketch. Suggestion severity
(T-0332 noise discipline), same unwaivable-advisory channel every other
`frob.arch` category lives on (`frob.gates._unwaivable_channel_rules`
picks up the new category automatically): exceptions remain sanctioned
for programmer bugs, this is a recommendation, not a gate -- the sibling
consumer of the SAME computed sets that IS a real gate is
`frob.gates._exhaustive_handling.exhaustive_handling_gate` (EXHAUST001/
EXHAUST002), a different question (is an attempted boundary exhaustive)
over the same `compute_may_raise` output.

REUSE, NOT A SECOND ANALYSIS: this module consumes `frob.arch._mayraise.
compute_may_raise`'s already-computed, already-except-subtracted
per-function `raises` set (own raises + resolved callee propagation +
builtin raisers, `UNKNOWN` included) rather than re-deriving a second
exception-flow analysis -- its own job is narrower: (1) which of those
types count as "recoverable" (`_RECOVERABLE_EXCEPTION_TYPES`, duplicated
from `frob.arch._fallibility._RECOVERABLE_EXCEPTION_TYPES`'s own small
constant -- the same narrow same-shape-duplication precedent that
sibling module's own docstring already established, since this ticket's
scope carve-out is `_mayraise.py` only, not a blanket ban on every other
private import, but keeping this one small and local avoids a second
cross-module private dependency for four literal strings), and (2)
whether ANY same-module caller of the raising function visibly discharges
that type via its own wrapping `except` clause.

MODEL-LIMIT DISCLOSURE (matching `_mayraise.py`/`_fallibility.py`'s own
house convention): "does this caller handle it" is a coarse,
function-wide, EXACT-TYPE-OR-CATCH-ALL proxy -- no exception-hierarchy
subtype walk (unlike `_mayraise._catches`, which this module deliberately
does not import, per the scope carve-out around that private helper) and
no lexical scoping finer than "this catching function has some qualifying
`except` clause somewhere in its body" (the same function-wide adjacency-
proxy limit `_mayraise.py`'s own except-clause subtraction already
discloses). This can both under- and over-credit a caller as "handling"
relative to true block-scoped, subtype-aware coverage; a suggestion
severity finding is exactly where that coarseness is an acceptable
trade, per T-0332's own noise-discipline precedent for every advisory
category in this package.

WIRING STATUS: like `frob.arch._fallibility.run_fallibility_checks`
before it (that module's own precedent, still true as of this ticket),
`check_errors_as_values` is a written-once, fully-tested check against
`NormalizedModule` that is NOT YET dispatched by `analyze_project`'s live
per-file walk -- wiring the whole T-0623 fallibility family (plus this
category) into that dispatch loop is a distinct, larger-surface follow-up
(same "catalogued built, dispatch wiring deferred" shape T-0616's
Done report disclosed and T-0728 later closed for the SRP family); this
ticket files that follow-up rather than silently widening its own scope
to also touch `frob.arch.__init__`'s dispatch loop."""

from __future__ import annotations

from frob.arch._mayraise import compute_may_raise
from frob.arch._models import ArchSuggestion
from frob.arch._normalized import NormalizedFunction, NormalizedModule

#: Exception type names (T-0688) counted as "clearly recoverable" for
#: `check_errors_as_values` -- the same four user-input/lookup validation
#: types `frob.arch._fallibility._RECOVERABLE_EXCEPTION_TYPES` already
#: curates, duplicated narrowly here (see this module's docstring) rather
#: than imported across a sibling private boundary.
_RECOVERABLE_EXCEPTION_TYPES = frozenset(
    {"ValueError", "KeyError", "LookupError", "TypeError"}
)


def _qualname(
    module: NormalizedModule, cls_name: str | None, func: NormalizedFunction
) -> str:
    """`path::Class.method`/`path::function` symref (T-0289's shape,
    T-0688) -- a narrow local duplicate of `frob.arch._mayraise._qualname`,
    same reasoning as that module's own duplicate of `_fallibility`'s
    helper: one small private helper, not a cross-module import."""
    if cls_name is None:
        return f"{module.path}::{func.name}"
    return f"{module.path}::{cls_name}.{func.name}"


def _bare_callee_name(callee: str) -> str:
    """The trailing identifier of a possibly-dotted callee text (T-0688)
    -- same convention as `frob.arch._mayraise._bare_callee_name`."""
    return callee.rsplit(".", 1)[-1]


def _is_public(name: str) -> bool:
    """True when a bare function/method name (T-0688) is not
    underscore-prefixed -- this advisory's "public function" gate,
    matching this package's usual leading-underscore private convention."""
    return not name.startswith("_")


def _all_functions(
    module: NormalizedModule,
) -> list[tuple[NormalizedFunction, str, str]]:
    """Every top-level function/method in `module` (T-0688) as
    `(func, bare_name, qualname)` triples -- the enumeration this module's
    caller-discharge scan and the `compute_may_raise` qualname lookup both
    walk over."""
    out: list[tuple[NormalizedFunction, str, str]] = []
    for f in module.functions:
        out.append((f, f.name, _qualname(module, None, f)))
    for c in module.classes:
        for m in c.methods:
            out.append((m, m.name, _qualname(module, c.name, m)))
    return out


def _caller_visibly_handles(
    module: NormalizedModule, raising_bare_name: str, recoverable: frozenset[str]
) -> bool:
    """True when some function/method in `module` calls
    `raising_bare_name` and ALSO has its own catch clause broad enough to
    plausibly discharge at least one type in `recoverable` (a catch-all,
    or a catch naming one of `recoverable` directly -- T-0688's disclosed
    coarse, function-wide, exact-type-or-catch-all proxy; see this
    module's docstring). A caller that merely calls the function without
    any qualifying catch does not count."""
    for func, _bare, _qual in _all_functions(module):
        calls_it = any(
            _bare_callee_name(call.callee) == raising_bare_name for call in func.calls
        )
        if not calls_it:
            continue
        for c in func.catches:
            if c.exception_type is None or c.exception_type == "Exception":
                return True
            if c.exception_type in recoverable:
                return True
    return False


# frob:doc docs/modules/gates.md#errors-as-values-advisory-t-0688
# frob:ticket T-0688
# frob:ticket T-0972
# frob:tests tests/test_gates.py::TestErrorsAsValuesAdvisory.test_public_raiser_with_no_handling_caller_recommends_result  # noqa: E501
# frob:tests tests/test_gates.py::TestErrorsAsValuesAdvisory.test_public_raiser_with_handling_caller_not_flagged  # noqa: E501
# frob:tests tests/test_gates.py::TestErrorsAsValuesAdvisory.test_private_raiser_not_flagged  # noqa: E501
# frob:tests tests/test_gates.py::TestErrorsAsValuesAdvisory.test_only_ubiquitous_or_unknown_raises_not_flagged  # noqa: E501
def check_errors_as_values(module: NormalizedModule) -> list[ArchSuggestion]:
    """errors-as-values advisory (T-0688): a PUBLIC function/method whose
    `frob.arch._mayraise.compute_may_raise` set contains at least one
    `_RECOVERABLE_EXCEPTION_TYPES` member, with no same-module caller
    visibly discharging it (`_caller_visibly_handles`), gets a suggestion-
    severity `ArchSuggestion` (category `"errors-as-values-recommended"`)
    naming the recoverable types and pointing at the raising function as
    the sketch site. A function whose leaked set is empty, or contains
    only `UNKNOWN`/non-recoverable types (programmer-bug-class exceptions
    stay exceptions, per this module's docstring), is never flagged."""
    out: list[ArchSuggestion] = []
    mayraise = compute_may_raise(module)

    for func, bare_name, qualname in _all_functions(module):
        if not _is_public(bare_name):
            continue
        fmr = mayraise.get(qualname)
        if fmr is None:
            continue
        recoverable = frozenset(
            t for t in fmr.raises if t in _RECOVERABLE_EXCEPTION_TYPES
        )
        if not recoverable:
            continue
        if _caller_visibly_handles(module, bare_name, recoverable):
            continue
        out.append(
            ArchSuggestion(
                file=module.path,
                line=func.line,
                category="errors-as-values-recommended",
                severity="suggestion",
                message=(
                    # frob:waive PERF004 reason="recoverable is this loop's own per-function distinct set, not a shared re-sort"  # noqa: E501
                    f"`{qualname}` may raise {sorted(recoverable)} with no "
                    "caller in this module visibly handling it"
                ),
                detail=(
                    "a public function whose recoverable failure modes are"
                    " raised, not returned, and go unhandled at every"
                    " same-module call site is a candidate for a typani"
                    " Result[T, E] signature -- the raise sites named above"
                    " are the sketch for what the Err variant should carry"
                    " (UNKNOWN is never included: this reflects only"
                    " types this resolver could positively identify)"
                ),
                symref=qualname,
            )
        )
    return out


__all__ = ["check_errors_as_values"]
