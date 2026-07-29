"""R6 opt-in observational-equivalence probing (split from `dup/_pipeline.py`, T-1086).

`probe_equivalence` and its supporting purity/import/generator/case-running
helpers -- see docs/modules/dup.md#public-api's "R6" section and the module
docstring's "R6's purity heuristic" deviation note (now on
`frob.dup._pipeline`'s `__init__.py`). Opt-in, never called from
`find_clones`/the DUP gate path.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/dup/_pipeline/_probe.py's exclusivity-vocabulary hit is source-level \
# design-rationale prose (a docstring or comment describing already-implemented \
# internal behavior, verifiable by reading the code it annotates) rather than a \
# separate cross-module contract needing its own tracked invariant; disposed as a \
# calibration batch, not claim-by-claim -- module prose split from the pre-T-1086 \
# monolith"

from __future__ import annotations

import importlib.util
import time
import warnings
from pathlib import Path
from typing import Any

from typani import Err, Ok
from typani.result import Result

from frob.dup._models import DupError, ProbeVerdict
from frob.dup._pipeline._callgraph import _parsed_symbols_by_path
from frob.dup._pipeline._shared import _IMPURE_TOKENS, _log
from frob.graph._models import GraphSnapshot

_builtin_generators_registered = False


def _ensure_builtin_generators() -> None:
    """Register plain-builtin Arbitrary strategies once (int/float/str/bool).

    `frob.fuzz.resolve` only derives generators for pydantic `BaseModel`
    subclasses or types with a declared/registered strategy -- it has no
    built-in fallback for `int`/`str`/etc. R6 probing overwhelmingly needs
    exactly those scalar types, so this registers them once, through the
    same public `frob.fuzz.register` mechanism the docs describe for
    "third-party types the caller cannot annotate" -- plain builtins are
    exactly that case for a probe harness that does not own the probed
    function's module.
    """
    global _builtin_generators_registered
    if _builtin_generators_registered:
        return
    from frob.fuzz._arbitrary import HYPOTHESIS_AVAILABLE, register

    if not HYPOTHESIS_AVAILABLE:
        return
    import hypothesis.strategies as st

    register(int, st.integers(min_value=-10_000, max_value=10_000))
    register(float, st.floats(allow_nan=False, allow_infinity=False, width=32))
    register(str, st.text(max_size=20))
    register(bool, st.booleans())
    _builtin_generators_registered = True


def _is_pure_heuristic(tokens: tuple[str, ...]) -> bool:
    """Conservative purity check -- see the module docstring's R6 deviation note."""
    return not any(tok in _IMPURE_TOKENS for tok in tokens)


def _load_python_callable(root: Path, path: str, qualname: str) -> Any | None:
    """Best-effort `importlib` load of a top-level or `Class.method` callable."""
    if not path.endswith(".py"):
        return None
    file_path = root / path
    try:
        module_name = f"_frob_dup_probe_{hash(path)}"
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 - any import-time failure means "can't probe"
        _log.debug("probe_equivalence: failed to load %s: %s", path, exc)
        return None

    obj: Any = module
    for part in qualname.split("."):
        obj = getattr(obj, part, None)
        if obj is None:
            return None
    return obj if callable(obj) else None


# frob:doc docs/modules/dup.md#public-api
def probe_equivalence(
    a: str, b: str, snapshot: GraphSnapshot, budget_s: float
) -> Result[ProbeVerdict, DupError]:
    """R6: observational-equivalence probing for effect-free candidate pairs.

    Refuses (`Err(NotPure)`/`Err(NoGenerator)`) unless both `a` and `b` pass
    the purity heuristic, load as importable callables, and `a`'s
    parameters all have a resolvable Arbitrary generator that `b` also
    accepts positionally -- see `_probe_setup`. Compares outputs for up to
    `budget_s` seconds; both sides are always called positionally
    (`_call_safe`), since a pair the prober cannot legitimately call that
    way must never fall through to a vacuous `equivalent=True` verdict.
    """
    setup = _probe_setup(a, b, snapshot)
    if setup.is_err:
        return Err(setup.danger_err)
    fn_a, fn_b, strategies = setup.danger_ok

    verdict = _run_probe_cases(fn_a, fn_b, strategies, budget_s)
    return Ok(_probe_verdict(a, b, verdict))


def _probe_verdict(
    a: str, b: str, verdict: tuple[bool, int, dict[str, str] | None]
) -> ProbeVerdict:
    """Log and package a `_run_probe_cases` result as the final `ProbeVerdict`."""
    equivalent, cases_run, counterexample = verdict
    _log.info(
        "probe_equivalence: %s vs %s -- equivalent=%s cases_run=%d",
        a,
        b,
        equivalent,
        cases_run,
    )
    return ProbeVerdict(
        left=a,
        right=b,
        equivalent=equivalent,
        cases_run=cases_run,
        counterexample=counterexample,
    )


def _probe_setup(
    a: str, b: str, snapshot: GraphSnapshot
) -> Result[tuple[Any, Any, dict[str, Any]], DupError]:
    """Resolve `a`/`b` to callables and `a`'s Arbitrary strategies, verifying
    `b` accepts the same positional arity -- everything `probe_equivalence`
    needs before it can actually run cases."""
    callables = _probe_callables(a, b, snapshot)
    if callables.is_err:
        return Err(callables.danger_err)
    fn_a, fn_b = callables.danger_ok

    strategies_r = _probe_strategies(fn_a)
    if strategies_r.is_err:
        return Err(strategies_r.danger_err)
    strategies = strategies_r.danger_ok

    if not _probe_arity_compatible(fn_b, len(strategies)):
        _log.info(
            "probe_equivalence: %s vs %s -- fn_b rejects %d positional arg(s)",
            a,
            b,
            len(strategies),
        )
        return Err(DupError.NoGenerator)
    return Ok((fn_a, fn_b, strategies))


def _probe_callables(
    a: str, b: str, snapshot: GraphSnapshot
) -> Result[tuple[Any, Any], DupError]:
    """Resolve `a`/`b` to importable pure Python callables, or `Err(NotPure)`
    when either is missing, effectful (purity heuristic), or unloadable."""
    root = Path(snapshot.root)
    a_rec = snapshot.symbols.get(a)
    b_rec = snapshot.symbols.get(b)
    if a_rec is None or b_rec is None:
        _log.debug("probe_equivalence: %s or %s not in snapshot", a, b)
        return Err(DupError.NotPure)

    a_tokens = _parsed_symbols_by_path(root, a_rec.id.path).get(a_rec.id.qualname)
    b_tokens = _parsed_symbols_by_path(root, b_rec.id.path).get(b_rec.id.qualname)
    if not a_tokens or not b_tokens:
        _log.debug("probe_equivalence: %s or %s has no body tokens", a, b)
        return Err(DupError.NotPure)
    if not (_is_pure_heuristic(a_tokens) and _is_pure_heuristic(b_tokens)):
        _log.info("probe_equivalence: %s vs %s -- purity heuristic refuses", a, b)
        return Err(DupError.NotPure)

    fn_a = _load_python_callable(root, a_rec.id.path, a_rec.id.qualname)
    fn_b = _load_python_callable(root, b_rec.id.path, b_rec.id.qualname)
    if fn_a is None or fn_b is None:
        _log.info("probe_equivalence: %s or %s could not be loaded as a callable", a, b)
        return Err(DupError.NotPure)
    return Ok((fn_a, fn_b))


# frob:waive EXHAUST001 reason="T-1062: leaked Unknown traces to resolve() (deferred \
# import of frob.fuzz._arbitrary.resolve, a typani Result-returning call the resolver \
# cannot follow) and _probe_param_strategy's own dict/attribute access on \
# sig.parameters, an inspect.Signature the caught inspect.signature() call already \
# produced; every other locally-visible fallible step is Result-checked"
# frob:waive EXHAUST002 reason="T-1062: same resolver artifact as EXHAUST001 above"
def _probe_strategies(fn_a: Any) -> Result[dict[str, Any], DupError]:
    """Arbitrary generators for `fn_a`'s parameters, keyed by name.

    `Err(NoGenerator)` for var-args, keyword-only params, an unannotated
    parameter, or a type with no resolvable generator (see
    `_probe_param_strategy` for why KEYWORD_ONLY is rejected -- T-0041's
    vacuous-pass bug); `Err(NotPure)` if the signature is uninspectable.
    """
    import inspect

    from frob.fuzz._arbitrary import resolve

    _ensure_builtin_generators()

    try:
        sig = inspect.signature(fn_a)
    except (TypeError, ValueError):
        return Err(DupError.NotPure)

    strategies: dict[str, Any] = {}
    for name, param in sig.parameters.items():
        gen_result = _probe_param_strategy(param, resolve)
        if gen_result.is_err:
            return Err(gen_result.danger_err)
        strategies[name] = gen_result.danger_ok
    return Ok(strategies)


def _probe_param_strategy(param: Any, resolve: Any) -> Result[Any, DupError]:
    """One parameter's Arbitrary generator, or `Err(NoGenerator)` for
    var-args/keyword-only/unannotated/unresolvable -- see `_probe_strategies`.

    KEYWORD_ONLY is rejected for the same reason VAR_POSITIONAL/VAR_KEYWORD
    are: `_run_probe_cases` calls both `fn_a` and `fn_b` positionally
    (renamed clones have differently-named parameters, so keyword binding
    by `fn_a`'s names would call `fn_b` with the wrong names). A
    keyword-only parameter can never legitimately be supplied positionally,
    so probing it would always raise `TypeError` on the first case -- and
    because `_call_safe` maps matching exceptions to a comparable sentinel,
    two functions that are NOT equivalent but both reject positional
    calling would score `equivalent=True` on every case (the vacuous-pass
    bug this guard exists to close, T-0041 reviewer repro). A pair the
    prober cannot legitimately call this way must be an explicit refusal,
    never a verdict."""
    import inspect

    if param.kind in (
        inspect.Parameter.VAR_POSITIONAL,
        inspect.Parameter.VAR_KEYWORD,
        inspect.Parameter.KEYWORD_ONLY,
    ):
        return Err(DupError.NoGenerator)
    annotation = param.annotation
    if annotation is inspect.Parameter.empty:
        return Err(DupError.NoGenerator)
    gen_result = resolve(annotation)
    if gen_result.is_err:
        return Err(DupError.NoGenerator)
    return Ok(gen_result.danger_ok)


# frob:waive EXHAUST001 reason="T-1062: leaked Unknown traces to \
# inspect.Signature.bind, a stdlib call the resolver cannot bound-check statically; \
# both of its documented raise paths (TypeError for arity mismatch, ValueError for \
# unmet defaults) are caught below"
def _probe_arity_compatible(fn_b: Any, n_positional: int) -> bool:
    """True if `fn_b` can be called with exactly `n_positional` positional
    arguments, checked via `Signature.bind` (never by calling `fn_b`).

    `_run_probe_cases` calls `fn_b(*args)` with `len(args) ==
    n_positional` (the count of `fn_a`'s probed parameters -- see
    `_probe_strategies`). If `fn_b` requires a different arity (extra
    required params, too few params, or a keyword-only param with no
    default that positional binding can't satisfy), the call always
    raises `TypeError`, which is not "equivalent" evidence -- it is an
    uncallable pair. Without this guard a differing-arity pair would
    silently degenerate into the same vacuous-pass failure mode
    `_probe_strategies`'s KEYWORD_ONLY rejection closes for `fn_a`: if
    `fn_a` also happens to raise on some input, `_call_safe`'s shared
    exception sentinel would count the mismatch as agreement. Checked
    with placeholder values via `bind`, so this never partially
    executes `fn_b`.
    """
    import inspect

    try:
        sig_b = inspect.signature(fn_b)
        sig_b.bind(*([None] * n_positional))
    except TypeError:
        return False
    except ValueError:
        return False
    return True


def _call_safe(fn: Any, args: tuple[Any, ...]) -> Any:
    """Call `fn(*args)` positionally, mapping any exception to a comparable
    sentinel so two callables that fail the same way compare equal.

    Positional, not keyword, because R6's whole purpose is comparing
    *renamed* clones -- `fn_b`'s parameters routinely have different names
    than `fn_a`'s (that is the rename), so binding by name would call
    `fn_b` with `fn_a`'s parameter names and raise a spurious TypeError on
    every renamed pair, making renamed clones always compare unequal.
    """
    try:
        return fn(*args)
    except Exception as exc:  # noqa: BLE001 - comparing failure modes, not raising
        return ("__frob_exc__", type(exc).__name__)


def _run_probe_cases(
    fn_a: Any, fn_b: Any, strategies: dict[str, Any], budget_s: float
) -> tuple[bool, int, dict[str, str] | None]:
    """Draw inputs and compare `fn_a`/`fn_b` outputs until they diverge, the
    case budget is hit, or `budget_s` elapses.

    Inputs are drawn once per case (keyed on `fn_a`'s parameter names, in
    declaration order) and passed to BOTH callables positionally in that
    same order -- see `_call_safe` for why keyword-binding would be wrong
    for renamed clones.
    """
    cases_run = 0
    equivalent = True
    counterexample: dict[str, str] | None = None
    start = time.monotonic()
    max_cases = 50
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        while (
            equivalent and cases_run < max_cases and time.monotonic() - start < budget_s
        ):
            cases_run += 1
            counterexample = _probe_one_case(fn_a, fn_b, strategies)
            if counterexample is not None:
                equivalent = False
    return equivalent, cases_run, counterexample


def _probe_one_case(
    fn_a: Any, fn_b: Any, strategies: dict[str, Any]
) -> dict[str, str] | None:
    """Draw one case from `strategies` and call both callables with it;
    `None` if they agree, else the counterexample dict."""
    kwargs = {name: strategy.example() for name, strategy in strategies.items()}
    args = tuple(kwargs.values())
    result_a = _call_safe(fn_a, args)
    result_b = _call_safe(fn_b, args)
    if result_a == result_b:
        return None
    return {
        **{k: repr(v) for k, v in kwargs.items()},
        "left_result": repr(result_a),
        "right_result": repr(result_b),
    }
