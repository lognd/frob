"""The Arbitrary protocol: derived, declared, and registered generators
(docs/modules/fuzz.md).

A type becomes generatable exactly one of three ways, resolved by
`resolve`: a `__fuzz__()` classmethod (declared -- the escape hatch for
invariants rejection sampling cannot hit efficiently), a pydantic
`BaseModel` subclass (derived -- a hypothesis strategy built from field
annotations, round-tripped through `model_validate` so validators act as
the invariant filter), or a `register(tp, strategy)` entry (registered --
for third-party types the caller cannot annotate). Anything else is
`Err(NoGenerator)`.

hypothesis is an optional dependency at import time: a worktree without it
installed still imports this module cleanly, and every function that would
need it returns `Err(NoGenerator)` instead of raising `ImportError`.

Registered strategies live in a `FuzzRegistry` (T-0469): the module-level
`register`/`resolve` functions default to a process-global instance for the
common single-project case, but a caller hosting more than one project in
one process (or a test that must not leak registrations across cases) can
construct its own `FuzzRegistry()` and pass it explicitly, keeping
registrations scoped instead of bleeding across projects sharing a process.
"""

# frob:waive TEST005 reason="module line coverage 77.2%, debt T-0160"

from __future__ import annotations

from typing import Any, get_type_hints

from pydantic import BaseModel
from typani import Err, Ok
from typani.result import Result

from frob.fuzz._models import FuzzError
from frob.logging import get_logger

_log = get_logger(__name__)

_st: Any = None
try:
    import hypothesis.strategies as _st  # noqa: F811

    HYPOTHESIS_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only where hypothesis is absent
    HYPOTHESIS_AVAILABLE = False


# frob:doc docs/modules/fuzz.md#public-api
class FuzzRegistry:
    """A registered-strategy table scoped to one instance (T-0469): the
    default module-level registry serves the common single-project case,
    but a multi-project host constructs its own instance per project so
    registrations never bleed across projects sharing a process."""

    def __init__(self) -> None:
        self._entries: dict[type, object] = {}

    # frob:doc docs/modules/fuzz.md#public-api
    def register(self, tp: type, strategy: object) -> None:
        """Register `strategy` (a hypothesis `SearchStrategy`) as the
        generator for `tp` on this instance."""
        _log.info("FuzzRegistry.register: %s -> %r", tp, strategy)
        self._entries[tp] = strategy

    def __contains__(self, tp: type) -> bool:
        """Whether `tp` has a registered strategy on this instance."""
        return tp in self._entries

    def __getitem__(self, tp: type) -> object:
        """The registered strategy for `tp`; raises `KeyError` if absent."""
        return self._entries[tp]


_default_registry = FuzzRegistry()


# frob:doc docs/modules/fuzz.md#public-api
def register(
    tp: type, strategy: object, *, registry: FuzzRegistry | None = None
) -> None:
    """Register `strategy` (a hypothesis `SearchStrategy`) as the generator
    for `tp`, on `registry` (default: the process-global default registry)."""
    (registry or _default_registry).register(tp, strategy)


def _declared_strategy(tp: type) -> object | None:
    """The hypothesis strategy from `tp.__fuzz__()`, or `None` if not declared."""
    fuzz_fn = getattr(tp, "__fuzz__", None)
    if fuzz_fn is None:
        return None
    try:
        return fuzz_fn()
    except Exception as exc:  # noqa: BLE001 - a broken __fuzz__ must not crash resolve()
        _log.warning("resolve: %s.__fuzz__() raised %s", tp, exc)
        return None


def _field_strategy(annotation: Any) -> Result[object, FuzzError]:
    """A hypothesis strategy for one pydantic field's annotation, via `st.from_type`."""
    assert _st is not None  # noqa: S101 - guarded by HYPOTHESIS_AVAILABLE at call site
    try:
        return Ok(_st.from_type(annotation))
    except Exception as exc:  # noqa: BLE001 - from_type raises many unrelated types
        _log.debug("_field_strategy: no strategy for %r: %s", annotation, exc)
        return Err(FuzzError.NoGenerator)


def _derived_strategy(tp: type[BaseModel]) -> Result[object, FuzzError]:
    """A hypothesis strategy built from `tp`'s pydantic fields, round-tripping
    every candidate through `tp.model_validate` so validators reject bad draws.
    """
    assert _st is not None  # noqa: S101 - guarded by HYPOTHESIS_AVAILABLE at call site
    try:
        hints = get_type_hints(tp, include_extras=True)
    except Exception as exc:  # noqa: BLE001 - forward refs can fail arbitrarily
        _log.warning("resolve: %s has unresolvable type hints: %s", tp, exc)
        return Err(FuzzError.NoGenerator)

    field_strategies = _field_strategies_for(tp, hints)
    if field_strategies.is_err:
        return Err(field_strategies.danger_err)
    combined = _st.fixed_dictionaries(field_strategies.danger_ok)

    @_st.composite
    def _validated(draw: Any) -> BaseModel:
        """One rejection-sampled draw: build a candidate dict, then `model_validate`."""
        candidate = draw(combined)
        try:
            return tp.model_validate(candidate)
        except Exception:  # noqa: BLE001 - pydantic ValidationError, filtered via reject
            from hypothesis import reject

            reject()  # always raises UnsatisfiedAssumption
            raise AssertionError("unreachable: reject() always raises")  # noqa: TRY003

    return Ok(_validated())


def _field_strategies_for(
    tp: type[BaseModel], hints: dict[str, Any]
) -> Result[dict[str, Any], FuzzError]:
    """Per-field hypothesis strategies for `tp`'s pydantic fields, or the
    first field's `Err` if any field lacks a resolvable annotation/strategy."""
    field_strategies: dict[str, Any] = {}
    for name in tp.model_fields:
        annotation = hints.get(name)
        if annotation is None:
            _log.warning("resolve: %s.%s has no resolvable annotation", tp, name)
            return Err(FuzzError.NoGenerator)
        resolved = _field_strategy(annotation)
        if resolved.is_err:
            return Err(resolved.danger_err)
        field_strategies[name] = resolved.danger_ok
    return Ok(field_strategies)


# frob:doc docs/modules/fuzz.md#public-api
# frob:waive TEST005 reason="resolve 88.2% branch cover, debt T-0160"
def resolve(
    tp: type, *, registry: FuzzRegistry | None = None
) -> Result[object, FuzzError]:
    """Derived -> declared -> registered; `Err(NoGenerator)` otherwise.

    `registry` (default: the process-global default registry, T-0469) is
    consulted for the REGISTERED case, letting a multi-project host pass a
    project-scoped `FuzzRegistry` instead of sharing one process-wide table.

    Deviation from docs/modules/fuzz.md's literal 1-2-3 ordering: `__fuzz__()` is
    checked *before* pydantic derivation, not after. The design-decisions
    section frames the declared classmethod as the escape hatch for models
    "where rejection sampling can't hit efficiently" -- if derivation were
    checked first for every `BaseModel`, a `__fuzz__()` on such a model
    would never be consulted, defeating that stated purpose. Declared
    generators on non-pydantic types are unaffected either way.
    """
    if not HYPOTHESIS_AVAILABLE:
        _log.error("resolve: hypothesis is not installed; cannot generate for %s", tp)
        return Err(FuzzError.NoGenerator)
    return _resolve_cascade(tp, registry or _default_registry)


def _resolve_cascade(tp: type, registry: FuzzRegistry) -> Result[object, FuzzError]:
    """Try declared -> pydantic-derived -> registered strategies for `tp`
    in order, logging which source hit (or that all missed)."""
    declared = _declared_strategy(tp)
    if declared is not None:
        _log.debug("resolve: %s -> declared __fuzz__()", tp)
        return Ok(declared)

    if isinstance(tp, type) and issubclass(tp, BaseModel):
        derived = _derived_strategy(tp)
        if derived.is_ok:
            _log.debug("resolve: %s -> derived from pydantic fields", tp)
        return derived

    if tp in registry:
        _log.debug("resolve: %s -> registered strategy", tp)
        return Ok(registry[tp])

    _log.warning(
        "resolve: no generator for %s (derived/declared/registered all miss)", tp
    )
    return Err(FuzzError.NoGenerator)


__all__ = ["HYPOTHESIS_AVAILABLE", "FuzzRegistry", "register", "resolve"]
