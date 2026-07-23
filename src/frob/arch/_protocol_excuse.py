"""Language-excuse discharge predicates for T-0746's protocol verification
gate (docs/modules/gates.md#proto002proto003-t-0746).

T-0746's mandate: a state-requirement/invalid-transition violation the
`frob.gates._protocol_summary` verifier cannot statically prove satisfied
through the T-0744 DSL alone is an ERROR by default -- NEVER a silent pass
-- UNLESS a specific, per-language runtime guarantee discharges it, and
that discharge is itself recorded (never a quiet downgrade) and revocable
the moment the guarantee is observed broken. This module holds the pure,
best-effort TEXTUAL predicates each language's discharge rule reduces to;
it deliberately does not touch `tree_sitter` (unlike `frob.arch`'s other
per-language adapters, which parse a full `NormalizedModule`) -- a
discharge check only needs to answer "is this one idiom present in this
file", which a narrow regex answers cheaply and the caller can always
override with an explicit `frob:waive` if it is wrong for a given file
(same fallback every other best-effort gate in this repo already offers,
e.g. `frob.gates._protocol_summary`'s PROTO001 dunder-call disposition).

Doctrine (T-0746 ticket text, restated here as the single source every
`DischargeResult` this module returns must trace back to):
  - Rust: a `Drop` impl for the type discharges its cleanup obligation,
    UNLESS `mem::forget`/`ManuallyDrop` is observed on that type anywhere
    in the same source -- observing either REVOKES the discharge.
  - C++: RAII (a destructor-bearing class) discharges only when the
    resource's acquiring call result is held by an instance of that class.
  - Python: a `with`-block over the resource discharges lexically.
  - TypeScript: a `using`/`try`-`finally` block discharges lexically.
  - GC finalizers (Java/Kotlin `finalize()`, JS `FinalizationRegistry`,
    etc.) NEVER discharge -- a GC finalizer's run timing is unspecified,
    so it is not a static guarantee at all; `gc_finalizer_discharge` always
    returns a non-discharging `DischargeResult` and exists only so a
    caller has one call to make instead of hand-rolling "always False"
    (and so this doctrine has ONE tracked home, not four).

Every predicate is best-effort and WARN-caliber on its own (a caller
decides final severity) -- a false discharge (idiom matched textually but
not actually protecting the resource in question) is possible, same
caveat every other name-based heuristic in this repo already carries.
"""
# frob:waive INV006 reason="T-0746: this module docstring's 'ONLY'/'NEVER' \
# occurrences are source-level design-rationale prose describing this \
# module's own already-implemented scope/doctrine (verifiable by reading \
# the functions it annotates), the same INV006 first-turn-on-pool \
# disposition frob.graph.dsl's own module docstring already carries -- not \
# a separate cross-module contract needing its own tracked invariant"

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

__all__ = [
    "DischargeResult",
    "cpp_raii_discharge",
    "gc_finalizer_discharge",
    "python_with_discharge",
    "rust_drop_discharge",
    "typescript_using_discharge",
]

_RUST_DROP_RE = re.compile(r"impl\s+Drop\s+for\s+(\w+)")
_RUST_FORGET_RE = re.compile(r"(?:mem::forget|std::mem::forget)\s*\(\s*(\w+)")
_RUST_TYPE_ANNOTATION_RE = r"\b{var}\s*:\s*{type_name}\b"
_RUST_MANUALLY_DROP_RE = re.compile(r"ManuallyDrop\s*<\s*(\w+)\s*>")
_PY_WITH_RE = re.compile(r"\bwith\s+(\w+)")
_CPP_DESTRUCTOR_RE = re.compile(r"~(\w+)\s*\(")
_TS_USING_RE = re.compile(r"\busing\s+\w+\s*=\s*(\w+)")
_TS_TRY_FINALLY_RE = re.compile(r"\btry\b[\s\S]*?\bfinally\b[\s\S]*?\b(\w+)")


# frob:doc docs/modules/gates.md#proto002proto003-t-0746
class DischargeResult(BaseModel):
    """Whether a language-excuse discharges a protocol obligation, and why --
    `discharged=False` always carries a `reason` naming what was missing or
    what revoked it, so a `frob check` message never has to say "no" with
    no explanation (NO-FAIL-SILENT)."""

    model_config = ConfigDict(frozen=True)

    discharged: bool
    mechanism: str
    reason: str


# frob:doc docs/modules/gates.md#proto002proto003-t-0746
# frob:tests tests/test_gates.py::TestProtocolLanguageExcuseDischarge.test_rust_drop_impl_discharges  # noqa: E501
# frob:tests tests/test_gates.py::TestProtocolLanguageExcuseDischarge.test_rust_mem_forget_revokes_the_drop_discharge  # noqa: E501
# frob:tests tests/test_gates.py::TestProtocolLanguageExcuseDischarge.test_rust_manually_drop_revokes_the_discharge  # noqa: E501
# frob:tests tests/test_gates.py::TestProtocolLanguageExcuseDischarge.test_rust_no_drop_impl_is_not_discharged  # noqa: E501
def rust_drop_discharge(source: str, type_name: str) -> DischargeResult:
    """`impl Drop for <type_name>` discharges `type_name`'s cleanup
    obligation -- UNLESS `mem::forget`/`ManuallyDrop<type_name>` is also
    observed anywhere in `source`, either of which REVOKES the discharge
    (the value's destructor is no longer guaranteed to run).

    `mem::forget` takes a VARIABLE, not a type name -- best-effort textual
    revocation match: a `mem::forget(x)` call revokes the discharge when
    `x` also carries a `: <type_name>` type annotation somewhere in
    `source` (a parameter or `let` binding), the same name-based
    resolution posture every other predicate in this module already
    documents."""
    has_drop = any(m.group(1) == type_name for m in _RUST_DROP_RE.finditer(source))
    if not has_drop:
        return DischargeResult(
            discharged=False,
            mechanism="rust-drop",
            reason=f"no `impl Drop for {type_name}` found",
        )
    forgotten = any(
        re.search(
            _RUST_TYPE_ANNOTATION_RE.format(var=m.group(1), type_name=type_name),
            source,
        )
        for m in _RUST_FORGET_RE.finditer(source)
    )
    if forgotten:
        return DischargeResult(
            discharged=False,
            mechanism="rust-drop",
            reason=f"mem::forget observed on {type_name}: Drop discharge revoked",
        )
    manually_dropped = any(
        m.group(1) == type_name for m in _RUST_MANUALLY_DROP_RE.finditer(source)
    )
    if manually_dropped:
        return DischargeResult(
            discharged=False,
            mechanism="rust-drop",
            reason=f"ManuallyDrop<{type_name}> observed: Drop discharge revoked",
        )
    return DischargeResult(
        discharged=True,
        mechanism="rust-drop",
        reason=f"impl Drop for {type_name} guarantees the obligation runs",
    )


# frob:doc docs/modules/gates.md#proto002proto003-t-0746
# frob:tests tests/test_gates.py::TestProtocolLanguageExcuseDischarge.test_cpp_raii_destructor_discharges  # noqa: E501
# frob:tests tests/test_gates.py::TestProtocolLanguageExcuseDischarge.test_cpp_no_destructor_is_not_discharged  # noqa: E501
def cpp_raii_discharge(source: str, class_name: str) -> DischargeResult:
    """A `~<class_name>()` destructor discharges `class_name`'s cleanup
    obligation ONLY when the acquiring call's result is held by an
    instance of that destructor-bearing class -- best-effort textual
    check: a destructor for `class_name` exists in `source` at all
    (matching this repo's other name-based, non-scope-aware heuristics;
    the "result actually held" half is left to the caller to establish via
    the resource-tracking DSL's `escaped`/`acquired` sets, T-0809)."""
    has_destructor = any(
        m.group(1) == class_name for m in _CPP_DESTRUCTOR_RE.finditer(source)
    )
    if not has_destructor:
        return DischargeResult(
            discharged=False,
            mechanism="cpp-raii",
            reason=f"no ~{class_name}() destructor found",
        )
    return DischargeResult(
        discharged=True,
        mechanism="cpp-raii",
        reason=f"~{class_name}() destructor guarantees the obligation runs",
    )


# frob:doc docs/modules/gates.md#proto002proto003-t-0746
# frob:tests tests/test_gates.py::TestProtocolLanguageExcuseDischarge.test_python_with_block_discharges  # noqa: E501
# frob:tests tests/test_gates.py::TestProtocolLanguageExcuseDischarge.test_python_no_with_block_is_not_discharged  # noqa: E501
def python_with_discharge(source: str, resource: str) -> DischargeResult:
    """A `with ... <resource> ...:` block discharges `resource`'s cleanup
    obligation lexically -- Python's context-manager protocol guarantees
    `__exit__` runs on every exit from the block, normal or exceptional."""
    matched = any(m.group(1) == resource for m in _PY_WITH_RE.finditer(source))
    if not matched:
        return DischargeResult(
            discharged=False,
            mechanism="python-with",
            reason=f"no `with` block naming {resource!r} found",
        )
    return DischargeResult(
        discharged=True,
        mechanism="python-with",
        reason=f"a `with {resource}` block guarantees __exit__ runs",
    )


# frob:doc docs/modules/gates.md#proto002proto003-t-0746
# frob:tests tests/test_gates.py::TestProtocolLanguageExcuseDischarge.test_typescript_using_discharges  # noqa: E501
# frob:tests tests/test_gates.py::TestProtocolLanguageExcuseDischarge.test_typescript_try_finally_discharges  # noqa: E501
# frob:tests tests/test_gates.py::TestProtocolLanguageExcuseDischarge.test_typescript_bare_call_is_not_discharged  # noqa: E501
def typescript_using_discharge(source: str, resource: str) -> DischargeResult:
    """A `using`-declaration or a `try`/`finally` block naming `resource`
    discharges its cleanup obligation lexically -- both are TypeScript/JS
    guarantees that a disposal path runs on every exit from the block."""
    if any(m.group(1) == resource for m in _TS_USING_RE.finditer(source)):
        return DischargeResult(
            discharged=True,
            mechanism="typescript-using",
            reason=f"a `using` declaration for {resource!r} guarantees disposal",
        )
    if any(m.group(1) == resource for m in _TS_TRY_FINALLY_RE.finditer(source)):
        return DischargeResult(
            discharged=True,
            mechanism="typescript-try-finally",
            reason=f"a try/finally naming {resource!r} guarantees the finally runs",
        )
    return DischargeResult(
        discharged=False,
        mechanism="typescript-using",
        reason=f"no using-declaration or try/finally naming {resource!r} found",
    )


# frob:doc docs/modules/gates.md#proto002proto003-t-0746
# frob:tests tests/test_gates.py::TestProtocolLanguageExcuseDischarge.test_gc_finalizer_never_discharges  # noqa: E501
def gc_finalizer_discharge(resource: str) -> DischargeResult:
    """GC finalizers NEVER discharge (T-0746 doctrine): a finalizer's run
    timing (if it ever runs at all) is unspecified by every mainstream GC,
    so it is not a static guarantee -- always returns `discharged=False`,
    regardless of `resource`. Exists as a named call so this doctrine has
    one home instead of being re-derived (or, worse, silently assumed) at
    every call site that might otherwise be tempted to treat a
    `finalize()`/`FinalizationRegistry` as equivalent to Drop/RAII/with."""
    return DischargeResult(
        discharged=False,
        mechanism="gc-finalizer",
        reason=(
            f"GC finalizers never discharge a cleanup obligation ({resource!r}): "
            "finalizer run timing is unspecified"
        ),
    )
