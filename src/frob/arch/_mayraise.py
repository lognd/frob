"""Python may-raise resolver (T-0686, child 1 of T-0685's exception may-
raise umbrella): per-function may-raise sets computed over the shared
`frob.arch._normalized.NormalizedModule` (T-0609) -- own `raise` sites +
a curated builtin-raiser table (subscript/cast/attribute/io) + callee
propagation (fixpoint over the same-module call graph, cycles converge) +
`except`-clause subtraction (exception-hierarchy aware: `except Exception`
discharges a `ValueError`). An unresolved callee -- one this module's
same-module name lookup cannot match to a `NormalizedFunction`, and whose
bare name is not in the curated builtin-raiser table -- contributes the
`UNKNOWN` sentinel, FAIL-CLOSED, per the T-0339 doctrine T-0685 reuses.

REUSE, NOT A SECOND BINDING ANALYSIS: this resolver deliberately does not
reimplement `frob.vet`'s tree-sitter-level alias/import binding resolver
(T-0328/T-0337/T-0659) -- that resolver answers a narrower question ("is
this identifier bound, however indirectly, to one specific dangerous
target") over raw source, not "what NormalizedFunction does this call
site's callee resolve to" over the flattened T-0609 model. It instead
reuses the SAME name-resolution convention T-0659 hardened and this
package's own `frob.arch._fallibility` already exercises against
`NormalizedModule` (`_result_returning_names`/`_bare_callee_name`'s
same-module bare-identifier lookup, T-0623): a call's bare callee name
(`self.load`/`store.load`/`load` -> `"load"`) is looked up against every
`NormalizedFunction` in the module (free functions and methods share one
namespace, matching `_fallibility.py`'s existing convention). A name bound
to more than one function in the module is treated as AMBIGUOUS and
excluded from the lookup table entirely -- a call to an ambiguous name
therefore resolves to Unknown, fail-closed, rather than guessing which
definition it means.

MODEL-LIMIT DISCLOSURE (matching `_fallibility.py`'s own house convention
for this package): cross-module callee resolution, aliased imports, and
attribute-chain receiver resolution are OUT of this resolver's scope --
same-module bare-name lookup only, same limit `_fallibility.py`'s
`check_unhandled_result` already discloses and accepts. A subscript
(`d[k]`) is modeled as `KeyError` only (the curated table's disclosed
default for the common dict-shaped case); this model has no way to know
whether the subscripted value is dict-shaped (`KeyError`) or
sequence-shaped (`IndexError`) without a resolved type, so it picks the
one the parent ticket's own acceptance criterion names rather than
under-approximating with nothing.

EXCEPT-CLAUSE SUBTRACTION is applied FUNCTION-WIDE (every `catch` in a
function can discharge any raise/propagated-raise anywhere else in that
same function), not scoped to the lexical try-block a catch actually
guards -- the T-0609 model has no block-scoping finer than a whole
function body (same disclosed limitation `_fallibility.py`'s adjacency-
window checks already live with). A bare `raise` (re-raise, no static
type) resolves to whatever the NEAREST PRECEDING `catch` on that function
caught (the same line-adjacency-proxy style `_fallibility.py` uses
elsewhere); with no preceding catch, or a bare-`except:` preceding catch
(re-raising an unknown active exception), it resolves to `UNKNOWN`.

THE UBIQUITOUS TIER (`MemoryError`/`KeyboardInterrupt`/`SystemExit`,
T-0685) is tracked SEPARATELY, exposed as the `UBIQUITOUS_TIER` constant
below, and never folded into a `FunctionMayRaise.raises` set -- per the
parent ticket's own doctrine, exhaustiveness never demands it be
enumerated per-function; only a boundary catch-all discharges it, which
is a caller's concern (T-0688's gate/advisory job), not this resolver's.

OPAQUE C-EXTENSION/CTYPES/CFFI BOUNDARIES (T-0689): a call whose bare name
is not a same-module function and not in one of the curated raiser tables
below is ALREADY fail-closed to `UNKNOWN` by the unresolved-callee path
above -- this covers every ctypes/cffi call (`ctypes.CDLL(...)`, a loaded
handle's `lib.some_c_function(...)`, `cffi.FFI().dlopen(...)` and its
resulting object's calls) and any other compiled-extension call this
resolver has no source to see into: none of them carry a fixed per-call
raised type (a C extension's own exception behavior is opaque to a
Python-source-level resolver, and ctypes/cffi calls specifically have no
exception-propagation contract at all -- see T-0690's own FFI-boundary
ticket for the cross-language enforcement built on top of this). The
`_STDLIB_QUALIFIED_RAISERS` table curates the well-known STDLIB
C-extension exceptions (`json.loads`/`json.load` -> `JSONDecodeError`,
`sqlite3.connect`/`sqlite3.execute` -> `sqlite3.Error`,
`struct.pack`/`struct.unpack` -> `struct.error`) so those specific common
cases resolve precisely instead of falling to `UNKNOWN` -- keyed on the
call's FULL dotted callee text (not the bare name `_BUILTIN_RAISERS`
matches on), since a bare-name match here would risk shadowing an
unrelated same-module function sharing one of these names.

`frob:callee-raises` DECLARATION (T-0689, `NormalizedCall.declared_raises`): a
same-line `# frob:callee-raises A, B` comment on a call site (parsed by
`frob.arch._python`'s adapter for python; `# frob:callee-raises` alone declares
the empty set) SUBSTITUTES its declared exception-name set for that call
UNCONDITIONALLY -- checked FIRST, before either curated table or the
same-module lookup, so a declaration on an otherwise-opaque ctypes/cffi
boundary call is exactly how a caller escapes the `UNKNOWN` fail-closed
default. This resolver only CONSUMES the declaration already parsed onto
the model; the declaration GRAMMAR/enforcement (requiring a declaration on
every such boundary, cross-checking it against a visible Rust/C side) is
T-0690's job, not duplicated here."""
# frob:waive INV006 reason="this module's 'only' occurrences are source-level \
# design-rationale prose (the module docstring's model-limit disclosures and \
# per-function docstrings describing already-implemented resolution/matching logic), \
# verifiable by reading the function it annotates, not a separate cross-module \
# contract needing its own tracked invariant -- the same INV006 first-turn-on-pool \
# disposition frob.arch._fallibility's own module docstring already carries"

from __future__ import annotations

from pydantic import BaseModel

from frob.arch._normalized import NormalizedCatch, NormalizedFunction, NormalizedModule

#: Sentinel raised-type name (T-0686) meaning "this function may raise
#: something this resolver could not statically determine" -- the
#: fail-closed contribution of any unresolved callee or unresolvable bare
#: `raise`. Kept as a plain string (not a distinct type) since every other
#: raised-type name in this module is already a bare exception-name string
#: and `FunctionMayRaise.raises` is one homogeneous `frozenset[str]`.
#: `frob:doc` points at the dedicated may-raise-resolver anchor (T-0916).
# frob:doc docs/modules/arch.md#may-raise-resolver
# frob:ticket T-0686
UNKNOWN = "Unknown"

#: Exception types (T-0685) tracked as an always-possible tier SEPARATE
#: from a function's own computed may-raise set -- async/asynchronous-
#: delivery exceptions no static analysis of a function's own body can
#: rule out. Exhaustiveness never demands these be enumerated per
#: function; only a boundary catch-all (bare `except:`) discharges them
#: (see this module's docstring).
# frob:doc docs/modules/arch.md#may-raise-resolver
# frob:ticket T-0686
UBIQUITOUS_TIER: frozenset[str] = frozenset(
    {"MemoryError", "KeyboardInterrupt", "SystemExit"}
)

#: Minimal Python exception-hierarchy parent map (T-0686) -- just enough
#: of `BaseException`'s tree for `_catches`'s subtype check to know that
#: `except Exception` discharges a raised `ValueError`, `except
#: LookupError` discharges a raised `KeyError`, etc. Not exhaustive
#: against the full `builtins` hierarchy (no existing check in this
#: package needs more, and the curated `_BUILTIN_RAISERS` table below
#: only ever contributes types already listed here) -- extend as new
#: builtin-raiser rows need a new leaf.
# frob:ticket T-0686
_EXCEPTION_PARENT: dict[str, str | None] = {
    "BaseException": None,
    "SystemExit": "BaseException",
    "KeyboardInterrupt": "BaseException",
    "Exception": "BaseException",
    "StopIteration": "Exception",
    "ValueError": "Exception",
    "TypeError": "Exception",
    "AttributeError": "Exception",
    "NameError": "Exception",
    "UnboundLocalError": "NameError",
    "LookupError": "Exception",
    "KeyError": "LookupError",
    "IndexError": "LookupError",
    "ArithmeticError": "Exception",
    "ZeroDivisionError": "ArithmeticError",
    "OSError": "Exception",
    "FileNotFoundError": "OSError",
    "PermissionError": "OSError",
    "IsADirectoryError": "OSError",
    "RuntimeError": "Exception",
    "NotImplementedError": "RuntimeError",
    "RecursionError": "RuntimeError",
    "AssertionError": "Exception",
    "ImportError": "Exception",
    "ModuleNotFoundError": "ImportError",
    "MemoryError": "Exception",
    # T-0689: parent links for the curated stdlib C-extension raiser table
    # below -- `JSONDecodeError` really is a `ValueError` subclass
    # (`json.JSONDecodeError(ValueError)`); `sqlite3.Error`/`struct.error`
    # are their own hierarchy roots directly under `Exception`.
    "JSONDecodeError": "ValueError",
    "sqlite3.Error": "Exception",
    "struct.error": "Exception",
}

#: Curated builtin-raiser table (T-0685/T-0686): bare callee name -> the
#: exception type(s) that call is known to be capable of raising, per the
#: parent ticket's own examples (`int()`/`float()` casts -> `ValueError`,
#: `getattr` reflection -> `AttributeError`, `open`/file IO -> `OSError`,
#: `next` on an exhausted iterator -> `StopIteration`). A call whose bare
#: name matches a row here is treated as RESOLVED (contributes exactly
#: these types, does not also fall through to the unresolved-callee
#: `UNKNOWN` path) even though this resolver has no `NormalizedFunction`
#: body for it to recurse into -- deliberately narrow (see this module's
#: docstring): every callee name NOT in this table and NOT a same-module
#: function is fail-closed to `UNKNOWN`, not silently assumed safe.
# frob:ticket T-0686
_BUILTIN_RAISERS: dict[str, frozenset[str]] = {
    "int": frozenset({"ValueError", "TypeError"}),
    "float": frozenset({"ValueError", "TypeError"}),
    "open": frozenset({"OSError"}),
    "getattr": frozenset({"AttributeError"}),
    "next": frozenset({"StopIteration"}),
}

#: Curated stdlib C-EXTENSION raiser table (T-0689), keyed on the call's
#: FULL dotted callee text (`"json.loads"`, not the bare `"loads"`) --
#: deliberately a SEPARATE, more specific table from `_BUILTIN_RAISERS`
#: (which matches on bare name): a bare-name match here would risk
#: shadowing an unrelated same-module function that happens to share a
#: name with one of these (`def pack(...)` in the caller's own module,
#: say) the same way `_BUILTIN_RAISERS` already narrowly accepts for true
#: builtins with no realistic same-module collision. Qualified stdlib
#: C-extension calls (json's `_json` accelerator, sqlite3's `_sqlite3`,
#: struct's `_struct`) resolve to their documented raised type instead of
#: falling through to the opaque-boundary `UNKNOWN` default (this ticket's
#: user mandate) -- extend as more curated stdlib C-extension surface is
#: identified; anything NOT listed here (including ctypes/cffi calls,
#: which have no fixed per-call raised type at all -- see this module's
#: docstring) stays `UNKNOWN`, fail-closed, unless covered by a
#: `frob:callee-raises` declaration (`NormalizedCall.declared_raises`).
# frob:ticket T-0689
_STDLIB_QUALIFIED_RAISERS: dict[str, frozenset[str]] = {
    "json.loads": frozenset({"JSONDecodeError"}),
    "json.load": frozenset({"JSONDecodeError"}),
    "sqlite3.connect": frozenset({"sqlite3.Error"}),
    "sqlite3.execute": frozenset({"sqlite3.Error"}),
    "struct.pack": frozenset({"struct.error"}),
    "struct.unpack": frozenset({"struct.error"}),
}

#: Raised-type name a bare (dict-shaped default, see this module's
#: docstring) `NormalizedSubscript` event contributes.
# frob:ticket T-0686
_SUBSCRIPT_RAISE = "KeyError"


# frob:doc docs/modules/arch.md#may-raise-resolver
# frob:ticket T-0686
class FunctionMayRaise(BaseModel):
    """One function/method's computed may-raise set (T-0686): its
    `path::Class.method`/`path::function` symref (`_qualname`'s shape) and
    the `frozenset` of exception type names it may raise, `UNKNOWN`
    included when any contributing raise/call could not be statically
    resolved. Never includes `UBIQUITOUS_TIER` members (tracked
    separately, see this module's docstring)."""

    model_config = {}

    qualname: str
    raises: frozenset[str]


# frob:ticket T-0686
def _qualname(
    module: NormalizedModule, cls_name: str | None, func: NormalizedFunction
) -> str:
    """`path::Class.method`/`path::function` symref (T-0289's shape,
    T-0686) for `func`, optionally scoped to `cls_name` -- a narrow local
    duplicate of `frob.arch._fallibility._qualname` (that sibling module
    is out of this ticket's declared scope; see this module's docstring
    for why duplicating this one small helper, not importing a private
    name across modules, is the intended shape here)."""
    if cls_name is None:
        return f"{module.path}::{func.name}"
    return f"{module.path}::{cls_name}.{func.name}"


# frob:ticket T-0686
def _bare_callee_name(callee: str) -> str:
    """The trailing identifier of a possibly-dotted callee text (T-0686)
    -- same convention as `frob.arch._fallibility._bare_callee_name`."""
    return callee.rsplit(".", 1)[-1]


# frob:ticket T-0686
def _is_subtype(sub: str, sup: str) -> bool:
    """True when raised-type `sub` is `sup` or a descendant of it in
    `_EXCEPTION_PARENT` (T-0686) -- `_is_subtype("KeyError",
    "LookupError")` and `_is_subtype("KeyError", "Exception")` are both
    true. A type absent from `_EXCEPTION_PARENT` is only ever equal to
    itself (walks to a dead end immediately)."""
    cur: str | None = sub
    while cur is not None:
        if cur == sup:
            return True
        cur = _EXCEPTION_PARENT.get(cur)
    return False


# frob:ticket T-0686
def _catches(caught: str | None, raised: str) -> bool:
    """True when an `except` clause whose caught type text is `caught`
    (`None` for a bare `except:`) discharges a raised/propagated type
    `raised` (T-0686). `UNKNOWN` is only discharged by a catch-all (bare
    `except:` or `except Exception:`) -- a narrow `except ValueError:`
    must not be credited with silently handling a raise this resolver
    could not identify (fail-closed: an unresolved raise stays unresolved
    unless the catch is broad enough to plausibly cover it)."""
    if raised == UNKNOWN:
        return caught is None or caught == "Exception"
    if caught is None or caught == "Exception":
        return True
    return _is_subtype(raised, caught)


# frob:ticket T-0686
def _nearest_preceding_catch(
    func: NormalizedFunction, line: int
) -> NormalizedCatch | None:
    """The `catch` in `func` with the greatest `line` at or before `line`
    (T-0686) -- the line-adjacency proxy a bare `raise` (re-raise) resolves
    its active exception type against, same convention style
    `frob.arch._fallibility`'s adjacency-window checks already use."""
    candidates = [c for c in func.catches if c.line <= line]
    if not candidates:
        return None
    return max(candidates, key=lambda c: c.line)


# frob:ticket T-0686
# frob:ticket T-0689
def _own_base_raises(
    func: NormalizedFunction, name_to_func: dict[str, NormalizedFunction]
) -> tuple[set[str], set[str], set[str]]:
    """`func`'s own contribution (T-0686, extended T-0689) before
    callee-graph fixpoint, split into two pools whose treatment under
    `func`'s OWN `except` clauses differs (`compute_may_raise`'s
    docstring): `direct_raises` -- from `func.raises` (a resolved-directly
    type, or a bare re-raise resolved via `_nearest_preceding_catch`) --
    ALWAYS escapes `func` unconditionally; a `raise` statement, once
    reached, executes, and a catch clause earlier in the SAME flattened
    function body must not be credited with discharging the very re-raise
    it produced. `catchable` -- `subscripts` (`_SUBSCRIPT_RAISE`) and each
    call's contribution -- represents a call site's exception, which a
    wrapping `try`/`except` genuinely CAN discharge, so it is left subject
    to `func`'s own catches by the caller (`compute_may_raise`'s fixpoint).

    T-0689: each call is resolved in priority order -- (1) a `frob:callee-raises`
    declaration (`NormalizedCall.declared_raises is not None`) SUBSTITUTES
    its declared set unconditionally, the intended escape hatch for an
    opaque ctypes/cffi/C-extension boundary this resolver cannot see
    inside of (an empty declared set is honored as-is: "declared to raise
    nothing"); (2) failing that, the curated qualified-stdlib table
    (`_STDLIB_QUALIFIED_RAISERS`, keyed on the call's full dotted text);
    (3) failing that, the bare-name `_BUILTIN_RAISERS` table; (4) failing
    that, a same-module function name (`name_to_func`) is deferred to the
    caller's fixpoint; (5) anything else -- including every ctypes/cffi
    call and every other unrecognized compiled-extension call, since none
    of those resolve via (2)-(4) -- fails closed to `UNKNOWN`. Returns
    `(direct_raises, catchable, resolved_callee_bare_names)`: the third
    element is every call's bare name that DOES match `name_to_func`,
    consumed by the caller's fixpoint loop rather than recursed into here
    directly, so cycles are handled by the iterative fixpoint, not
    unbounded recursion."""
    direct = _resolve_direct_raises(func)
    catchable, resolved_callees = _resolve_call_contributions(func, name_to_func)
    return direct, catchable, resolved_callees


# frob:ticket T-0976
def _resolve_direct_raises(func: NormalizedFunction) -> set[str]:
    """`func`'s own `raise` statements (T-0686): a resolved-directly type
    as-is, or a bare re-raise resolved against the nearest preceding
    `except` via `_nearest_preceding_catch` -- these always escape `func`
    unconditionally regardless of any later catch in the same body."""
    direct: set[str] = set()
    for r in func.raises:
        if r.exception_type is not None:
            direct.add(r.exception_type)
            continue
        catch = _nearest_preceding_catch(func, r.line)
        if catch is None or catch.exception_type is None:
            direct.add(UNKNOWN)
        else:
            direct.add(catch.exception_type)
    return direct


# frob:ticket T-0976
def _resolve_call_contributions(
    func: NormalizedFunction, name_to_func: dict[str, NormalizedFunction]
) -> tuple[set[str], set[str]]:
    """`func`'s subscript and call-site contributions to `catchable`
    (T-0689's priority order: declared_raises, then the qualified-stdlib
    table, then the bare-builtin table, then same-module deferral, else
    fail-closed UNKNOWN) -- these ARE subject to `func`'s own catches,
    unlike `_resolve_direct_raises`'s set. Returns `(catchable,
    resolved_callee_bare_names)`, the latter deferred to the caller's
    fixpoint rather than recursed into here."""
    catchable: set[str] = set()
    resolved_callees: set[str] = set()

    for _ in func.subscripts:
        catchable.add(_SUBSCRIPT_RAISE)

    for call in func.calls:
        if call.declared_raises is not None:
            catchable |= call.declared_raises
            continue
        bare = _bare_callee_name(call.callee)
        if call.callee in _STDLIB_QUALIFIED_RAISERS:
            catchable |= _STDLIB_QUALIFIED_RAISERS[call.callee]
        elif bare in _BUILTIN_RAISERS:
            catchable |= _BUILTIN_RAISERS[bare]
        elif bare in name_to_func:
            resolved_callees.add(bare)
        else:
            catchable.add(UNKNOWN)

    return catchable, resolved_callees


# frob:ticket T-0686
def _build_name_to_func(module: NormalizedModule) -> dict[str, NormalizedFunction]:
    """Same-module bare-name -> `NormalizedFunction` lookup table (T-0686):
    every top-level function and every method across every class share one
    namespace (matching `frob.arch._fallibility._result_returning_names`'s
    existing convention). A name bound to more than one function/method in
    the module is AMBIGUOUS and excluded entirely -- a call to an
    ambiguous name resolves to `UNKNOWN` (fail-closed) rather than
    guessing which definition it means."""
    table: dict[str, NormalizedFunction] = {}
    ambiguous: set[str] = set()
    for f in module.functions:
        if f.name in table:
            ambiguous.add(f.name)
        table[f.name] = f
    for c in module.classes:
        for m in c.methods:
            if m.name in table:
                ambiguous.add(m.name)
            table[m.name] = m
    for name in ambiguous:
        del table[name]
    return table


# frob:doc docs/modules/arch.md#may-raise-resolver
# frob:ticket T-0686
# frob:tests tests/unit/test_arch.py::TestMayRaiseResolver.test_fixture_chain_own_raise_and_builtin_raiser_and_catch_subtraction  # noqa: E501
# frob:tests tests/unit/test_arch.py::TestMayRaiseResolver.test_unresolvable_call_yields_unknown  # noqa: E501
# frob:waive AFFECT001 reason="T-0976 pure internal refactor: extraction of cohesive helpers from this already-documented function, no external contract/behavior change, doc anchor(s) remain accurate as-is"  # noqa: E501
def compute_may_raise(module: NormalizedModule) -> dict[str, FunctionMayRaise]:
    """Per-function may-raise sets for every top-level function and method
    in `module` (T-0686): each function's EXPOSED set (what escapes it,
    both the reported result and what a caller's propagation sees) is its
    own unconditional `direct_raises` (own `raise` statements -- never
    discharged by that SAME function's own catches, see
    `_own_base_raises`'s docstring) UNIONED with its `catchable` pool
    (builtin-raiser/subscript contributions) and every resolved callee's
    own exposed set, both of the latter FILTERED by this function's own
    `except` clauses (`_catches`) -- a monotonic chaotic-iteration
    fixpoint (`exposed[fn]` only ever grows across iterations, so cycles
    converge rather than recursing unboundedly). Keyed by `_qualname`.
    Unresolved calls (same-module lookup miss, `_build_name_to_func`) and
    unresolved bare raises fail-closed to `UNKNOWN`, per this module's
    docstring."""
    name_to_func = _build_name_to_func(module)
    id_to_func, qualname_by_id, direct_by_id, catchable_by_id, resolved_calls = (
        _register_module_functions(module, name_to_func)
    )
    exposed = _fixpoint_exposed(
        id_to_func, direct_by_id, catchable_by_id, resolved_calls, name_to_func
    )

    return {
        qualname_by_id[fid]: FunctionMayRaise(
            qualname=qualname_by_id[fid], raises=frozenset(exposed[fid])
        )
        for fid in id_to_func
    }


# frob:ticket T-0976
def _register_module_functions(
    module: NormalizedModule, name_to_func: dict[str, NormalizedFunction]
) -> tuple[
    dict[int, NormalizedFunction],
    dict[int, str],
    dict[int, set[str]],
    dict[int, set[str]],
    dict[int, set[str]],
]:
    """Walk every top-level function and method in `module`, computing
    each one's `_own_base_raises` contribution once and indexing all of it
    by `id(func)` -- the per-function tables `compute_may_raise`'s
    fixpoint loop iterates over, built once up front so the fixpoint below
    never re-derives them."""
    id_to_func: dict[int, NormalizedFunction] = {}
    qualname_by_id: dict[int, str] = {}
    direct_by_id: dict[int, set[str]] = {}
    catchable_by_id: dict[int, set[str]] = {}
    resolved_calls: dict[int, set[str]] = {}

    def _register(func: NormalizedFunction, qualname: str) -> None:
        """Index one function/method's `_own_base_raises` split by its
        `id()` into the enclosing tables."""
        fid = id(func)
        id_to_func[fid] = func
        qualname_by_id[fid] = qualname
        direct, catchable, resolved = _own_base_raises(func, name_to_func)
        direct_by_id[fid] = direct
        catchable_by_id[fid] = catchable
        resolved_calls[fid] = resolved

    for f in module.functions:
        _register(f, _qualname(module, None, f))
    for c in module.classes:
        for m in c.methods:
            _register(m, _qualname(module, c.name, m))

    return id_to_func, qualname_by_id, direct_by_id, catchable_by_id, resolved_calls


# frob:ticket T-0976
def _fixpoint_exposed(
    id_to_func: dict[int, NormalizedFunction],
    direct_by_id: dict[int, set[str]],
    catchable_by_id: dict[int, set[str]],
    resolved_calls: dict[int, set[str]],
    name_to_func: dict[str, NormalizedFunction],
) -> dict[int, set[str]]:
    """Chaotic-iteration fixpoint over `id_to_func`: each function's
    exposed set only ever grows (own `direct_by_id` union its
    catchable-after-filtering pool, including resolved callees' own
    exposed sets), so cycles converge rather than recursing unboundedly.
    Returns the converged `id(func) -> exposed exception types` map."""
    name_to_fid = {name: id(fn) for name, fn in name_to_func.items()}
    exposed: dict[int, set[str]] = {
        fid: set(direct) for fid, direct in direct_by_id.items()
    }

    changed = True
    while changed:
        changed = False
        for fid, func in id_to_func.items():
            pool = set(catchable_by_id[fid])
            for bare in resolved_calls[fid]:
                callee_fid = name_to_fid[bare]
                pool |= exposed[callee_fid]
            filtered = {
                t
                for t in pool
                if not any(_catches(c.exception_type, t) for c in func.catches)
            }
            new_exposed = direct_by_id[fid] | filtered
            if new_exposed != exposed[fid]:
                exposed[fid] = new_exposed
                changed = True

    return exposed
